#!/usr/bin/env python3
"""
简化版 Luminaut Viewer - 仅核心功能
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import requests

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from lightweight_charts import Chart

class SimpleViewer:
    def __init__(self, symbol='btcusdt'):
        self.symbol = symbol.upper()
        self.logger = logging.getLogger(__name__)
        
        # 设置简单日志
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
        
        print(f"🚀 初始化 Simple Viewer - {self.symbol}")
        
        # 创建简单图表
        self.chart = Chart(
            title=f"Luminaut Simple Viewer - {self.symbol}",
            width=800,
            height=600
        )
        
        # 添加 K 线图
        self.chart.set(pd.DataFrame([]))
        
    def fetch_recent_data(self, limit=50):
        """获取最近数据"""
        print(f"📥 获取最近 {limit} 条数据...")
        
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': self.symbol,
                'interval': '1m',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 转换为 DataFrame
                df = pd.DataFrame(data, columns=[
                    'time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # 转换数据类型
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float) 
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                # 只保留需要的列
                df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
                
                print(f"✅ 成功获取 {len(df)} 条数据")
                return df
                
            else:
                print(f"❌ API 请求失败: {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            return pd.DataFrame()
    
    def run(self):
        """运行查看器"""
        print("🎯 启动查看器...")
        
        # 获取数据
        df = self.fetch_recent_data()
        
        if df.empty:
            print("❌ 无法获取数据，退出")
            return
        
        try:
            # 设置图表数据
            self.chart.set(df)
            print("✅ 图表数据设置成功")
            
            # 显示图表
            print("📊 显示图表...")
            print("💡 提示: 关闭图表窗口以退出程序")
            
            self.chart.show(block=True)
            print("👋 程序正常退出")
            
        except Exception as e:
            print(f"❌ 图表显示失败: {e}")
            import traceback
            traceback.print_exc()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Luminaut Simple Viewer')
    parser.add_argument('--symbol', default='btcusdt', help='交易对')
    parser.add_argument('--limit', type=int, default=50, help='数据条数')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("🧪 Luminaut Simple Viewer")
    print("=" * 50)
    
    try:
        viewer = SimpleViewer(symbol=args.symbol)
        viewer.run()
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
