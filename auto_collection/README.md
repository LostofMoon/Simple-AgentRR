# 自动数据收集模块 (Auto Collection)

这个模块通过AI智能体自动执行移动应用任务，收集操作数据用于训练。智能体能够理解任务描述，自主规划并执行一系列操作步骤。

## 环境配置
详情查看根目录下的README.md

### 手机配置
- 在Android设备上安装项目根目录中的 `ADBKeyboard.apk` 文件
- 使用USB数据线连接手机和电脑
- 手机上会弹出USB调试授权提示，点击 **允许**

## 快速开始

### 配置任务
在 `task.json` 文件中定义要执行的任务：
```json
[
   "任务描述1",
   "任务描述2",
   "任务描述3"
]
```

### 项目启动
在根目录下运行指令
```bash
python -m auto_collection.server
```

## 数据存储结构

在数据收集过程中会生成log，存储在/auto_collection/data_log，数据存储在/auto_collection/data，按照以下结构：
```
data/
├── <应用名称>/
│   ├── <任务类型>/
│   │   ├── 1/
│   │   │   ├── 1.jpg          # 第1个操作前的截图
│   │   │   ├── 2.jpg          # 第2个操作前的截图
│   │   │   ├── ...
│   │   │   └── actions.json   # 操作记录和任务信息
│   │   ├── 2/
│   │   │   └── ...
│   │   └── ...
│   └── <其他任务类型>/
└── <其他应用名称>/
```
结构与手动收集数据一致


### actions.json 文件格式
```json
{
    "app_name": "饿了么",
    "task_type": "帮我点<店名>的<食品名称>",
    "task_description": "在饿了么APP中点击麦当劳的巨无霸汉堡",
    "action_count": 3,
    "actions": [
        {
            "type": "click",
            "position_x": 500,
            "position_y": 300,
            "bounds": [450, 250, 550, 350]
        },
        {
            "type": "swipe",
            "press_position_x": 500,
            "press_position_y": 800,
            "release_position_x": 500,
            "release_position_y": 400,
            "direction": "up"
        },
        {
            "type": "input",
            "text": "巨无霸"
        },
        {
            "type": "done"
        }
    ]
}
```