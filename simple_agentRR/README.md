# Simple-AgentRR 智能体模块

这是项目的核心模块，实现了一个能够理解自然语言指令并在移动设备上自动执行任务的AI智能体。智能体使用多模态大语言模型来理解屏幕内容并做出操作决策。

## vLLM
下载好 `decider` 和 `grounder` 两个模型后，使用vLLM部署模型推理，版本为 `0.9.1`，`transformers` 版本为 `4.51.3`:
```bash
vllm serve decider/ --port 8000
vllm serve grounder/ --port 8001
```

## 快速开始

### 环境配置
详情查看根目录下的README.md

### 设置任务
在/simple_agentRR/task.json中写入要测试的列表

### 启动
在根目录下运行下述指令：
```bash
python -m simple_agentRR.simple_agentRR
```