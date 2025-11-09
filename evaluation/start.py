#!/usr/bin/env python3
"""
axSpA 智能诊断系统 - 简化启动脚本
"""

import os
import sys
import subprocess
import time

def main():
    """主函数"""
    print("=" * 50)
    print("🧠 axSpA 智能诊断系统 - 在线版本")
    print("=" * 50)
    
    # 检查当前目录
    current_dir = os.getcwd()
    print(f"📁 当前目录: {current_dir}")
    
    # 检查必要文件
    required_files = [
        "evaluation_online.py",
        "static/index.html"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} (缺失)")
            return
    
    # 创建uploads目录
    os.makedirs("uploads", exist_ok=True)
    print("✅ uploads 目录已创建")
    
    # 创建测试文件
    try:
        import numpy as np
        test_file = "test_mri.npy"
        if not os.path.exists(test_file):
            print("🔧 创建测试文件...")
            test_data = np.random.rand(24, 512, 512).astype(np.float32)
            np.save(test_file, test_data)
            print(f"✅ 测试文件已创建: {test_file}")
        else:
            print(f"✅ 测试文件已存在: {test_file}")
    except Exception as e:
        print(f"❌ 创建测试文件失败: {e}")
        return
    
    # 启动服务
    print("\n🚀 启动Web服务...")
    print("📱 访问地址: http://localhost:5500")
    print("🛑 按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        # 直接运行Flask应用
        subprocess.run([sys.executable, "evaluation_online.py"])
    except KeyboardInterrupt:
        print("\n✅ 服务已停止")

if __name__ == "__main__":
    main() 