#!/usr/bin/env python3
"""
axSpA 智能诊断系统 - 在线版本启动脚本
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

def create_test_file():
    """创建测试用的npy文件"""
    print("🔧 创建测试文件...")
    
    try:
        # 检查是否已存在测试文件
        test_file = "test_mri.npy"
        if os.path.exists(test_file):
            print(f"✅ 测试文件已存在: {test_file}")
            return test_file
        
        # 创建测试文件
        import numpy as np
        test_data = np.random.rand(24, 512, 512).astype(np.float32)
        np.save(test_file, test_data)
        
        print(f"✅ 测试文件已创建: {test_file}")
        print(f"📊 文件大小: {os.path.getsize(test_file) / 1024 / 1024:.2f} MB")
        return test_file
        
    except Exception as e:
        print(f"❌ 创建测试文件失败: {e}")
        return None

def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查依赖...")
    
    required_packages = [
        'flask',
        'flask-cors',
        'numpy',
        'pandas'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} (缺失)")
    
    if missing_packages:
        print(f"\n⚠️  缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ 所有依赖检查通过")
    return True

def start_web_service():
    """启动Web服务"""
    print("\n🚀 启动Web服务...")
    
    try:
        # 切换到evaluation目录
        os.chdir(Path(__file__).parent)
        
        # 启动Flask应用
        cmd = [sys.executable, "evaluation_online.py"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待服务启动
        time.sleep(3)
        
        # 检查服务是否正常启动
        if process.poll() is None:
            print("✅ Web服务启动成功!")
            print("📱 访问地址: http://localhost:5500")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Web服务启动失败:")
            print(f"错误信息: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ 启动Web服务失败: {e}")
        return None

def open_browser():
    """打开浏览器"""
    print("\n🌐 正在打开浏览器...")
    try:
        webbrowser.open('http://localhost:5500')
        print("✅ 浏览器已打开")
    except Exception as e:
        print(f"❌ 无法自动打开浏览器: {e}")
        print("请手动访问: http://localhost:5500")

def main():
    """主函数"""
    print("=" * 50)
    print("🧠 axSpA 智能诊断系统 - 在线版本")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 创建测试文件
    test_file = create_test_file()
    if test_file:
        print(f"📁 测试文件路径: {os.path.abspath(test_file)}")
    
    # 启动Web服务
    process = start_web_service()
    if not process:
        return
    
    # 打开浏览器
    open_browser()
    
    print("\n" + "=" * 50)
    print("📋 使用说明:")
    print("1. 在Web界面中拖拽或选择 .npy 文件")
    print("2. 点击'开始诊断分析'按钮")
    print("3. 等待诊断结果")
    print("4. 按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        # 保持服务运行
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        process.terminate()
        process.wait()
        print("✅ 服务已停止")

if __name__ == "__main__":
    main() 