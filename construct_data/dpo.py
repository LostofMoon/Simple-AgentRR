import os, json, shutil
from construct_data.util import load_augmentation_rules, augment_data
from dataclasses import dataclass, asdict
from typing import List, Dict
import copy, re
from PIL import Image
import random
import argparse

@dataclass
class AlpacaImageDPOEntry:
    instruction: str
    chosen: str
    rejected: str
    images: List[str]
    input: str = ""

decider_prompt = '''
<image>
You are a phone-use AI agent. Now your task is "{task}".
Your action history is:
{history}
Please provide the next action based on the screenshot and your action history. You should do careful reasoning before providing the action.
Your action space includes:
- Name: click, Parameters: target_element (a high-level description of the UI element to click).
- Name: swipe, Parameters: direction (one of UP, DOWN, LEFT, RIGHT).
- Name: input, Parameters: text (the text to input).
- Name: wait, Parameters: (no parameters, will wait for 1 second).
- Name: done, Parameters: (no parameters).
Your output should be a JSON object with the following format:
{{"reasoning": "Your reasoning here", "action": "The next action (one of click, input, swipe, wait, done)", "parameters": {{"param1": "value1", ...}}}}
'''.strip()

def construct_ds(data_path, out_path, factor=0.5, train_ratio=0.9):
    os.makedirs(out_path, exist_ok=True)
    
    # 训练集
    entries_train_type1 = []
    entries_train_type2 = []

    # 验证集
    entries_val_type1 = []
    entries_val_type2 = []

    current_dir = os.getcwd()
    augment_config_path = os.path.join(current_dir, 'construct_data', 'augment_config.json')
    rules = load_augmentation_rules(augment_config_path)

    for root, dirs, files in os.walk(data_path):
        if len(files) == 0:
            continue
        if "actions.json" not in files or "react.json" not in files or "parse.error" in files:
            continue

        actions_json = os.path.join(root, "actions.json")
        with open(actions_json, 'r', encoding='utf-8') as file:
            data = json.load(file)
        task_description = data.get("task_description")
        actions = data.get("actions")
        react_json = os.path.join(root, "react.json")
        with open(react_json, "r", encoding="UTF-8") as f:
            react_data = json.load(f)

        # 多模式适配 将没有done的react补充done，目前全部修正带done
        index = 1
        while f"{index}.jpg" in files:
            index += 1
        num_img = index - 1
        if num_img == len(react_data) + 1:
            done_reasoning = "我已经完成了目标任务，任务已结束。"
            react_data.append(
                {
                    "reasoning": done_reasoning,
                    "function": {
                        "name": "done",
                        "parameters": {}
                    }
                }
            )
        elif num_img != len(react_data):
            print(f"Warning: Number of images ({num_img}) does not match number of ReAct entries ({len(react_data)}) in {root}. Skipping this directory.")
            continue
    
        history = []
        # 预处理所有react数据以便后续构建rejected samples
        all_outputs = []
        for react in react_data:
            reasoning = react["reasoning"]
            action_type = react["function"]["name"]
            param = react["function"]["parameters"]
            output_dict = dict(reasoning=reasoning, action=action_type, parameters=param)
            output = json.dumps(output_dict, ensure_ascii=False)
            all_outputs.append(output)
        
        # 预处理所有图片，避免重复处理
        img_paths = {}
        for i in range(1, num_img + 1):
            img_path = os.path.join(root, f"{i}.jpg")
            pil_img = Image.open(img_path)
            width, height = pil_img.size
            new_width = int(width * factor)
            new_height = int(height * factor)
            resized_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
            
            relative_path = os.path.relpath(img_path, data_path)
            safe_filename = relative_path.replace(os.sep, "_").replace(":", "_")
            safe_filename = f"main_{safe_filename}"
            out_relpath = os.path.join(out_path, safe_filename)
            resized_img.save(out_relpath)
            out_abspath = os.path.abspath(out_relpath)
            img_paths[i] = out_abspath

        for i, react in enumerate(react_data, 1):
            is_train = random.random() < train_ratio

            augment_rule = augment_data(react, rules)

            # 使用预处理的图片路径
            out_abspath = img_paths[i]

            # 获取相关参数
            reasoning = react["reasoning"]
            action_type = react["function"]["name"]
            param = react["function"]["parameters"]
            
            chosen = all_outputs[i-1]
            rejected_candidates = []
            if i > 1:
                rejected_candidates.append(all_outputs[i-2])
            if i < len(all_outputs):
                rejected_candidates.append(all_outputs[i])
            
            # 对input类型特殊处理
            if action_type == "input" or action_type == "done":
                # input类型需要至少min(3, total_history_length)的历史长度
                min_history_length = min(3, len(history))
                partial_histories = [history[i:] for i in range(len(history) + 1 - min_history_length)]
            else:
                partial_histories = [history[i:] for i in range(len(history) + 1)]
            
            partial_history_entries = []

            for partial_history in partial_histories:
                if len(partial_history) == 0:
                    history_str = "(No history)"
                else:
                    history_str = "\n".join(f"{idx}. {h}" for idx, h in enumerate(partial_history, 1))

                if(isinstance(task_description, list)):
                    random_tasks = random.sample(task_description, 1)
                    for task in random_tasks:
                        instruction = decider_prompt.format(task=task, history=history_str)
                        for rejected in rejected_candidates:
                            entry = AlpacaImageDPOEntry(
                                instruction=instruction,
                                chosen=chosen,
                                rejected=rejected,
                                images=[out_abspath]
                            )
                            partial_history_entries.append(entry)
                else:
                    instruction = decider_prompt.format(task=task_description, history=history_str)
                    for rejected in rejected_candidates:
                        entry = AlpacaImageDPOEntry(
                            instruction=instruction,
                            chosen=chosen,
                            rejected=rejected,
                            images=[out_abspath]
                        )
                        partial_history_entries.append(entry)

            history.append(chosen)

            # 全历史和部分历史 针对一个action的训练entry
            full_history_entry = partial_history_entries[0]
            partial_history_entries = partial_history_entries[1:]
            partial_history_entries = random.sample(partial_history_entries, min(2, len(partial_history_entries)))
            
            if is_train:
                num = augment_rule.get("reason", augment_rule.get("other", 1))
                entries_train_type1.extend((partial_history_entries + [full_history_entry]) * num)
            else:
                entries_val_type1.extend(partial_history_entries + [full_history_entry])

        # 需求：img到index，action history到index（包含这张图片原本应该做的），chosen是index的action，rejected是index+1的action
        for i in range(1, len(react_data)):  # 从1到len-1，因为需要index+1存在
            is_train = random.random() < train_ratio
            
            # 使用第 i 张图片（index位置的图片）
            out_abspath = img_paths[i]
            
            # chosen 是第 i 步的 action，rejected 是第 i+1 步的 action
            chosen = all_outputs[i-1]   # 第 i 步 (索引 i-1)
            rejected = all_outputs[i]   # 第 i+1 步 (索引 i)
            
            # action history 到 index，即包含第 i 步的历史
            full_history = all_outputs[:i]  # 包含第1步到第i步

            # 生成部分历史，类似 type1 的逻辑
            # 对于 type2，我们基于完整历史生成部分历史
            if len(full_history) <= 1:
                partial_histories = [full_history]
            else:
                # 生成不同长度的部分历史
                partial_histories = [full_history[j:] for j in range(len(full_history))]
            
            partial_history_entries = []
            
            for partial_history in partial_histories:
                if len(partial_history) == 0:
                    history_str = "(No history)"
                else:
                    history_str = "\n".join(f"{idx}. {h}" for idx, h in enumerate(partial_history, 1))
                
                if isinstance(task_description, list):
                    random_tasks = random.sample(task_description, 1)
                    for task in random_tasks:
                        instruction = decider_prompt.format(task=task, history=history_str)
                        entry = AlpacaImageDPOEntry(
                            instruction=instruction,
                            chosen=chosen,
                            rejected=rejected,
                            images=[out_abspath]
                        )
                        partial_history_entries.append(entry)
                else:
                    instruction = decider_prompt.format(task=task_description, history=history_str)
                    entry = AlpacaImageDPOEntry(
                        instruction=instruction,
                        chosen=chosen,
                        rejected=rejected,
                        images=[out_abspath]
                    )
                    partial_history_entries.append(entry)
            
            # 全历史和部分历史 针对 type2 的训练entry
            full_history_entry = partial_history_entries[0]  # 完整历史的entry
            partial_history_entries = partial_history_entries[1:]  # 部分历史的entries
            partial_history_entries = random.sample(partial_history_entries, min(2, len(partial_history_entries)))
            
            if is_train:
                entries_train_type2.extend(partial_history_entries + [full_history_entry])
            else:
                entries_val_type2.extend(partial_history_entries + [full_history_entry])

    # 合并训练集数据
    data = {}

    decider_entries_train = []
    temp_entries = [asdict(entry) for entry in entries_train_type1]
    temp_entries = random.sample(temp_entries, int(len(temp_entries) * 0.03))
    decider_entries_train.extend(temp_entries)

    print(f"entries_train_type1: {len(temp_entries)}")
    data.update({
        "entries_train_type1": len(temp_entries)
    })

    temp_entries = [asdict(entry) for entry in entries_train_type2]
    temp_entries = random.sample(temp_entries, int(len(temp_entries) * 0.1))
    decider_entries_train.extend(temp_entries)
    random.shuffle(decider_entries_train)

    print(f"entries_train_type2: {len(temp_entries)}")
    data.update({
        "entries_train_type2": len(temp_entries)
    })

    decider_entries_val = []
    temp_entries = [asdict(entry) for entry in entries_val_type1]
    temp_entries = random.sample(temp_entries, int(len(temp_entries) * 0.03))
    decider_entries_val.extend(temp_entries)

    print(f"entries_val_type1: {len(temp_entries)}")
    data.update({
        "entries_val_type1": len(temp_entries)
    })

    temp_entries = [asdict(entry) for entry in entries_val_type2]
    temp_entries = random.sample(temp_entries, int(len(temp_entries) * 0.1))
    decider_entries_val.extend(temp_entries)
    random.shuffle(decider_entries_val)

    print(f"entries_val_type2: {len(temp_entries)}")
    data.update({
        "entries_val_type2": len(temp_entries)
    })

    # 保存训练集
    with open(os.path.join(out_path, f"dpo_decider_train.json"), "w", encoding="UTF-8") as f:
        json.dump(decider_entries_train, f, ensure_ascii=False)
    
    # 保存验证集
    with open(os.path.join(out_path, f"dpo_decider_val.json"), "w", encoding="UTF-8") as f:
        json.dump(decider_entries_val, f, ensure_ascii=False)

    with open(os.path.join(out_path, f"dpo_metadata.json"), "w", encoding="UTF-8") as f:
        json.dump(data, f, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Training dataset construction with Alpaca format")
    parser.add_argument("--data_path", type=str, default="data", help="root path of raw data (default: data)")
    # parser.add_argument("--ss_data_path", type=str, default="ss_data", help="root path of single-step data (default: ss_data)")
    parser.add_argument("--out_path", type=str, default="output", help="output path of train dataset (default: output)")
    parser.add_argument("--factor", type=float, default=0.5, help="resize factor for images (default: 0.5)")
    parser.add_argument("--train_ratio", type=float, default=0.9, help="ratio of training data (default: 0.9)")
    args = parser.parse_args()
    construct_ds(
        data_path=args.data_path,
        # single_step_data_path=args.ss_data_path,
        out_path=args.out_path,
        factor=args.factor,
        train_ratio=args.train_ratio,
    )
