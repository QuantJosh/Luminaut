#!/usr/bin/env python3
"""
快速诊断脚本 - 检查基本环境
"""

import sys
import os

def check_python():
    """检查 Python 环境"""
    print(f"Python 版本: {sys.version}")
    print(f"Python 路径: {sys.executable}")
    print(f"当前目录: {os.getcwd()}")

def check_imports():
    """检查关键依赖"""
    packages = [
        'lightweight_charts',
        'pandas', 
        'requests',
        'websockets',
        'numpy'
    ]
    
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError as e:
            print(f"❌ {package}: {e}")

def check_files():
    """检查关键文件"""
    files = [
        'luminaut/viewer/app.py',
        'luminaut/viewer/ui_manager.py',
        'luminaut/viewer/config_manager.py',
        'scripts/launch_viewer.py'
    ]
    
    for file_path in files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")

def main():
    print("🔍 Luminaut Viewer 环境诊断")
    print("=" * 40)
    
    check_python()
    print()
    check_imports()
    print()
    check_files()
    
    print("\n📝 如果所有检查都通过，问题可能在:")
    print("1. lightweight-charts 版本兼容性")
    print("2. UI 初始化脚本")
    print("3. WebSocket 连接")

if __name__ == "__main__":
    main()
