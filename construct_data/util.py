import os
import json
import re
from functools import reduce

def load_augmentation_rules(config_path="augment_config.json"):
    """读取数据扩充配置文件，返回规则列表"""
    if not os.path.exists(config_path):
        print(f"警告：配置文件 '{config_path}' 不存在，使用默认规则（无扩充）。")
        return []
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        for rule in rules:
            if not isinstance(rule.get("dir"), list):
                raise ValueError(f"无效规则：{rule}，dir 必须是列表")
            if not isinstance(rule.get("pattern"), str):
                raise ValueError(f"无效规则：{rule}，pattern 必须是字符串")
            if not isinstance(rule.get("multiplier"), dict):
                raise ValueError(f"无效规则：{rule}，multiplier 必须是字典")
            rule["compiled_pattern"] = re.compile(rule["pattern"])
        return rules
    except Exception as e:
        print(f"读取配置文件失败：{e}，使用默认规则（无扩充）。")
        return []

def augment_data(action, rules):
    # 检查每个规则
    for rule in rules:
        try:
            field_value = reduce(lambda d, k: d[k], rule["dir"], action)
        except (KeyError, TypeError):
            continue
        if not isinstance(field_value, str):
            continue
        if rule["compiled_pattern"].search(field_value):
            return rule["multiplier"]
    return {"other": 1}