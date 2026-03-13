#!/usr/bin/env python3
"""
Luminaut Viewer 启动脚本
自动选择合适的版本
"""

import sys
import argparse
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    parser = argparse.ArgumentParser(description='Luminaut Viewer')
    parser.add_argument('--mode', choices=['historical', 'realtime'], default='realtime')
    parser.add_argument('--symbol', default='btcusdt')
    parser.add_argument('--file', help='历史数据文件路径')
    parser.add_argument('--simple', action='store_true', help='使用简化版本')
    
    args = parser.parse_args()
    
    print("🚀 Luminaut Viewer 启动中...")
    print(f"📊 模式: {args.mode}, 交易对: {args.symbol.upper()}")
    
    if args.simple:
        print("🎨 使用简化版本")
        from luminaut.viewer.simple_app import main as simple_main
        
        # 设置参数
        sys.argv = ['simple_app.py', '--mode', args.mode, '--symbol', args.symbol]
        if args.file:
            sys.argv.extend(['--file', args.file])
        
        simple_main()
    else:
        print("⚠️ 完整版本可能存在兼容性问题")
        print("💡 建议使用 --simple 参数")
        print("🔄 尝试启动完整版本...")
        
        try:
            from luminaut.viewer.app import main as full_main
            
            # 设置参数
            sys.argv = ['app.py', '--mode', args.mode, '--symbol', args.symbol]
            if args.file:
                sys.argv.extend(['--file', args.file])
            
            full_main()
            
        except Exception as e:
            print(f"❌ 完整版本启动失败: {e}")
            print("💡 自动切换到简化版本...")
            
            from luminaut.viewer.simple_app import main as simple_main
            sys.argv = ['simple_app.py', '--mode', args.mode, '--symbol', args.symbol]
            if args.file:
                sys.argv.extend(['--file', args.file])
            
            simple_main()

if __name__ == "__main__":
    main()
