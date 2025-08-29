# MobiAgent

<div align="center">
<p align="center">
  <img src="assets/logo.png"/>
</p>
</div>

## 📢News
- `[2025.8.29]`🔥🔥 We've open-sourced the MobiAgent.

## 📊Results

<div align="center">
<p align="center">
  <img src="assets/result1.png" width="30%" style="margin-right: 15px;"/>
  <img src="assets/result2.png" width="30%" style="margin-right: 15px;"/>
  <img src="assets/result3.png" width="30%"/>
</p>
</div>


## 环境配置
```bash
conda create -n MobiMind python=3.10
conda activate MobiMind

pip install -r requirements.txt

# 下载OmniParser模型权重
for f in icon_detect/{train_args.yaml,model.pt,model.yaml} ; do huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights; done

# 如果需要使用gpu加速ocr，需要根据cuda版本，手动安装paddlepaddle-gpu
# 详情参考 https://www.paddlepaddle.org.cn/install/quick，例如cuda 11.8版本：
python -m pip install paddlepaddle-gpu==3.1.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

```

## 手机配置
- 在Android设备上下载并安装 [ADBKeyboard](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk)
- 在Android设备上，开启开发者选项，并允许USB调试
- 使用USB数据线连接手机和电脑

## 项目结构

- `agent_rr/` - Agent Record & Replay框架
- `collect/` - 数据收集、标注、处理与导出工具
- `runner/` - 智能体执行器，通过ADB连接手机、执行任务、并记录执行轨迹
- `MobiFlow/` - 基于里程碑DAG的智能体评测基准
- `deployment/` - MobiAgent移动端应用的服务部署方式

## 子模块使用方式
详细使用方式见各子模块目录下的 `README.md` 文件

## 快速启动

### APP下载
[下载连接](https://www.baidu.com)

<!-- TODO: 怎么使用 -->

### ADB调用

#### 模型部署
下载好 `decider`、`grounder` 和 `planner` 三个模型后，使用 vLLM 部署模型推理服务：

**默认端口部署**
```bash
vllm serve IPADS-SAI/MobiMind-Decider-7B --port <decider port>
vllm serve IPADS-SAI/MobiMind-Grounder-3B --port <grounder port>
vllm serve Qwen/Qwen3-4B-Instruct --port <planner port>
```

**注意事项**
- 确保部署的服务端口与后续启动 MobiMind-Agent 时指定的端口参数一致
- 如果使用非默认端口，需要在启动 Agent 时通过 `--decider_port`、`--grounder_port`、`--planner_port` 参数指定对应端口

#### 设置任务
在 `runner/mobiagent/task.json` 中写入要测试的任务列表

#### 项目启动

**基本启动**（使用默认配置）
```bash
python -m runner.mobiagent.mobiagent
```

**自定义配置启动**
```bash
python -m runner.mobiagent.mobiagent --service_ip <服务IP> --decider_port <决策服务端口> --grounder_port <定位服务端口> --planner_port <规划服务端口>
```

**参数说明**
- `--service_ip`：服务IP（默认：`localhost`）
- `--decider_port`：决策服务端口（默认：`8000`）
- `--grounder_port`：定位服务端口（默认：`8001`）
- `--planner_port`：规划服务端口（默认：`8002`）