import os, json, shutil
from construct_data.util import load_augmentation_rules, augment_data
from dataclasses import dataclass, asdict
from typing import List, Dict
import copy, re
from PIL import Image
import random
import argparse
import math

from utils.load_md_prompt import load_prompt

def calculate_index_weight(index, total_length):
    # 分段权重计算
    if index <= 5:
        base_weight = 1
    elif index <= 8:
        base_weight = 1 + index // 4
    else:
        base_weight = 1 + index // 3
    return base_weight

@dataclass
class AlpacaImageEntry:
    instruction: str
    output: str
    images: List[str]
    input: str = ""

executor_prompt = load_prompt("grounder_coordinates.md")
executor_prompt_bbox = load_prompt("grounder_bbox.md")

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

decider_prompt_no_history = '''
<image>
You are a phone-use AI agent. Now your task is "{task}". Please provide the next action based on the screenshot.
You should do careful reasoning before providing the action.
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

main_page_classification_prompt = '''
<image>
Is this screenshot the main page of the current app? Your answer can only be "yes" or "no".
'''

def construct_main_page_classification_ds(data_path, out_path, factor=0.5, train_ratio=0.9):
    if not os.path.exists(out_path):
        raise RuntimeError(f"Output path {out_path} does not exist. Make sure out_path is the same as construct_ds")
    entries_train = []
    entries_val = []

    main_pages = []
    other_pages = []
    for root, dirs, files in os.walk(data_path):
        if len(files) == 0:
            continue
        if "react.json" not in files or "actions.json" not in files or "parse.error" in files:
            continue
        if "1.jpg" not in files:
            continue
        idx = 1
        while f"{idx}.jpg" in files:
            idx += 1
        largest_idx = idx - 1
        for i in range(1, largest_idx + 1):
            img_path = os.path.join(root, f"{i}.jpg")
            relative_path = os.path.relpath(img_path, data_path)
            safe_filename = relative_path.replace(os.sep, "_").replace(":", "_")
            safe_filename = f"main_{safe_filename}"
            out_relpath = os.path.join(out_path, safe_filename)
            out_abspath = os.path.abspath(out_relpath)
            if not os.path.exists(out_abspath):
                raise RuntimeError(f"Image {out_abspath} does not exist. Make sure out_path is the same as construct_ds")
            if i == 1:
                main_pages.append(out_abspath)
            else:
                other_pages.append(out_abspath)
    other_pages = random.sample(other_pages, len(other_pages) // 2)
    for pages in [main_pages, other_pages]:
        output = "yes" if pages is main_pages else "no"
        entries = []
        for abspath in pages:
            entry = AlpacaImageEntry(
                instruction=main_page_classification_prompt,
                output=output,
                images=[abspath]
            )
            entries.append(entry)
        random.shuffle(entries)
        split_idx = int(len(entries) * train_ratio)
        entries_train.extend(entries[:split_idx])
        entries_val.extend(entries[split_idx:])

    print(f"main_page_classification entries_train: {len(entries_train)}")
    print(f"main_page_classification entries_val: {len(entries_val)}")

    with open(os.path.join(out_path, "main_page_train.json"), "w", encoding="utf-8") as f:
        json.dump([asdict(entry) for entry in entries_train], f, ensure_ascii=False)
    with open(os.path.join(out_path, "main_page_val.json"), "w", encoding="utf-8") as f:
        json.dump([asdict(entry) for entry in entries_val], f, ensure_ascii=False)


def construct_ds(data_path, single_step_data_path, unexpected_img_path, out_path, factor=0.5, train_ratio=0.9):
    os.makedirs(out_path, exist_ok=True)
    
    # 训练集
    reason_entries_train = []
    shift_entries_train = []
    terminate_entries_train = []
    reason_no_history_entries_train = []
    grounder_entries_train = []
    
    # 验证集
    reason_entries_val = []
    shift_entries_val = []
    terminate_entries_val = []
    reason_no_history_entries_val = []
    grounder_entries_val = []

    current_dir = os.getcwd()
    augment_config_path = os.path.join(current_dir, 'construct_data', 'augment_config.json')
    rules = load_augmentation_rules(augment_config_path)

    unexpected_img_dir = os.path.abspath(args.unexpected_img_path)
    unexpected_img_paths = os.listdir(unexpected_img_dir)
    unexpected_img_paths = [os.path.join(unexpected_img_dir, img) for img in unexpected_img_paths]

    unexpected_img_safe_abspaths = []
    for unexpected_img_path in unexpected_img_paths:
        pil_img = Image.open(unexpected_img_path)
        width, height = pil_img.size
        new_width = int(width * factor)
        new_height = int(height * factor)
        resized_img = pil_img.resize((new_width, new_height), Image.LANCZOS)

        relative_path = os.path.relpath(unexpected_img_path, unexpected_img_dir)
        safe_filename = relative_path.replace(os.sep, "_").replace(":", "_")
        safe_filename = f"unexpected_{safe_filename}"
        out_relpath = os.path.join(out_path, safe_filename)
        resized_img.save(out_relpath)
        out_abspath = os.path.abspath(out_relpath)
        unexpected_img_safe_abspaths.append(out_abspath)

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
        for i, react in enumerate(react_data, 1):
            is_train = random.random() < train_ratio

            augment_rule = augment_data(react, rules)

            # Resize image并保存在同一目录下
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

            # 获取相关参数
            reasoning = react["reasoning"]
            action_type = react["function"]["name"]
            param = react["function"]["parameters"]
            
            output_dict = dict(reasoning=reasoning, action=action_type, parameters=param)
            output = json.dumps(output_dict, ensure_ascii=False)

            # partial_histories是当前action的前几个action
            # 对input类和done类型特殊处理
            if action_type == "input" or action_type == "done":
                min_history_length = min(3, len(history))
                partial_histories = [history[i:] for i in range(len(history) + 1 - min_history_length)]
            else:
                partial_histories = [history[i:] for i in range(len(history) + 1)]
            
            partial_history_entries = []

            for partial_history in partial_histories:
                if len(partial_history) == 0:
                    partial_history_str = "(No history)"
                else:
                    partial_history_str = "\n".join(f"{idx}. {h}" for idx, h in enumerate(partial_history, 1))

                if(isinstance(task_description, list)):
                    weight = calculate_index_weight(i, len(actions))
                    weight = min(weight, len(task_description))
                    random_tasks = random.sample(task_description, weight)
                    for task in random_tasks:
                        instruction = decider_prompt.format(task=task, history=partial_history_str)
                        entry = AlpacaImageEntry(
                            instruction=instruction,
                            output=output,
                            images=[out_abspath]
                        )
                        partial_history_entries.append(entry)
                else:
                    instruction = decider_prompt.format(task=task_description, history=partial_history_str)
                    entry = AlpacaImageEntry(
                        instruction=instruction,
                        output=output,
                        images=[out_abspath]
                    )
                    partial_history_entries.append(entry)

            history.append(output)

            if action_type != "wait" and action_type != "done":
                shifted_history_entry = []
                terminate_history_entry = []
                retry_list1 = [
                    "应用未响应",
                    "上一个操作没有成功",
                    "操作未响应",
                    "上一动作未正常执行"
                ]
                retry_list2 = [
                    "需要重新执行上一个动作",
                    "需要再执行一次上一个操作",
                    "我需要进行重试",
                ]

                retry_reasoning = "，".join(map(random.choice, [retry_list1, retry_list2]))
                retry_output_dict = dict(reasoning=retry_reasoning, action=action_type, parameters=param)
                retry_output = json.dumps(retry_output_dict, ensure_ascii=False)

                terminate_list1 = [
                    "当前页面未按预期加载",
                    "进入了错误的页面",
                    "打开了不合预期的页面",
                    "当前打开了错误页面",
                    "当前页面不合预期"

                ]
                terminate_list2 = [
                    "需要用户介入",
                    "需要用户接管",
                    "任务无法继续执行"
                ]
                terminate_list3 = [
                    "任务提前结束",
                    "中止任务执行"
                ]

                terminate_reasoning = "，".join(map(random.choice, [terminate_list1, terminate_list2, terminate_list3]))
                terminate_output_dict = dict(reasoning=terminate_reasoning, action="done", parameters={})
                terminate_output = json.dumps(terminate_output_dict, ensure_ascii=False)

                history_str = "\n".join(f"{idx}. {h}" for idx, h in enumerate(history, 1))
                if(isinstance(task_description, list)):
                    weight = calculate_index_weight(i, len(actions))
                    weight = min(weight, len(task_description))
                    random_tasks = random.sample(task_description, weight)
                    for task in random_tasks:
                        instruction = decider_prompt.format(task=task, history=history_str)
                        entry = AlpacaImageEntry(
                            instruction=instruction,
                            output=retry_output,
                            images=[out_abspath]
                        )
                        shifted_history_entry.append(entry)

                        unexpected_img_abspath = random.choice(unexpected_img_safe_abspaths)
                        entry = AlpacaImageEntry(
                            instruction=instruction,
                            output=terminate_output,
                            images=[unexpected_img_abspath]
                        )
                        terminate_history_entry.append(entry)
                else:
                    instruction = decider_prompt.format(task=task_description, history=history_str)
                    entry = AlpacaImageEntry(
                        instruction=instruction,
                        output=retry_output,
                        images=[out_abspath]
                    )
                    shifted_history_entry.append(entry)

                    
                    unexpected_img_abspath = random.choice(unexpected_img_safe_abspaths)
                    entry = AlpacaImageEntry(
                        instruction=instruction,
                        output=terminate_output,
                        images=[unexpected_img_abspath]
                    )
                    terminate_history_entry.append(entry)

            # 有历史action训练集
            full_history_entry = partial_history_entries[0]
            partial_history_entries = partial_history_entries[1:]
            partial_history_entries = random.sample(partial_history_entries, min(2, len(partial_history_entries)))
            
            # 按比例分配到训练集和验证集（在增强前分配）
            if is_train:
                num = augment_rule.get("reason", augment_rule.get("other", 1))
                reason_entries_train.extend((partial_history_entries + [full_history_entry]) * num)
                shift_entries_train.extend(shifted_history_entry * num)
                terminate_entries_train.extend(terminate_history_entry * num)
            else:
                reason_entries_val.extend(partial_history_entries + [full_history_entry])
                shift_entries_val.extend(shifted_history_entry)
                terminate_entries_val.extend(terminate_history_entry)

            # 无历史action训练集 (input类型不生成no history数据)
            if action_type != "done" and action_type != "input":
                no_history_entries = []
                if(isinstance(task_description, list)):
                    weight = calculate_index_weight(i, len(actions))
                    weight = min(weight, len(task_description))
                    random_tasks = random.sample(task_description, weight)
                    for task in random_tasks:
                        instruction = decider_prompt_no_history.format(task=task)
                        entry = AlpacaImageEntry(
                            instruction=instruction,
                            output=output,
                            images=[out_abspath]
                        )
                        no_history_entries.append(entry)
                else:
                    instruction = decider_prompt_no_history.format(task=task_description)
                    entry = AlpacaImageEntry(
                        instruction=instruction,
                        output=output,
                        images=[out_abspath]
                    )
                    no_history_entries.append(entry)

                # 按比例分配到训练集和验证集（在增强前分配）
                if is_train:
                    num = augment_rule.get("reason_no_history", augment_rule.get("other", 1))
                    reason_no_history_entries_train.extend(no_history_entries * num)
                else:
                    reason_no_history_entries_val.extend(no_history_entries)

            # grounder训练集
            if action_type == "click":
                action = actions[i - 1]
                coords = [int(action["position_x"]* factor), int(action["position_y"]* factor)]
                bbox = action.get("bounds", None)
                instruction = executor_prompt.format(reasoning=reasoning, description=param["target_element"])
                output = json.dumps(dict(coordinates=coords))
                entry = AlpacaImageEntry(
                    instruction=instruction,
                    output=output,
                    images=[out_abspath]
                )
                
                # 按比例分配到训练集和验证集（在增强前分配）
                if is_train:
                    num = augment_rule.get("grounder", augment_rule.get("other", 1))
                    grounder_entries_train.extend([entry] * num)
                else:
                    grounder_entries_val.append(entry)

                if bbox:
                    bbox = [int(x * factor) for x in bbox]
                    output = json.dumps(dict(bbox=bbox))
                    instruction = executor_prompt_bbox.format(reasoning=reasoning, description=param["target_element"])
                    entry = AlpacaImageEntry(
                        instruction=instruction,
                        output=output,
                        images=[out_abspath]
                    )
                    
                    # 按比例分配到训练集和验证集（在增强前分配）
                    if is_train:
                        num = augment_rule.get("grounder", augment_rule.get("other", 1))
                        grounder_entries_train.extend([entry] * num)
                    else:
                        grounder_entries_val.append(entry)

    if os.path.exists(single_step_data_path):
        for root, dirs, files in os.walk(single_step_data_path):
            if len(files) == 0:
                continue
            if "react.json" not in files:
                continue

            react_path = os.path.join(root, "react.json")
            with open(react_path, "r", encoding="UTF-8") as f:
                react_data = json.load(f)

            tasks_path = os.path.join(root, "tasks.json")
            with open(tasks_path, "r", encoding="UTF-8") as f:
                tasks = json.load(f)

            for i, react in enumerate(react_data, 1):
                is_train = random.random() < train_ratio

                img_path = os.path.join(root, f"{i}.jpg")
                pil_img = Image.open(img_path)
                width, height = pil_img.size
                new_width = int(width * factor)
                new_height = int(height * factor)
                resized_img = pil_img.resize((new_width, new_height), Image.LANCZOS)

                relative_path = os.path.relpath(img_path, single_step_data_path)
                safe_filename = relative_path.replace(os.sep, "_").replace(":", "_")
                safe_filename = f"ss_{safe_filename}"
                out_relpath = os.path.join(out_path, safe_filename)
                resized_img.save(out_relpath)
                out_abspath = os.path.abspath(out_relpath)

                reasoning = react["reasoning"]
                action = react["function"]["name"]
                param = react["function"]["parameters"]
                augment_rule = augment_data(react, rules)

                random_tasks = random.sample(tasks, 1)

                for task in random_tasks:
                    instruction = decider_prompt_no_history.format(task=task)
                    output_dict = dict(reasoning=reasoning, action=action, parameters=param)
                    output = json.dumps(output_dict, ensure_ascii=False)
                    entry = AlpacaImageEntry(
                        instruction=instruction,
                        output=output,
                        images=[out_abspath]
                    )
                    if is_train:
                        num = augment_rule.get("reason_no_history", augment_rule.get("other", 1))
                        reason_no_history_entries_train.extend([entry] * num)
                    else:
                        reason_no_history_entries_val.append(entry)

    # 合并训练集数据
    shift_entries_train = random.sample(shift_entries_train, len(shift_entries_train) // 4)
    shift_entries_val = random.sample(shift_entries_val, len(shift_entries_val) // 4)
    terminate_entries_train = random.sample(terminate_entries_train, len(terminate_entries_train) // 4)
    terminate_entries_val = random.sample(terminate_entries_val, len(terminate_entries_val) // 4)

    print(f"reason_entries_train: {len(reason_entries_train)}")
    print(f"reason_entries_no_history_train: {len(reason_no_history_entries_train)}")
    print(f"shift_entries_train: {len(shift_entries_train)}")
    print(f"terminate_entries_train: {len(terminate_entries_train)}")
    print(f"grounder_entries_train: {len(grounder_entries_train)}")
    
    data = {
        "reason_entries_train": len(reason_entries_train),
        "reason_entries_no_history_train": len(reason_no_history_entries_train),
        "shift_entries_train": len(shift_entries_train),
        "terminate_entries_train": len(terminate_entries_train),
        "grounder_entries_train": len(grounder_entries_train)
    }

    decider_entries_train = [asdict(entry) for entry in reason_entries_train]
    decider_entries_train.extend([asdict(entry) for entry in reason_no_history_entries_train])
    decider_entries_train.extend([asdict(entry) for entry in shift_entries_train])
    decider_entries_train.extend([asdict(entry) for entry in terminate_entries_train])
    # random.shuffle(decider_entries_train)
    
    grounder_entries_train = [asdict(entry) for entry in grounder_entries_train]
    random.shuffle(grounder_entries_train)
    
    # 合并验证集数据
    print(f"reason_entries_val: {len(reason_entries_val)}")
    print(f"reason_entries_no_history_val: {len(reason_no_history_entries_val)}")
    print(f"shift_entries_val: {len(shift_entries_val)}")
    print(f"terminate_entries_val: {len(terminate_entries_val)}")
    print(f"grounder_entries_val: {len(grounder_entries_val)}")

    # 添加验证集统计信息到data字典
    data.update({
        "reason_entries_val": len(reason_entries_val),
        "reason_entries_no_history_val": len(reason_no_history_entries_val),
        "shift_entries_val": len(shift_entries_val),
        "terminate_entries_val": len(terminate_entries_val),
        "grounder_entries_val": len(grounder_entries_val)
    })

    decider_entries_val = [asdict(entry) for entry in reason_entries_val]
    decider_entries_val.extend([asdict(entry) for entry in reason_no_history_entries_val])
    decider_entries_val.extend([asdict(entry) for entry in shift_entries_val])
    decider_entries_val.extend([asdict(entry) for entry in terminate_entries_val])
    random.shuffle(decider_entries_val)
    
    grounder_entries_val_dict = [asdict(entry) for entry in grounder_entries_val]
    random.shuffle(grounder_entries_val_dict)

    # 保存训练集
    with open(os.path.join(out_path, f"general_decider_train.json"), "w", encoding="UTF-8") as f:
        json.dump(decider_entries_train, f, ensure_ascii=False)
    with open(os.path.join(out_path, f"general_grounder_train.json"), "w", encoding="UTF-8") as f:
        json.dump(grounder_entries_train, f, ensure_ascii=False)
    
    # 保存验证集
    with open(os.path.join(out_path, f"general_decider_val.json"), "w", encoding="UTF-8") as f:
        json.dump(decider_entries_val, f, ensure_ascii=False)
    with open(os.path.join(out_path, f"general_grounder_val.json"), "w", encoding="UTF-8") as f:
        json.dump(grounder_entries_val_dict, f, ensure_ascii=False)

    with open(os.path.join(out_path, f"metadata.json"), "w", encoding="UTF-8") as f:
        json.dump(data, f, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Training dataset construction with Alpaca format")
    parser.add_argument("--data_path", type=str, default="data", help="root path of raw data (default: data)")
    parser.add_argument("--ss_data_path", type=str, default="ss_data", help="root path of single-step data (default: ss_data)")
    parser.add_argument("--unexpected_img_path", type=str, default="unexpected_img", help="root path of unexpected image data (default: unexpected_data)")
    parser.add_argument("--out_path", type=str, default="output", help="output path of train dataset (default: output)")
    parser.add_argument("--factor", type=float, default=0.5, help="resize factor for images (default: 0.5)")
    parser.add_argument("--train_ratio", type=float, default=0.9, help="ratio of training data (default: 0.9)")
    args = parser.parse_args()
    construct_ds(
        data_path=args.data_path,
        single_step_data_path=args.ss_data_path,
        unexpected_img_path=args.unexpected_img_path,
        out_path=args.out_path,
        factor=args.factor,
        train_ratio=args.train_ratio,
    )
    construct_main_page_classification_ds(
        data_path=args.data_path,
        out_path=args.out_path,
        factor=args.factor,
        train_ratio=args.train_ratio
    )