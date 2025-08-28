# Simple-AgentRR: 移动设备AI智能体数据收集与训练平台

## 环境配置
```bash
conda create -n agentRR python=3.10
conda activate agentRR
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia -y
python -m pip install paddlepaddle-gpu==3.1.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
pip install paddleocr==2.10.0 ultralytics transformers==4.47.0 Pillow opencv-python numpy scipy supervision langchain-openai langchain-core
pip install openai uiautomator2 pillow
pip install fastapi uvicorn

for f in icon_detect/{train_args.yaml,model.pt,model.yaml} ; do huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights; done
```

## 手机配置
- 在Android设备上安装项目根目录中的 `ADBKeyboard.apk` 文件，必须开启开发者选项
- 使用USB数据线连接手机和电脑
- 手机上会弹出USB调试授权提示，点击 **允许**

## 项目启动
详情见子目录 README.md

### 手动数据收集
```bash
python -m manual_collection.server
```
启动成功后，访问 http://localhost:9000 查看web界面

### 自动数据收集
先在 `/auto_collection/task.json` 写入需要完成的任务列表
```bash
python -m auto_collection.server
```

### 数据标注
```bash
python -m annotation.auto_annotate
```

### 数据构建
```bash
python -m construct_data.sft
python -m construct_data.dpo
```

### Simple-AgentRR 智能体
```bash
python -m simple_agentRR.simple_agentRR
```

## 项目结构

- `annotation/` - 数据标注模块，自动为收集的数据添加视觉标注
- `auto_collection/` - 自动数据收集模块，通过AI智能体自动执行任务并收集数据
- `construct_data/` - 数据构建模块，将原始数据转换为训练格式
- `manual_collection/` - 手动数据收集模块，提供Web界面进行人工数据收集
- `simple_agentRR/` - 核心智能体模块，实现移动设备的AI自动化操作
- `prompts/` - 提示词模板
- `utils/` - 工具函数库
- `weights/` - 模型权重文件

## 详细文档

每个子模块都有独立的README文档，详细说明使用方法和配置选项。请参考对应目录下的README.md文件。