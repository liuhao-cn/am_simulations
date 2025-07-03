# AM 大气模拟代码库

这个代码库用于生成大气模拟配置文件并运行 AM 大气传输模拟。

## 目录结构

```
am_simulations/
├── amc_inputs/              # 输入配置文件模板
├── generated_configs/        # 生成的配置文件
├── simulation_results/       # 模拟结果
└── src/                     # 源代码
    ├── generate_am_configs.py
    └── run_am_simulations.py
```

## 使用方法

### 1. 生成配置文件

使用 `generate_am_configs.py` 从模板生成配置文件：

```bash
# 基本用法（使用默认模板）
python src/generate_am_configs.py

# 指定配置文件数量和模板
python src/generate_am_configs.py 10 amc_inputs/tropical_JJA.amc

# 指定最小高度阈值
python src/generate_am_configs.py 10 amc_inputs/tropical_JJA.amc 1000

# 保存原始配置文件
python src/generate_am_configs.py 10 amc_inputs/tropical_JJA.amc 1000 true
```

### 2. 运行模拟

使用 `run_am_simulations.py` 运行批量模拟：

```bash
# 运行所有模板的模拟
python src/run_am_simulations.py
```

## 可用的配置文件模板

在 `amc_inputs/` 目录中有以下配置文件模板：

- **热带地区**：`tropical_DJF.amc`, `tropical_JJA.amc`, `tropical_MAM.amc`, `tropical_SON.amc`
- **北半球中纬度**：`northern_midlatitude_annual.amc`, `northern_midlatitude_DJF.amc`, `northern_midlatitude_JJA.amc`, `northern_midlatitude_MAM.amc`, `northern_midlatitude_SON.amc`
- **南极地区**：`SPole_DJF_50.amc`, `SPole_JJA_50.amc`, `SPole_MAM_50.amc`, `SPole_SON_50.amc`
- **阿里地区**：`Ali_B_DJF_50.amc`, `Ali_B_JJA_50.amc`, `Ali_B_MAM_50.amc`, `Ali_B_SON_50.amc`

## 输出文件

### 生成的配置文件
- 位置：`generated_configs/`
- 格式：`config_XXXXXX.amc`
- 包含：随机生成的大气参数

### 模拟结果
- 位置：`simulation_results/`
- 格式：二进制文件（`.bin`）和元数据文件（`_meta.txt`）
- 内容：频率、透射率、亮温数据

### 图表
- `simulation_results/transmittance.png`：透射率分布图
- `simulation_results/brightness_temperature.png`：亮温分布图
- `generated_configs/profiles.png`：大气参数分布图

## 参数说明

### generate_am_configs.py 参数
- `num_configs`：生成的配置文件数量（默认：5）
- `config_template`：模板文件路径（默认：`amc_inputs/northern_midlatitude_annual.amc`）
- `min_height`：最小高度阈值，低于此高度的层将被忽略（默认：None）
- `save_original`：是否保存原始配置文件（默认：False）

### run_am_simulations.py 参数
- `NUM_CONFIGS_PER_TEMPLATE`：每个模板生成的配置文件数量（默认：100）
- `START_FREQ`：起始频率，GHz（默认：30）
- `END_FREQ`：结束频率，GHz（默认：500）
- `FREQ_RES`：频率分辨率，MHz（默认：10）
- `ZENITH_ANGLE`：天顶角，度（默认：0.0）
- `H2O_SCALE_MIN/MAX`：水汽缩放因子范围（默认：0.1-1.0）
- `MIN_HEIGHT`：最小高度阈值（默认：None）

## 注意事项

1. 确保 AM 程序已正确安装并可在命令行中使用
2. 生成的配置文件会保留在 `generated_configs/` 目录中
3. 模拟结果会自动转换为二进制格式以节省空间
4. 如果配置文件数量过多，绘图时会随机选择部分文件进行显示 