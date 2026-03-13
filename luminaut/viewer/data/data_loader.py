import pandas as pd
import numpy as np
from typing import Dict

class DataLoader:
    def load_trades(self, filepath: str) -> pd.DataFrame:
        try:
            first_line = pd.read_csv(filepath, nrows=1)
            has_header = 'timestamp' in first_line.columns or 'price' in first_line.columns
        except:
            has_header = False
        
        if has_header:
            df = pd.read_csv(filepath)
        else:
            df = pd.read_csv(filepath, header=None)
            df.columns = ['trade_id', 'price', 'quantity', 'quote_quantity', 'timestamp', 'is_buyer_maker', 'is_best_match']
        
        if 'timestamp' in df.columns:
            sample_ts = pd.to_numeric(df['timestamp'].iloc[0], errors='coerce')
            if pd.isna(sample_ts):
                df['datetime'] = pd.to_datetime(df['timestamp'], errors='coerce')
            elif sample_ts > 1e15: # 微秒
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='us', errors='coerce')
            elif sample_ts > 1e12: # 毫秒
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
            else: # 秒
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
        
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        return df.sort_values('datetime').reset_index(drop=True)

    def resample_klines(self, trades_df: pd.DataFrame, timeframe: str = '1min') -> pd.DataFrame:
        df = trades_df.set_index('datetime')
        ohlc = df['price'].resample(timeframe).ohlc()
        volume = df['quantity'].resample(timeframe).sum()
        klines = pd.DataFrame({
            'time': ohlc.index,
            'open': ohlc['open'], 'high': ohlc['high'], 'low': ohlc['low'], 'close': ohlc['close'],
            'volume': volume
        }).dropna()
        # lightweight-charts 需要秒级时间戳
        klines['time'] = klines['time'].astype(np.int64) // 10**9
        return klines.reset_index(drop=True)
