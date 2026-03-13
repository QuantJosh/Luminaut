#!/usr/bin/env python3
"""
Luminaut Viewer - 简化版本
使用简化的 UI 管理器，避免复杂 JavaScript 注入
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import requests
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lightweight_charts import Chart
from luminaut.viewer.simple_ui_manager import SimpleUIManager

class LuminautSimpleViewer:
    def __init__(self, mode='historical', symbol='btcusdt', timeframe='1min'):
        self.mode = mode
        self.symbol = symbol.upper()
        self.timeframe = timeframe
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
        
        print(f"🚀 初始化 Luminaut Simple Viewer")
        print(f"📊 模式: {mode}, 交易对: {symbol}, 周期: {timeframe}")
        
        # 初始化图表
        self.chart = Chart(
            title=f"Luminaut Viewer - {self.symbol} ({self.mode})",
            width=1200,
            height=700
        )
        
        # 简化的 UI 管理器
        self.ui_manager = SimpleUIManager(self.chart)
        
        # 数据状态
        self.current_price = 0
        self.price_history = []
        self.last_price_update = None
        
        # WebSocket 流（实时模式）
        self.stream = None
        
        print("✅ 初始化完成")
    
    def init_dashboard_ui(self):
        """初始化 UI"""
        try:
            self.ui_manager.create_simple_layout()
            print("✅ UI 初始化成功")
        except Exception as e:
            print(f"⚠️ UI 初始化失败: {e}")
    
    def fetch_recent_klines(self, limit=100):
        """获取最近 K 线数据"""
        print(f"📥 获取最近 {limit} 条 K 线数据...")
        
        try:
            url = "https://api.binance.com/api/v3/klines"
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
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                # 只保留需要的列
                df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
                
                print(f"✅ 成功获取 {len(df)} 条 K 线数据")
                return df
                
            else:
                print(f"❌ API 请求失败: {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 获取 K 线数据失败: {e}")
            return pd.DataFrame()
    
    def on_realtime_update(self, bar):
        """实时 K 线回调"""
        try:
            if bar:
                # 更新价格历史
                self.current_price = bar.get('close', 0)
                self.price_history.append(self.current_price)
                
                # 计算价格变化
                price_change = 0
                if len(self.price_history) > 1:
                    prev_price = self.price_history[-2]
                    if prev_price > 0:
                        price_change = ((self.current_price - prev_price) / prev_price) * 100
                
                # 更新 UI
                self.ui_manager.update_price(self.current_price, price_change)
                
                # 更新图表
                if not hasattr(self, '_first_data_set'):
                    df = pd.DataFrame([bar])
                    self.chart.set(df)
                    self._first_data_set = True
                else:
                    bar['time'] = pd.to_datetime(bar['time'], unit='s')
                    series = pd.Series(bar)
                    self.chart.update(series)
                    
        except Exception as e:
            print(f"⚠️ 实时更新失败: {e}")
    
    def on_depth_update(self, data):
        """订单簿更新回调"""
        try:
            bids = data.get('bids', [])[:5]
            asks = data.get('asks', [])[:5]
            
            if bids or asks:
                self.ui_manager.update_orderbook(bids, asks)
                
        except Exception as e:
            print(f"⚠️ 订单簿更新失败: {e}")
    
    def on_trade_update(self, trade):
        """成交更新回调"""
        try:
            price = trade.get('price', 0)
            qty = trade.get('qty', 0)
            side = trade.get('side', 'UNKNOWN')
            timestamp = trade.get('time', int(time.time()))
            
            if price > 0 and qty > 0:
                self.ui_manager.add_trade(timestamp, price, qty, side)
                
        except Exception as e:
            print(f"⚠️ 成交更新失败: {e}")
    
    def run_historical(self, filepath=None):
        """历史模式"""
        print("📜 运行历史模式...")
        
        # 获取历史数据
        df = self.fetch_recent_klines(200)
        
        if df.empty:
            print("❌ 无法获取历史数据")
            return
        
        try:
            # 初始化 UI
            self.init_dashboard_ui()
            
            # 设置图表数据
            self.chart.set(df)
            print(f"✅ 历史数据加载完成: {len(df)} 条 K 线")
            
            # 显示图表
            print("📊 显示历史图表...")
            self.chart.show(block=True)
            
        except Exception as e:
            print(f"❌ 历史模式运行失败: {e}")
    
    def run_realtime(self):
        """实时模式"""
        print("🔴 运行实时模式...")
        
        try:
            # 1. 先获取历史数据初始化图表
            df = self.fetch_recent_klines(50)
            
            if df.empty:
                print("❌ 无法获取初始数据")
                return
            
            # 2. 初始化图表
            self.chart.set(df)
            print("✅ 初始图表设置完成")
            
            # 3. 初始化 UI
            self.init_dashboard_ui()
            
            # 4. 模拟实时数据更新（简化版，不使用 WebSocket）
            print("🔄 模拟实时数据更新...")
            print("💡 提示: 这是简化版本，仅显示静态数据")
            print("💡 完整版本将支持 WebSocket 实时连接")
            
            # 显示图表
            self.chart.show(block=True)
            
        except Exception as e:
            print(f"❌ 实时模式运行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self, filepath=None):
        """主运行方法"""
        print(f"🎯 启动 Luminaut Simple Viewer...")
        
        if self.mode == 'realtime':
            self.run_realtime()
        else:
            if not filepath:
                print("❌ 历史模式需要数据文件")
                return
            self.run_historical(filepath)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Luminaut Simple Viewer')
    parser.add_argument('--mode', choices=['historical', 'realtime'], default='realtime')
    parser.add_argument('--symbol', default='btcusdt')
    parser.add_argument('--file', help='历史数据文件路径')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧪 Luminaut Simple Viewer")
    print("=" * 60)
    
    try:
        viewer = LuminautSimpleViewer(
            mode=args.mode,
            symbol=args.symbol
        )
        viewer.run(filepath=args.file)
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
