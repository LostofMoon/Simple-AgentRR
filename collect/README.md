## 数据收集

### 数据格式

通过人工/自动收集工具，收集每个action前的手机截图，并记录每个action的信息，并汇总到一个actions.json文件中。action格式如下：
```
{{
    "app_name": str
    "task_description": ["The description of the task list."],
    "action_count": "The count of the actions.",
    "actions": [
        {{
            "type": "The type of the action",
            "parameters": "etc.",  
        }},
        {{
            "type": "click",
            "position_x": "x-coordinate of click",
            "position_y": "y-coordinate of click action",
            "bounds": "the bound of the clicked element",
        }},
        {{
            "type": "swipe",
            "press_position_x": "x-coordinate of press",
            "press_position_y": "y-coordinate of press",
            "release_position_x": "x-coordinate of release",
            "release_position_y": "y-coordinate of release",
            "direction": "The direction of the user's swipe gesture. UP: swipe finger upward to scroll content up and reveal content below. DOWN: swipe finger downward to scroll content down and reveal content above. LEFT: swipe finger leftward to scroll content left. RIGHT: swipe finger rightward to scroll content right."
        }},
        {{
            "type": "input",
            "text": "The text to input",
        }},
        {{
            "type": "done"
        }},
        {{
            "type": "wait"
        }},
    ]
}}
```

### 手动数据收集

**启动服务器**
```bash
python -m collect.manual_collection.server
```
启动成功后，访问 http://localhost:9000 进入Web操作界面。

**操作步骤**

1. **开始收集**：在Web界面点击 **开始收集** 按钮

2. **配置应用信息**：在弹出的 **应用信息配置** 窗口中填写：
- **应用名称**：如 "饿了么"、"微信"、"淘宝" 等
- **任务类型**：如 “tpye1”、 “tpye2” 等，具体参考收集任务文档

3. **输入任务描述**
   - 在 **任务描述** 窗口中详细描述当前要执行的具体任务
   - 确保描述清晰明确，便于后续数据分析和模型训练

4. **执行操作**
   - 在Web界面的手机截图上进行以下操作：
     - **点击操作**：直接点击截图上的目标位置
     - **滑动操作**：按住鼠标左键拖拽到目标位置后松开（注意保持在屏幕范围内）
     - **文本输入**：点击 **文本输入** 按钮，在弹出框中输入文本内容

5. **保存数据**
   - 完成一个任务序列后，根据需要选择：
     - **下一条数据**：继续收集同类型任务的更多数据样本
     - **结束收集**：完成当前收集会话并保存所有数据
     - **删除任务**：丢弃当前数据（用于处理错误操作或无效数据）

**数据存储格式**

收集的数据自动保存到 `collect/manual_collection/data/` 目录，按以下层级结构组织：

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
│   │   │   └── ...            # 第2条数据
│   │   └── ...
│   └── <其他任务类型>/
└── <其他应用名称>/
```

每个数据样本包含：
- **截图序列**：记录每个操作步骤前的界面状态
- **actions.json**：包含完整的操作序列、任务描述和应用信息

### 自动数据收集
先在 `/collect/auto_collection/task.json` 写入需要完成的任务列表，格式为字符串数组：
```json
[
    "在淘宝搜索iPhone手机",
    "在微信给张三发消息说你好",
    "在b站关注up主李四"
]
```

运行自动数据收集程序：
```bash
python -m collect.auto_collection.server --model <模型名称> --api_key <API密钥> --base_url <API基础URL> [--max_steps <最大步数>]
```

**必需参数：**
- `--model`：LLM模型名称
- `--api_key`：API密钥
- `--base_url`：API基础URL

**可选参数：**
- `--max_steps`：每个任务的最大执行步数，默认为 15

**工作流程：**
1. 程序读取 `task.json` 中的任务列表
2. 对每个任务：
   - AI智能体根据任务描述自动选择并启动相应的应用
   - 自动执行操作序列（点击、滑动、输入等）
   - 每步操作前自动截图并记录操作信息
   - 达到最大步数或任务完成时停止
3. 自动保存数据到指定目录

**存储数据格式：**
- 原始日志数据存储在 `/collect/auto_collection/data_log/` 
- 转换后的标准格式数据存储在 `/collect/auto_collection/data/`
- 数据结构与手动收集保持一致，包含截图序列和 `actions.json` 文件