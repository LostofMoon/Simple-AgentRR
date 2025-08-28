# 数据标注模块 (Annotation)

这个模块负责为收集到的原始数据添加视觉标注，将动作数据转换为带有视觉提示的训练数据。

## 数据标注流程
通过 `manual_collection` 或者 `auto_collection` 收集到的data，其核心结构为，最小的子目录有如下结构：
```
dir1/
├── 1.jpg          # 第1个操作前的截图
├── 2.jpg          # 第2个操作前的截图
├── ...
└── actions.json   # 操作记录和任务信息
```

## 快速开始

### 自动标注
运行`auto_annotate.py`，需要有一个使用OpenAI API接口格式的云端模型服务，参数如下：
- `--data_path`：可选，表示原始轨迹数据存储路径，默认当前目录下的 `data` 目录。
- `--model`：必选，模型服务的模型名
- `--api_key`：必选，模型服务的API Key
- `--base_url`：必选，模型服务的Base URL
- 示例：
```bash
python -m annotation.auto_annotate --data_path <数据路径> --model <模型名称> --api_key <api key> --base_url <base url>
```
### react.json
运行完成后， `data` 目录下的每条轨迹的子目录中，将会多出一个 `react.json` 文件，其格式如下：
```
[
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "click",
            "parameters": {
                "target_element": "click的highlevel描述"
            }
        }
    },
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "swipe",
            "parameters": {
                "direction": "UP, DOWN, LEFT, RIGHT"
            }
        }
    },
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "input",
            "parameters": {
                "text": "input的内容"
            }
        }
    },
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "done",
            "parameters": {}
        }
    },
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "wait",
            "parameters": {}
        }
    }
]
```