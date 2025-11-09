import numpy as np
import os

def create_test_npy():
    """创建一个测试用的npy文件"""
    
    # 创建一个模拟的MRI影像数据 (24, 512, 512)
    # 这模拟了一个3D的MRI扫描数据
    test_data = np.random.rand(24, 512, 512).astype(np.float32)
    
    # 保存为npy文件
    output_path = "test_mri.npy"
    np.save(output_path, test_data)
    
    print(f"✅ 测试文件已创建: {output_path}")
    print(f"📊 文件大小: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
    print(f"📐 数据形状: {test_data.shape}")
    print(f"🔢 数据类型: {test_data.dtype}")
    
    return output_path

if __name__ == "__main__":
    create_test_npy() 