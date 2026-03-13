#!/usr/bin/env python3
"""
简化版 Luminaut Viewer 测试脚本
用于快速验证基本功能
"""

import sys
import logging
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from lightweight_charts import Chart
    import pandas as pd
    import requests
    from datetime import datetime
    print("✅ 基本依赖导入成功")
except ImportError as e:
    print(f"❌ 依赖导入失败: {e}")
    print("请确保已安装: pip install lightweight-charts pandas requests")
    sys.exit(1)

def test_basic_chart():
    """测试基本图表功能"""
    print("🚀 测试基本图表功能...")
    
    try:
        # 创建简单图表
        chart = Chart(title="Luminaut Viewer - Test", width=800, height=600)
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=50, freq='1min')
        data = pd.DataFrame({
            'time': dates,
            'open': 100 + pd.Series(range(50)) * 0.1,
            'high': 101 + pd.Series(range(50)) * 0.1,
            'low': 99 + pd.Series(range(50)) * 0.1,
            'close': 100.5 + pd.Series(range(50)) * 0.1,
            'volume': [1000] * 50
        })
        
        # 设置数据
        chart.set(data)
        print("✅ 图表数据设置成功")
        
        # 显示图表（非阻塞）
        chart.show(block=False)
        print("✅ 图表显示成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 图表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_binance_connection():
    """测试 Binance 连接"""
    print("🌐 测试 Binance API 连接...")
    
    try:
        # 测试 REST API
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            price = float(data['price'])
            print(f"✅ Binance API 连接成功，BTC 价格: {price}")
            return True
        else:
            print(f"❌ Binance API 返回错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Binance 连接测试失败: {e}")
        return False

def test_websocket_connection():
    """测试 WebSocket 连接"""
    print("🔌 测试 WebSocket 连接...")
    
    try:
        import asyncio
        import websockets
        import json
        
        async def test_ws():
            try:
                url = "wss://stream.binance.com:9443/ws/btcusdt@trade"
                async with websockets.connect(url, timeout=10) as websocket:
                    print("✅ WebSocket 连接成功")
                    # 等待一条消息
                    message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    data = json.loads(message)
                    print(f"✅ 收到数据: {data.get('p', 'N/A')}")
                    return True
            except Exception as e:
                print(f"❌ WebSocket 测试失败: {e}")
                return False
        
        # 运行测试
        result = asyncio.run(test_ws())
        return result
        
    except ImportError:
        print("⚠️ WebSocket 库未安装，跳过 WebSocket 测试")
        return True
    except Exception as e:
        print(f"❌ WebSocket 测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("🧪 Luminaut Viewer 简化测试")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
    
    tests = [
        ("基本图表功能", test_basic_chart),
        ("Binance API 连接", test_binance_connection),
        ("WebSocket 连接", test_websocket_connection),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 执行测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！Luminaut Viewer 基本功能正常")
    else:
        print("⚠️ 部分测试失败，请检查相关配置")
    
    print("\n💡 提示:")
    print("- 如果图表测试失败，请检查 lightweight-charts 安装")
    print("- 如果网络测试失败，请检查网络连接")
    print("- 如果所有测试通过，可以尝试运行完整版本")

if __name__ == "__main__":
    main()
