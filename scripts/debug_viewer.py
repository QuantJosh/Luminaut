#!/usr/bin/env python3
"""
最简化版 Luminaut Viewer
仅包含核心功能，用于调试
"""

import sys
import logging
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """测试依赖导入"""
    print("🔍 测试依赖导入...")
    
    try:
        from lightweight_charts import Chart
        print("✅ lightweight_charts 导入成功")
    except Exception as e:
        print(f"❌ lightweight_charts 导入失败: {e}")
        return False
    
    try:
        import pandas as pd
        print("✅ pandas 导入成功")
    except Exception as e:
        print(f"❌ pandas 导入失败: {e}")
        return False
    
    try:
        import requests
        print("✅ requests 导入成功")
    except Exception as e:
        print(f"❌ requests 导入失败: {e}")
        return False
    
    return True

def test_simple_chart():
    """测试最简单的图表"""
    print("📊 测试最简单图表...")
    
    try:
        from lightweight_charts import Chart
        import pandas as pd
        
        # 创建最小图表
        chart = Chart(title="Test", width=400, height=300)
        
        # 创建最小数据
        data = pd.DataFrame({
            'time': pd.date_range('2024-01-01', periods=5, freq='1min'),
            'close': [100, 101, 102, 101, 103]
        })
        
        # 设置数据
        chart.set(data)
        print("✅ 图表数据设置成功")
        
        # 不显示，直接退出
        print("✅ 最简单图表测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 简单图表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_connection():
    """测试 API 连接"""
    print("🌐 测试 API 连接...")
    
    try:
        import requests
        
        # 简单的 HTTP 请求
        response = requests.get("https://httpbin.org/get", timeout=5)
        
        if response.status_code == 200:
            print("✅ 基本网络连接正常")
            return True
        else:
            print(f"❌ 网络连接异常: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 网络连接测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🧪 Luminaut Viewer 最简化调试")
    print("=" * 40)
    
    # 设置最简单的日志
    logging.basicConfig(level=logging.DEBUG, 
                    format='%(levelname)s - %(message)s')
    
    tests = [
        ("依赖导入", test_imports),
        ("API 连接", test_api_connection), 
        ("简单图表", test_simple_chart),
    ]
    
    for test_name, test_func in tests:
        print(f"\n📋 执行: {test_name}")
        try:
            success = test_func()
            if not success:
                print(f"❌ {test_name} 失败，停止测试")
                return
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
            return
    
    print("\n🎉 所有基础测试通过！")
    print("\n📝 问题分析:")
    print("如果基础测试通过但完整版卡死，问题可能在:")
    print("1. UI 初始化脚本过于复杂")
    print("2. WebSocket 连接超时")
    print("3. 配置文件问题")
    print("4. 依赖版本兼容性")

if __name__ == "__main__":
    main()
