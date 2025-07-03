import os
import shutil
import random
import matplotlib.pyplot as plt
import numpy as np
import sys

class AMConfigGenerator:
    def __init__(self, config_template, output_dir='generated_configs', min_height=None, save_original=False):
        self.config_template = config_template
        self.output_dir = output_dir
        self.min_height = min_height  # 添加最小高度参数
        self.save_original = save_original  # 是否保存原始配置文件
        os.makedirs(output_dir, exist_ok=True)
        
        # 读取原始配置文件，提取层信息
        self.layers = self._parse_original_config()
        
        # 保存原始配置文件（仅在需要时）
        if self.save_original:
            self._save_original_config()
        
    def _parse_original_config(self):
        """
        解析原始配置文件，提取每层的信息
        返回: 包含层信息的列表
        """
        layers = []
        current_layer = None
        
        with open(self.config_template, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('layer'):
                    if current_layer:
                        layers.append(current_layer)
                    current_layer = {
                        'type': line.split()[1],
                        'height': None,
                        'Pbase': None,
                        'Tbase': None,
                        'h2o_vmr': None,
                        'o3_vmr': None,
                        'lineshape': None  # 添加lineshape字段
                    }
                elif line.startswith('Pbase'):
                    current_layer['Pbase'] = float(line.split()[1])
                    # 从注释中提取高度
                    if '#' in line:
                        height_str = line.split('#')[1].strip()
                        if 'z =' in height_str:
                            current_layer['height'] = float(height_str.split('=')[1].strip().split()[0])
                elif line.startswith('Tbase'):
                    current_layer['Tbase'] = float(line.split()[1])
                elif line.startswith('lineshape'):
                    current_layer['lineshape'] = line.split()[1]  # 保存lineshape参数
                elif 'h2o vmr' in line:
                    current_layer['h2o_vmr'] = float(line.split()[-1])
                elif 'o3 vmr' in line:
                    current_layer['o3_vmr'] = float(line.split()[-1])
        
        if current_layer:
            layers.append(current_layer)
            
        return layers
        
    def _save_original_config(self):
        """
        保存原始配置文件
        """
        original_config_path = os.path.join(self.output_dir, 'original_config.amc')
        shutil.copy2(self.config_template, original_config_path)
        
    def _calculate_layer_boundaries(self):
        """
        计算每层的参数边界
        返回: 包含每层参数边界的字典
        """
        boundaries = []
        for i in range(len(self.layers)-1):
            current = self.layers[i]
            next_layer = self.layers[i+1]
            
            boundary = {
                'height': current['height'],
                'h2o_vmr': {
                    'min': min(current['h2o_vmr'], next_layer['h2o_vmr']),
                    'max': max(current['h2o_vmr'], next_layer['h2o_vmr'])
                },
                'o3_vmr': {
                    'min': min(current['o3_vmr'], next_layer['o3_vmr']),
                    'max': max(current['o3_vmr'], next_layer['o3_vmr'])
                },
                'Tbase': {
                    'min': min(current['Tbase'], next_layer['Tbase']),
                    'max': max(current['Tbase'], next_layer['Tbase'])
                }
            }
            boundaries.append(boundary)
        return boundaries
        
    def generate_config(self, config_id):
        """
        生成单个配置文件
        """
        # 生成随机参数
        boundaries = self._calculate_layer_boundaries()
        
        # 为每层生成随机值
        layers = []
        for i, boundary in enumerate(boundaries):
            # 如果设置了最小高度，跳过低于该高度的层
            if self.min_height is not None and boundary['height'] < self.min_height:
                continue
                
            layer = {
                'type': self.layers[i]['type'],
                'height': boundary['height'],
                'Pbase': self.layers[i]['Pbase'],
                'lineshape': self.layers[i]['lineshape'],  # 保持原始lineshape参数
                'h2o_vmr': random.uniform(boundary['h2o_vmr']['min'], 
                                        boundary['h2o_vmr']['max']),
                'o3_vmr': random.uniform(boundary['o3_vmr']['min'], 
                                       boundary['o3_vmr']['max']),
                'Tbase': random.uniform(boundary['Tbase']['min'], 
                                      boundary['Tbase']['max'])
            }
            layers.append(layer)
            
        # 添加最后一层（如果高度符合要求）
        if self.min_height is None or self.layers[-1]['height'] >= self.min_height:
            last_layer = {
                'type': self.layers[-1]['type'],
                'height': self.layers[-1]['height'],
                'Pbase': self.layers[-1]['Pbase'],
                'lineshape': self.layers[-1]['lineshape'],  # 保持原始lineshape参数
                'h2o_vmr': self.layers[-1]['h2o_vmr'],
                'o3_vmr': self.layers[-1]['o3_vmr'],
                'Tbase': self.layers[-1]['Tbase']
            }
            layers.append(last_layer)
            
        # 生成配置文件
        config_path = os.path.join(self.output_dir, f'config_{config_id:06d}.amc')
        self._write_config_file(config_path, layers)
        return config_path, layers
        
    def _write_config_file(self, config_path, layers):
        """
        写入配置文件
        """
        with open(config_path, 'w') as f:
            # 写入文件头
            f.write("# Generated AM configuration file\n")
            f.write("#\n")
            f.write("f %1 %2  %3 %4  %5 %6\n")
            f.write("output f GHz  tx  Tb K\n")
            f.write("za %7 %8\n")
            f.write("tol 1e-4\n")
            f.write("\n")
            f.write("Nscale troposphere h2o %9\n")
            f.write("\n")
            f.write("T0 2.7 K\n")
            f.write("\n")
            
            # 写入层信息
            for layer in layers:
                f.write(f"layer {layer['type']}\n")
                f.write(f"Pbase {layer['Pbase']} mbar   # z = {layer['height']} m\n")
                f.write(f"Tbase {layer['Tbase']} K\n")
                if layer['lineshape'] is not None:  # 只有当lineshape不为None时才写入
                    f.write(f"lineshape {layer['lineshape']}\n")
                f.write("column dry_air vmr\n")
                f.write(f"column h2o vmr {layer['h2o_vmr']:.2e}\n")
                f.write(f"column o3 vmr {layer['o3_vmr']:.2e}\n")
                f.write("\n")
        
    def plot_profiles(self, configs_data):
        """
        绘制参数分布图
        configs_data: 包含所有配置数据的列表
        """
        # 限制最多绘制 100 个配置文件
        if len(configs_data) > 100:
            print(f'配置文件数量超过 100 个，随机选择 100 个进行绘图...')
            indices = random.sample(range(len(configs_data)), 100)
            configs_data = [configs_data[i] for i in indices]
        
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
        
        # 绘制温度分布
        for i, data in enumerate(configs_data):
            heights = [layer['height'] for layer in data]
            temps = [layer['Tbase'] for layer in data]
            ax1.plot(temps, heights, label=f'Config {i:06d}')
        # 添加原始配置（只取前N-1个点）
        N = len(configs_data[0])
        heights = [layer['height'] for layer in self.layers[:N]]
        temps = [layer['Tbase'] for layer in self.layers[:N]]
        ax1.plot(temps, heights, 'k--', label='Original')
        ax1.set_xlabel('Temperature (K)')
        ax1.set_ylabel('Height (m)')
        ax1.legend()
        
        # 绘制水汽分布
        for i, data in enumerate(configs_data):
            heights = [layer['height'] for layer in data]
            h2o = [layer['h2o_vmr'] for layer in data]
            ax2.semilogx(h2o, heights, label=f'Config {i:06d}')
        h2o = [layer['h2o_vmr'] for layer in self.layers[:N]]
        ax2.semilogx(h2o, heights, 'k--', label='Original')
        ax2.set_xlabel('H2O VMR')
        ax2.set_ylabel('Height (m)')
        ax2.legend()
        
        # 绘制臭氧分布
        for i, data in enumerate(configs_data):
            heights = [layer['height'] for layer in data]
            o3 = [layer['o3_vmr'] for layer in data]
            ax3.semilogx(o3, heights, label=f'Config {i:06d}')
        o3 = [layer['o3_vmr'] for layer in self.layers[:N]]
        ax3.semilogx(o3, heights, 'k--', label='Original')
        ax3.set_xlabel('O3 VMR')
        ax3.set_ylabel('Height (m)')
        ax3.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'profiles.png'))
        plt.close()

def main():
    # 解析命令行参数
    num_configs = 5
    config_template = "amc_inputs/northern_midlatitude_annual.amc"  # 默认模板路径
    min_height = None
    save_original = False  # 默认不保存原始配置文件
    
    if len(sys.argv) > 1:
        try:
            num_configs = int(sys.argv[1])
        except Exception:
            num_configs = 5
    
    if len(sys.argv) > 2:
        config_template = sys.argv[2]
        # 如果用户没有指定完整路径，则假设文件在 amc_inputs 目录中
        if not os.path.exists(config_template) and not os.path.isabs(config_template):
            config_template = os.path.join("amc_inputs", config_template)
    
    if len(sys.argv) > 3:
        try:
            min_height = float(sys.argv[3])
        except Exception:
            min_height = None
    
    if len(sys.argv) > 4:
        save_original = sys.argv[4].lower() in ['true', '1', 'yes']
    
    # 检查配置文件是否存在
    if not os.path.exists(config_template):
        print(f"错误：配置文件 {config_template} 不存在！")
        print("请检查文件路径或使用以下可用的配置文件：")
        amc_dir = "amc_inputs"
        if os.path.exists(amc_dir):
            for file in os.listdir(amc_dir):
                if file.endswith('.amc'):
                    print(f"  - {os.path.join(amc_dir, file)}")
        return
    
    # 创建生成器实例
    generator = AMConfigGenerator(config_template, min_height=min_height, save_original=save_original)
    
    # 生成指定数量的配置文件
    configs_data = []
    for i in range(num_configs):
        config_path, layers_data = generator.generate_config(i)
        configs_data.append(layers_data)
    
    # 绘制分布图
    generator.plot_profiles(configs_data)

if __name__ == "__main__":
    main() 