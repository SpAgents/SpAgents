#!/usr/bin/env python3
"""
测试导入脚本 - 验证所有模块是否正常导入
"""

def test_imports():
    """测试所有必要的导入"""
    print("🧪 测试导入...")
    
    try:
        # 测试标准库导入
        import sys
        import os
        import time
        import uuid
        import json
        import io
        import traceback
        import importlib
        print("✅ 标准库导入成功")
        
        # 测试第三方库导入
        import numpy as np
        import pandas as pd
        print("✅ 第三方库导入成功")
        
        # 测试Flask相关导入
        from flask import Flask, request, Response, stream_with_context, send_from_directory
        from flask_cors import CORS
        print("✅ Flask库导入成功")
        
        # 测试项目模块导入
        sys.path.append(os.path.abspath(".."))
        from agent.planner_agent import PlannerAgent
        print("✅ 项目模块导入成功")
        
        print("🎉 所有导入测试通过!")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    test_imports() 