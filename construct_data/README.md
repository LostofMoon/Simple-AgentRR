## 数据构建

数据构建模块将标注后的数据转换为适合模型训练的格式，支持监督微调（SFT）数据集的生成。

### 启动命令

```bash
python -m construct_data.sft --data_path <原始数据路径> --ss_data_path <单步数据路径> --unexpected_img_path <意外图片路径> --out_path <输出路径> [--factor <缩放因子>] [--train_ratio <训练比例>]
```

### 参数说明

**必需参数**
- `--data_path`：原始轨迹数据存储路径（默认：`data`）
- `--ss_data_path`：单步数据存储路径（默认：`ss_data`）
- `--unexpected_img_path`：意外图片数据路径（默认：`unexpected_img`）
- `--out_path`：训练数据集输出路径（默认：`output`）

**可选参数**
- `--factor`：图片缩放因子，用于减小图片尺寸（默认：`0.5`）
- `--train_ratio`：训练集与验证集的划分比例（默认：`0.9`）