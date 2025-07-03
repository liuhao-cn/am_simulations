import os
import subprocess
import platform
import numpy as np
import matplotlib.pyplot as plt
import random
import time
import struct
import glob

# 运行参数设置
NUM_CONFIGS_PER_TEMPLATE = 100     # 每个配置文件模板生成的配置文件数量
START_FREQ = 30                    # 起始频率，GHz
END_FREQ = 500                     # 结束频率，GHz
FREQ_RES = 100                     # MHz
ZENITH_ANGLE = 0.0                 # 天顶角，度
H2O_SCALE_MIN = 0.1                # 水汽缩放因子最小值
H2O_SCALE_MAX = 1.0                # 水汽缩放因子最大值
MIN_HEIGHT = None                  # 最小高度阈值，None表示不限制
MAX_PLOT_CONFIGS = 100             # 最大绘图配置数量
OUTPUT_DIR = 'simulation_results'  # 统一输出目录

# 注意：生成的 amc 配置文件将保留在 generated_configs 目录中，不会被自动删除

def save_binary_data(data, filename):
    """
    将数据保存为二进制格式
    data: numpy数组，形状为 (n_points, 3)
    filename: 输出文件名
    """
    # 确保数据类型为 float64
    data = data.astype(np.float64)
    
    # 按行优先顺序保存
    with open(filename, 'wb') as f:
        # 直接保存整个数组，按行优先顺序
        f.write(data.tobytes())
    
    # 保存元数据
    meta_filename = filename.replace('.bin', '_meta.txt')
    with open(meta_filename, 'w') as f:
        f.write(f'Shape: {data.shape}\n')
        f.write(f'Data type: float64\n')
        f.write(f'Column order: frequency, transmittance, brightness_temperature\n')
        f.write(f'Storage order: row-major\n')

def load_binary_data(filename):
    """
    从二进制文件读取数据
    filename: 二进制文件名
    返回: numpy数组，形状为 (n_points, 3)
    """
    # 读取元数据以获取形状信息
    meta_filename = filename.replace('.bin', '_meta.txt')
    shape = None
    with open(meta_filename, 'r') as f:
        for line in f:
            if line.startswith('Shape:'):
                shape_str = line.split('Shape:')[1].strip()
                # 解析形状字符串，例如 "(471, 3)"
                shape_str = shape_str.replace('(', '').replace(')', '')
                shape = tuple(map(int, shape_str.split(', ')))
                break
    
    if shape is None:
        raise ValueError("无法从元数据文件读取形状信息")
    
    # 读取二进制数据
    with open(filename, 'rb') as f:
        data_bytes = f.read()
    
    # 转换为numpy数组
    data = np.frombuffer(data_bytes, dtype=np.float64)
    data = data.reshape(shape)
    
    return data

def find_amc_files():
    """
    查找 amc_inputs 文件夹下的所有.amc配置文件
    返回: .amc文件列表
    """
    amc_dir = "amc_inputs"
    if not os.path.exists(amc_dir):
        print(f"错误：{amc_dir} 目录不存在！")
        return []
    
    amc_files = glob.glob(os.path.join(amc_dir, "*.amc"))
    return amc_files

def run_am_simulation():
    # 查找所有.amc配置文件
    amc_files = find_amc_files()
    if not amc_files:
        print("未找到任何.amc配置文件！")
        return
    
    print(f"找到 {len(amc_files)} 个.amc配置文件：")
    for file in amc_files:
        print(f"  - {file}")
    
    # 创建统一输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 记录所有配置使用的水汽缩放系数
    all_h2o_scales = {}
    total_configs = 0
    
    # 记录开始时间
    start_time = time.time()
    
    # 处理每个.amc配置文件
    for template_idx, config_template in enumerate(amc_files):
        print(f"\n处理配置文件模板 {template_idx + 1}/{len(amc_files)}: {config_template}")
        
        # 为当前模板生成配置文件
        print(f'正在为 {config_template} 生成 {NUM_CONFIGS_PER_TEMPLATE} 个配置文件...')
        if MIN_HEIGHT is not None:
            print(f'将屏蔽高度低于 {MIN_HEIGHT} m 的层')
        
        # 构建命令参数
        cmd_args = ['python', 'src/generate_am_configs.py', str(NUM_CONFIGS_PER_TEMPLATE), config_template]
        if MIN_HEIGHT is not None:
            cmd_args.append(str(MIN_HEIGHT))
        else:
            cmd_args.append('None')
        # 添加参数表示不保存原始配置文件
        cmd_args.append('False')
        
        ret = subprocess.run(cmd_args, capture_output=True, text=True)
        if ret.returncode != 0:
            print(f'为 {config_template} 生成配置文件失败：')
            print(ret.stderr)
            continue
        print(f'{config_template} 的配置文件生成完成。')
        
        # 记录当前模板的水汽缩放系数
        template_h2o_scales = []
        
        # 运行当前模板的所有配置文件
        for i in range(NUM_CONFIGS_PER_TEMPLATE):
            config_file = f'generated_configs/config_{i:06d}.amc'
            # 使用模板文件名+序号作为输出文件名
            template_name = os.path.splitext(os.path.basename(config_template))[0]  # 去掉路径和.amc扩展名
            output_file = f'{OUTPUT_DIR}/{template_name}_{i:06d}.out'
            
            # 生成随机水汽缩放系数
            h2o_scale = random.uniform(H2O_SCALE_MIN, H2O_SCALE_MAX)
            template_h2o_scales.append(h2o_scale)
            
            # 构建命令
            cmd = [
                'am',
                config_file,
                f'{START_FREQ}',
                'GHz',
                f'{END_FREQ}',
                'GHz',
                f'{FREQ_RES}',
                'MHz',
                f'{ZENITH_ANGLE}',
                'deg',
                f'{h2o_scale}'
            ]
            
            print(f'处理配置文件 {template_name}_{i:06d}... (H2O scale: {h2o_scale:.3f})')
            
            # 运行命令并重定向输出
            try:
                with open(output_file, 'w') as f:
                    subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True)
                print(f'配置文件 {template_name}_{i:06d} 处理完成')
                    
            except subprocess.CalledProcessError as e:
                print(f'处理配置文件 {template_name}_{i:06d} 时出错：')
                print(e.stderr)
                continue
        
        # 保存当前模板的水汽缩放系数
        all_h2o_scales[config_template] = template_h2o_scales
        total_configs += NUM_CONFIGS_PER_TEMPLATE
        
        # 保留生成的配置文件（不再自动删除）
        print(f"{config_template} 的配置文件已保留在 generated_configs 目录中")
    
    # 计算总时间和平均时间
    total_time = time.time() - start_time
    avg_time = total_time / total_configs
    
    print(f'\n时间统计：')
    print(f'总运行时间：{total_time:.2f} 秒')
    print(f'平均每次模拟时间：{avg_time:.2f} 秒')
    print('所有模拟已完成，开始转换为二进制格式...')
    
    # 统一转换为二进制格式并删除文本文件
    convert_to_binary_and_cleanup()
    
    # 保存水汽缩放系数记录
    with open(f'{OUTPUT_DIR}/h2o_scales.txt', 'w') as f:
        f.write('Template\tConfiguration\tH2O Scale\n')
        for template, scales in all_h2o_scales.items():
            template_name = os.path.splitext(os.path.basename(template))[0]  # 去掉路径和扩展名
            for i, scale in enumerate(scales):
                f.write(f'{template_name}\t{i:06d}\t{scale:.6f}\n')
    
    # 分析结果并绘图
    plot_results(all_h2o_scales)

def plot_results(all_h2o_scales):
    """
    读取所有二进制结果文件并绘制第2、3列数据
    """
    # 获取所有输出文件
    output_files = glob.glob(f'{OUTPUT_DIR}/*.bin')
    
    if not output_files:
        print("未找到任何二进制结果文件！")
        return
    
    # 限制绘图数量
    if len(output_files) > MAX_PLOT_CONFIGS:
        print(f'结果数量超过 {MAX_PLOT_CONFIGS} 个，随机选择 {MAX_PLOT_CONFIGS} 个进行绘图...')
        plot_files = random.sample(output_files, MAX_PLOT_CONFIGS)
    else:
        plot_files = output_files
    
    # 创建图形
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    fig2, ax2 = plt.subplots(figsize=(12, 8))
    
    # 设置颜色循环
    colors = plt.cm.viridis(np.linspace(0, 1, len(plot_files)))
    
    # 读取并绘制选定的结果文件
    for idx, binary_file in enumerate(plot_files):
        try:
            # 读取二进制数据
            data = load_binary_data(binary_file)
            freq = data[:, 0]  # 第1列：频率
            tx = data[:, 1]    # 第2列：透射率
            tb = data[:, 2]    # 第3列：亮温
            
            # 获取文件名（不含路径和扩展名）
            filename = os.path.basename(binary_file)
            config_name = os.path.splitext(filename)[0]
            
            # 绘制透射率
            ax1.plot(freq, tx, color=colors[idx], linewidth=0.5, 
                    label=config_name, alpha=0.7)
            
            # 绘制亮温
            ax2.plot(freq, tb, color=colors[idx], linewidth=0.5, 
                    label=config_name, alpha=0.7)
            
        except Exception as e:
            print(f'处理结果文件 {binary_file} 时出错：{str(e)}')
            continue
    
    # 设置透射率图
    ax1.set_xlabel('Frequency (GHz)')
    ax1.set_ylabel('Transmittance')
    ax1.set_title('Atmospheric Transmittance')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 设置亮温图
    ax2.set_xlabel('Frequency (GHz)')
    ax2.set_ylabel('Brightness Temperature (K)')
    ax2.set_title('Brightness Temperature')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 调整布局并保存
    plt.tight_layout()
    fig1.savefig(f'{OUTPUT_DIR}/transmittance.png', dpi=300, bbox_inches='tight')
    fig2.savefig(f'{OUTPUT_DIR}/brightness_temperature.png', dpi=300, bbox_inches='tight')
    plt.close('all')
    
    print('结果分析完成，图表已保存到 simulation_results 目录。')

def convert_to_binary_and_cleanup():
    """
    将所有文本结果文件转换为二进制格式并删除原文件
    """
    print('正在转换为二进制格式...')
    converted_count = 0
    
    # 查找所有.out文件
    out_files = glob.glob(f'{OUTPUT_DIR}/*.out')
    
    for out_file in out_files:
        binary_file = out_file.replace('.out', '.bin')
        
        try:
            # 读取文本文件并转换为二进制格式
            data = np.loadtxt(out_file, comments='#')
            save_binary_data(data, binary_file)
            
            # 删除文本文件
            os.remove(out_file)
            converted_count += 1
            
        except Exception as e:
            print(f'转换文件 {out_file} 时出错：{str(e)}')
            continue
    
    print(f'成功转换 {converted_count} 个文件为二进制格式并删除原文本文件。')

if __name__ == '__main__':
    run_am_simulation() 