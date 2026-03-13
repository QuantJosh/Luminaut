import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

class TechnicalIndicators:
    """技术指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_vwap(self, df: pd.DataFrame, price_col: str = 'close', 
                      volume_col: str = 'volume', window: Optional[int] = None) -> pd.Series:
        """计算 VWAP (成交量加权平均价格)"""
        try:
            if window is None:
                # 计算累积 VWAP
                cumulative_pv = (df[price_col] * df[volume_col]).cumsum()
                cumulative_volume = df[volume_col].cumsum()
                vwap = cumulative_pv / cumulative_volume
            else:
                # 计算滚动 VWAP
                rolling_pv = (df[price_col] * df[volume_col]).rolling(window=window).sum()
                rolling_volume = df[volume_col].rolling(window=window).sum()
                vwap = rolling_pv / rolling_volume
            
            return vwap.fillna(method='ffill')
            
        except Exception as e:
            self.logger.error(f"VWAP calculation error: {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def calculate_sma(self, df: pd.DataFrame, price_col: str = 'close', 
                     window: int = 20) -> pd.Series:
        """计算简单移动平均线 (SMA)"""
        try:
            return df[price_col].rolling(window=window).mean()
        except Exception as e:
            self.logger.error(f"SMA calculation error: {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def calculate_ema(self, df: pd.DataFrame, price_col: str = 'close', 
                     window: int = 20) -> pd.Series:
        """计算指数移动平均线 (EMA)"""
        try:
            return df[price_col].ewm(span=window).mean()
        except Exception as e:
            self.logger.error(f"EMA calculation error: {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, price_col: str = 'close', 
                                window: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """计算布林带"""
        try:
            sma = self.calculate_sma(df, price_col, window)
            std = df[price_col].rolling(window=window).std()
            
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            return {
                'middle': sma,
                'upper': upper_band,
                'lower': lower_band
            }
        except Exception as e:
            self.logger.error(f"Bollinger Bands calculation error: {e}")
            return {
                'middle': pd.Series(index=df.index, dtype=float),
                'upper': pd.Series(index=df.index, dtype=float),
                'lower': pd.Series(index=df.index, dtype=float)
            }
    
    def calculate_rsi(self, df: pd.DataFrame, price_col: str = 'close', 
                     window: int = 14) -> pd.Series:
        """计算相对强弱指数 (RSI)"""
        try:
            delta = df[price_col].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        except Exception as e:
            self.logger.error(f"RSI calculation error: {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def calculate_macd(self, df: pd.DataFrame, price_col: str = 'close',
                      fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """计算 MACD"""
        try:
            ema_fast = self.calculate_ema(df, price_col, fast)
            ema_slow = self.calculate_ema(df, price_col, slow)
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
        except Exception as e:
            self.logger.error(f"MACD calculation error: {e}")
            return {
                'macd': pd.Series(index=df.index, dtype=float),
                'signal': pd.Series(index=df.index, dtype=float),
                'histogram': pd.Series(index=df.index, dtype=float)
            }
    
    def calculate_stochastic(self, df: pd.DataFrame, high_col: str = 'high',
                           low_col: str = 'low', close_col: str = 'close',
                           k_window: int = 14, d_window: int = 3) -> Dict[str, pd.Series]:
        """计算随机指标 (Stochastic)"""
        try:
            lowest_low = df[low_col].rolling(window=k_window).min()
            highest_high = df[high_col].rolling(window=k_window).max()
            
            k_percent = 100 * ((df[close_col] - lowest_low) / (highest_high - lowest_low))
            d_percent = k_percent.rolling(window=d_window).mean()
            
            return {
                'k': k_percent,
                'd': d_percent
            }
        except Exception as e:
            self.logger.error(f"Stochastic calculation error: {e}")
            return {
                'k': pd.Series(index=df.index, dtype=float),
                'd': pd.Series(index=df.index, dtype=float)
            }
    
    def calculate_atr(self, df: pd.DataFrame, high_col: str = 'high',
                     low_col: str = 'low', close_col: str = 'close',
                     window: int = 14) -> pd.Series:
        """计算平均真实范围 (ATR)"""
        try:
            high_low = df[high_col] - df[low_col]
            high_close = np.abs(df[high_col] - df[close_col].shift())
            low_close = np.abs(df[low_col] - df[close_col].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=window).mean()
            
            return atr
        except Exception as e:
            self.logger.error(f"ATR calculation error: {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def calculate_obv(self, df: pd.DataFrame, price_col: str = 'close',
                     volume_col: str = 'volume') -> pd.Series:
        """计算能量潮 (On-Balance Volume)"""
        try:
            price_change = df[price_col].diff()
            obv = pd.Series(index=df.index, dtype=float)
            
            # 第一天的 OBV 等于成交量
            obv.iloc[0] = df[volume_col].iloc[0]
            
            # 后续 OBV 计算
            for i in range(1, len(df)):
                if price_change.iloc[i] > 0:
                    obv.iloc[i] = obv.iloc[i-1] + df[volume_col].iloc[i]
                elif price_change.iloc[i] < 0:
                    obv.iloc[i] = obv.iloc[i-1] - df[volume_col].iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i-1]
            
            return obv
        except Exception as e:
            self.logger.error(f"OBV calculation error: {e}")
            return pd.Series(index=df.index, dtype=float)
    
    def calculate_fibonacci_retracement(self, df: pd.DataFrame, 
                                     price_col: str = 'close',
                                     window: int = 100) -> Dict[str, float]:
        """计算斐波那契回撤水平"""
        try:
            recent_data = df[price_col].tail(window)
            high_price = recent_data.max()
            low_price = recent_data.min()
            
            diff = high_price - low_price
            
            levels = {
                '0%': high_price,
                '23.6%': high_price - 0.236 * diff,
                '38.2%': high_price - 0.382 * diff,
                '50%': high_price - 0.5 * diff,
                '61.8%': high_price - 0.618 * diff,
                '78.6%': high_price - 0.786 * diff,
                '100%': low_price
            }
            
            return levels
        except Exception as e:
            self.logger.error(f"Fibonacci calculation error: {e}")
            return {}
    
    def calculate_pivot_points(self, df: pd.DataFrame, high_col: str = 'high',
                            low_col: str = 'low', close_col: str = 'close') -> Dict[str, float]:
        """计算枢轴点"""
        try:
            # 使用最近一天的数据
            last_day = df.tail(1)
            high = last_day[high_col].iloc[0]
            low = last_day[low_col].iloc[0]
            close = last_day[close_col].iloc[0]
            
            pivot = (high + low + close) / 3
            
            levels = {
                'pivot': pivot,
                'r1': 2 * pivot - low,      # Resistance 1
                'r2': pivot + (high - low), # Resistance 2
                'r3': high + 2 * (high - low - pivot), # Resistance 3
                's1': 2 * pivot - high,     # Support 1
                's2': pivot - (high - low), # Support 2
                's3': low - 2 * (high - low - pivot)  # Support 3
            }
            
            return levels
        except Exception as e:
            self.logger.error(f"Pivot points calculation error: {e}")
            return {}
    
    def get_indicator_summary(self, df: pd.DataFrame) -> Dict:
        """获取技术指标摘要"""
        try:
            summary = {}
            
            # 趋势指标
            summary['sma_20'] = self.calculate_sma(df, window=20).iloc[-1] if len(df) >= 20 else None
            summary['sma_50'] = self.calculate_sma(df, window=50).iloc[-1] if len(df) >= 50 else None
            summary['ema_20'] = self.calculate_ema(df, window=20).iloc[-1] if len(df) >= 20 else None
            
            # 动量指标
            summary['rsi'] = self.calculate_rsi(df).iloc[-1] if len(df) >= 14 else None
            
            # 波动性指标
            bb = self.calculate_bollinger_bands(df)
            if len(df) >= 20:
                summary['bb_upper'] = bb['upper'].iloc[-1]
                summary['bb_middle'] = bb['middle'].iloc[-1]
                summary['bb_lower'] = bb['lower'].iloc[-1]
            
            # 成交量指标
            summary['vwap'] = self.calculate_vwap(df).iloc[-1] if len(df) >= 1 else None
            
            # 当前价格
            current_price = df['close'].iloc[-1] if len(df) > 0 else None
            
            # 生成简单信号
            signals = []
            if current_price and summary.get('sma_20'):
                if current_price > summary['sma_20']:
                    signals.append("价格在20日均线上方")
                else:
                    signals.append("价格在20日均线下方")
            
            if summary.get('rsi'):
                if summary['rsi'] > 70:
                    signals.append("RSI超买")
                elif summary['rsi'] < 30:
                    signals.append("RSI超卖")
                else:
                    signals.append("RSI中性")
            
            summary['signals'] = signals
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Indicator summary error: {e}")
            return {}
