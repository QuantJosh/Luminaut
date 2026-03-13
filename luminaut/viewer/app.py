from lightweight_charts import Chart
import pandas as pd
from pathlib import Path
import sys
import threading
import time
from datetime import datetime
import numpy as np
import logging

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from luminaut.viewer.data import DataLoader, LiveStream
from luminaut.viewer.ui_manager import UIManager
from luminaut.viewer.data_validator import DataValidator
from luminaut.viewer.technical_indicators import TechnicalIndicators
from luminaut.viewer.config_manager import ConfigManager

class LuminautViewer:
    def __init__(self, mode='historical', symbol='btcusdt', timeframe='1min', config_file=None):
        # 加载配置
        self.config_manager = ConfigManager(config_file or "luminaut_config.json")
        
        # 从配置获取设置
        self.mode = self.config_manager.get('app.mode', mode)
        self.symbol = self.config_manager.get('app.symbol', symbol)
        self.timeframe = self.config_manager.get('app.timeframe', timeframe)
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # 初始化图表 - 从配置获取尺寸
        self.chart = Chart(
            title=f"Luminaut Viewer - {self.symbol.upper()} ({self.mode})", 
            width=self.config_manager.get('chart.width', 1400), 
            height=self.config_manager.get('chart.height', 800)
        )
        self.chart.legend(visible=self.config_manager.get('chart.show_legend', True))
        self.chart.grid(vert_enabled=self.config_manager.get('chart.show_grid', True), horz_enabled=True)
        
        # 数据组件
        self.loader = DataLoader()
        self.stream = None
        
        # UI 管理器
        self.ui_manager = UIManager(self.chart)
        
        # 配置 UI 更新间隔
        self.ui_manager.update_interval = self.config_manager.get('ui.update_interval', 100)
        
        # 数据验证器
        self.data_validator = DataValidator()
        
        # 配置验证参数
        self.data_validator.price_change_threshold = self.config_manager.get('validation.price_change_threshold', 0.20)
        self.data_validator.volume_spike_threshold = self.config_manager.get('validation.volume_spike_threshold', 10.0)
        
        # 技术指标计算器
        self.tech_indicators = TechnicalIndicators()
        
        # 数据状态
        self.current_price = 0
        self.price_history = []
        self.last_price_update = None
        self.volume_history = []
        self.last_timestamp = None
        
        # K线数据存储（用于技术指标计算）
        self.kline_data = pd.DataFrame()
    
    def init_dashboard_ui(self):
        """初始化 TradingView 风格的 UI"""
        # 防止重复初始化
        if getattr(self, '_ui_initialized', False): 
            return
        
        try:
            self.ui_manager.create_tradingview_layout()
            self._ui_initialized = True
            self.logger.info("TradingView UI initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize UI: {e}")


    def on_realtime_update(self, bar):
        """实时K线回调"""
        # 初始化 UI
        if self.stream and not getattr(self, '_ui_initialized', False):
            self.init_dashboard_ui()

        if bar:
            # 数据验证
            is_valid, error_msg = self.data_validator.validate_kline_data(bar)
            if not is_valid:
                self.logger.warning(f"Invalid K-line data: {error_msg}")
                return
            
            # 更新价格历史
            self.current_price = bar.get('close', 0)
            self.price_history.append(self.current_price)
            
            # 更新成交量历史
            volume = bar.get('volume', 0)
            self.volume_history.append(volume)
            
            # 检测价格异常
            is_price_anomaly, price_deviation = self.data_validator.detect_price_anomaly(
                self.current_price, self.price_history[:-1]
            )
            if is_price_anomaly:
                self.logger.warning(f"Price anomaly detected: {price_deviation:.2%} deviation")
            
            # 检测成交量异常
            is_volume_spike, volume_ratio = self.data_validator.detect_volume_spike(
                volume, self.volume_history[:-1]
            )
            if is_volume_spike:
                self.logger.warning(f"Volume spike detected: {volume_ratio:.1f}x normal")
            
            # 计算价格变化百分比
            price_change = 0
            if len(self.price_history) > 1:
                prev_price = self.price_history[-2]
                if prev_price > 0:
                    price_change = ((self.current_price - prev_price) / prev_price) * 100
            
            # 更新 UI 价格显示
            self.ui_manager.update_price(self.current_price, price_change)
            
            # 更新图表
            if not hasattr(self, '_first_data_set'):
                df = pd.DataFrame([bar])
                df['time'] = pd.to_datetime(df['time'], unit='s')
                self.chart.set(df)
                self._first_data_set = True
                self.logger.info(f"Initial chart set with {len(df)} bars")
            else:
                bar['time'] = self._ts_to_dt(bar['time'])
                series = pd.Series(bar)
                self.chart.update(series)
            
            # 更新K线数据存储
            new_row = pd.DataFrame([{
                'time': pd.to_datetime(bar['time'], unit='s'),
                'open': bar['open'],
                'high': bar['high'],
                'low': bar['low'],
                'close': bar['close'],
                'volume': bar['volume']
            }])
            self.kline_data = pd.concat([self.kline_data, new_row], ignore_index=True)
            
            # 计算并更新技术指标（如果启用）
            if self.config_manager.get('indicators.vwap.enabled', True):
                self._update_technical_indicators()
                
    def _ts_to_dt(self, ts):
        return pd.to_datetime(ts, unit='s')

    def on_depth_update(self, data):
        """实时订单簿回调 - 更新侧边栏"""
        if not getattr(self, '_ui_initialized', False): 
            return

        try:
            # 验证订单簿数据
            is_valid, error_msg = self.data_validator.validate_orderbook_data(data)
            if not is_valid:
                self.logger.warning(f"Invalid orderbook data: {error_msg}")
                return
            
            bids = data.get('bids', [])[:10]  # Top 10
            asks = data.get('asks', [])[:10]  # Top 10
            
            # 转换数据格式并验证
            formatted_bids = []
            formatted_asks = []
            
            for bid in bids:
                if len(bid) >= 2:
                    price, qty = float(bid[0]), float(bid[1])
                    if price > 0 and qty >= 0:
                        formatted_bids.append((price, qty))
            
            for ask in asks:
                if len(ask) >= 2:
                    price, qty = float(ask[0]), float(ask[1])
                    if price > 0 and qty >= 0:
                        formatted_asks.append((price, qty))
            
            # 更新 UI
            if formatted_bids or formatted_asks:
                self.ui_manager.update_orderbook(formatted_bids, formatted_asks)
                
        except Exception as e:
            self.logger.error(f"Error processing depth update: {e}")
            
    def on_trade_update(self, trade):
        """实时成交回调 - 更新侧边栏"""
        if not getattr(self, '_ui_initialized', False): 
            return
        
        try:
            price = trade.get('price', 0)
            qty = trade.get('qty', 0)
            side = trade.get('side', 'UNKNOWN')
            timestamp = trade.get('time', 0)
            
            # 验证交易数据
            trade_data = {
                'price': price,
                'quantity': qty,
                'timestamp': timestamp
            }
            is_valid, error_msg = self.data_validator.validate_trade_data(trade_data)
            if not is_valid:
                self.logger.warning(f"Invalid trade data: {error_msg}")
                return
            
            # 检测时间戳间隙
            if self.last_timestamp:
                has_gap, gap_seconds = self.data_validator.detect_timestamp_gap(
                    timestamp, self.last_timestamp
                )
                if has_gap:
                    self.logger.warning(f"Timestamp gap detected: {gap_seconds} seconds")
            
            self.last_timestamp = timestamp
            
            # 更新 UI
            self.ui_manager.add_trade(timestamp, price, qty, side)
            
        except Exception as e:
            self.logger.error(f"Error processing trade update: {e}")
    
    def _update_technical_indicators(self):
        """计算并更新技术指标"""
        try:
            if len(self.kline_data) < 20:  # 需要足够的数据点
                return
            
            # 计算 VWAP
            vwap = self.tech_indicators.calculate_vwap(self.kline_data)
            if not vwap.empty:
                current_vwap = vwap.iloc[-1]
                # 可以在这里更新UI显示VWAP
                # self.ui_manager.update_indicator('VWAP', current_vwap)
            
            # 计算 SMA
            sma_20 = self.tech_indicators.calculate_sma(self.kline_data, window=20)
            if not sma_20.empty:
                current_sma = sma_20.iloc[-1]
                # self.ui_manager.update_indicator('SMA20', current_sma)
            
            # 计算 RSI
            rsi = self.tech_indicators.calculate_rsi(self.kline_data)
            if not rsi.empty:
                current_rsi = rsi.iloc[-1]
                # self.ui_manager.update_indicator('RSI', current_rsi)
            
            # 获取指标摘要
            summary = self.tech_indicators.get_indicator_summary(self.kline_data)
            if summary.get('signals'):
                for signal in summary['signals']:
                    self.logger.info(f"技术信号: {signal}")
                    
        except Exception as e:
            self.logger.error(f"Technical indicators update error: {e}")

    def fetch_recent_klines(self, limit=1000):
        """从Binance REST API获取最近K线"""
        self.logger.info(f"📥 Fetching recent {limit} candles...")
        import requests
        
        # Binance API: 1m, 5m, 15m, 1h
        interval_map = {'1min': '1m', '5min': '5m', '15min': '15m', '1H': '1h'}
        interval = interval_map.get(self.timeframe, '1m')
        
        url = f"https://api.binance.com/api/v3/klines?symbol={self.symbol.upper()}&interval={interval}&limit={limit}"
        try:
            resp = requests.get(url)
            data = resp.json()
            # data format: [ [open_time, open, high, low, close, volume, ...], ... ]
            
            klines = []
            for k in data:
                klines.append({
                    'time': int(k[0]) // 1000, # 秒级时间戳
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
            
            df = pd.DataFrame(klines)
            if df.empty:
                self.logger.warning("⚠️ Warning: Fetched DataFrame is empty.")
                return df
                
            # 确保按时间排序
            df = df.sort_values('time').drop_duplicates('time')
            
            # 尝试修复: 将时间戳转换为 datetime 字符串
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            self.logger.info(f"📊 Initialized with {len(df)} candles")
            
            # 初始化K线数据存储
            self.kline_data = df.copy()
            
            return df
        except Exception as e:
            self.logger.error(f"⚠️ Failed to fetch recent klines: {e}")
            return pd.DataFrame()

    def run_realtime(self):
        self.logger.info(f"🚀 Starting Real-time Mode for {self.symbol}...")
        
        # 1. 先获取历史K线
        try:
            recent_klines = self.fetch_recent_klines()
            if not recent_klines.empty:
                # Configure chart to datetime compatible
                self.chart.set(recent_klines)
                self._first_data_set = True
        except Exception as e:
                self.logger.error(f"⚠️ Error setting initial data: {e}")
            
        # 2. 初始化 LiveStream
        self.stream = LiveStream(
            symbol=self.symbol, 
            callback=self.on_realtime_update,
            depth_callback=self.on_depth_update,
            trades_callback=self.on_trade_update
        )
        self.stream.start()
        
        # Show block
        self.chart.show(block=True)
        self.stream.stop()

    def run(self, filepath=None):
        if self.mode == 'realtime':
            self.run_realtime()
        else:
            if not filepath:
                self.logger.error("❌ Historical mode requires --file")
                return
            self.run_historical(filepath)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=['historical', 'realtime'], default='historical')
    parser.add_argument("--file", help="Path to csv file for historical mode")
    parser.add_argument("--symbol", default="btcusdt")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--save-config", action='store_true', help="Save current configuration and exit")
    args = parser.parse_args()
    
    # 创建查看器实例
    viewer = LuminautViewer(
        mode=args.mode, 
        symbol=args.symbol,
        config_file=args.config
    )
    
    # 保存配置选项
    if args.save_config:
        if viewer.config_manager.save_config():
            print("✅ 配置已保存")
        else:
            print("❌ 配置保存失败")
        return
    
    # 显示配置摘要
    print(viewer.config_manager.get_summary())
    
    # 验证配置
    validation = viewer.config_manager.validate_config()
    if not validation['valid']:
        print("❌ 配置验证失败:")
        for issue in validation['issues']:
            print(f"  - {issue}")
        return
    
    if validation['warnings']:
        print("⚠️ 配置警告:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
    
    # 运行查看器
    viewer.run(filepath=args.file)

if __name__ == "__main__":
    main()
