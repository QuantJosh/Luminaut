import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

class DataValidator:
    """数据质量验证和异常检测"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 验证阈值
        self.price_change_threshold = 0.20  # 20% 价格变化阈值
        self.volume_spike_threshold = 10.0   # 10倍 成交量异常阈值
        self.gap_threshold = 0.05          # 5% 价格跳空阈值
        self.min_price = 0.001              # 最小有效价格
        self.max_price = 1000000            # 最大有效价格
        
        # 统计信息
        self.validation_stats = {
            'total_trades': 0,
            'invalid_trades': 0,
            'price_anomalies': 0,
            'volume_anomalies': 0,
            'timestamp_gaps': 0,
            'last_validation': None
        }
    
    def validate_trade_data(self, trade_data: Dict) -> Tuple[bool, str]:
        """验证单笔交易数据"""
        try:
            # 检查必要字段
            required_fields = ['price', 'quantity', 'timestamp']
            for field in required_fields:
                if field not in trade_data:
                    return False, f"Missing required field: {field}"
            
            price = float(trade_data['price'])
            quantity = float(trade_data['quantity'])
            timestamp = trade_data['timestamp']
            
            # 价格有效性检查
            if not (self.min_price <= price <= self.max_price):
                return False, f"Price out of range: {price}"
            
            # 数量有效性检查
            if quantity <= 0:
                return False, f"Invalid quantity: {quantity}"
            
            # 时间戳检查
            if not self._is_valid_timestamp(timestamp):
                return False, f"Invalid timestamp: {timestamp}"
            
            return True, "Valid"
            
        except (ValueError, TypeError) as e:
            return False, f"Data type error: {e}"
    
    def validate_orderbook_data(self, orderbook: Dict) -> Tuple[bool, str]:
        """验证订单簿数据"""
        try:
            if 'bids' not in orderbook or 'asks' not in orderbook:
                return False, "Missing bids or asks"
            
            bids = orderbook['bids']
            asks = orderbook['asks']
            
            if not bids or not asks:
                return False, "Empty orderbook"
            
            # 检查价格排序
            bid_prices = [float(bid[0]) for bid in bids if len(bid) >= 2]
            ask_prices = [float(ask[0]) for ask in asks if len(ask) >= 2]
            
            if not bid_prices or not ask_prices:
                return False, "Invalid price data"
            
            # 买单应该降序排列
            if bid_prices != sorted(bid_prices, reverse=True):
                return False, "Bid prices not sorted correctly"
            
            # 卖单应该升序排列
            if ask_prices != sorted(ask_prices):
                return False, "Ask prices not sorted correctly"
            
            # 检查买卖价差
            best_bid = bid_prices[0]
            best_ask = ask_prices[0]
            
            if best_bid >= best_ask:
                return False, f"Invalid spread: bid={best_bid} >= ask={best_ask}"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Orderbook validation error: {e}"
    
    def detect_price_anomaly(self, current_price: float, historical_prices: List[float]) -> Tuple[bool, float]:
        """检测价格异常"""
        if len(historical_prices) < 10:
            return False, 0.0
        
        try:
            # 计算最近价格的平均值和标准差
            recent_prices = historical_prices[-10:]
            mean_price = np.mean(recent_prices)
            std_price = np.std(recent_prices)
            
            if std_price == 0:
                return False, 0.0
            
            # 计算Z-score
            z_score = abs(current_price - mean_price) / std_price
            
            # 如果Z-score超过3，认为是异常
            is_anomaly = z_score > 3
            deviation = abs(current_price - mean_price) / mean_price
            
            return is_anomaly, deviation
            
        except Exception as e:
            self.logger.error(f"Price anomaly detection error: {e}")
            return False, 0.0
    
    def detect_volume_spike(self, current_volume: float, historical_volumes: List[float]) -> Tuple[bool, float]:
        """检测成交量异常"""
        if len(historical_volumes) < 5:
            return False, 0.0
        
        try:
            # 计算平均成交量
            avg_volume = np.mean(historical_volumes[-5:])
            
            if avg_volume == 0:
                return current_volume > 0, float('inf')
            
            # 计算成交量倍数
            volume_ratio = current_volume / avg_volume
            
            # 如果成交量超过平均值的10倍，认为是异常
            is_spike = volume_ratio > self.volume_spike_threshold
            
            return is_spike, volume_ratio
            
        except Exception as e:
            self.logger.error(f"Volume spike detection error: {e}")
            return False, 0.0
    
    def detect_timestamp_gap(self, current_timestamp: int, previous_timestamp: int) -> Tuple[bool, int]:
        """检测时间戳间隙"""
        try:
            # 转换为秒
            if current_timestamp > 1e12:  # 毫秒
                current_ts = current_timestamp / 1000
                prev_ts = previous_timestamp / 1000
            else:  # 秒
                current_ts = current_timestamp
                prev_ts = previous_timestamp
            
            gap_seconds = current_ts - prev_ts
            
            # 如果间隙超过60秒，认为是异常
            is_gap = gap_seconds > 60
            
            return is_gap, int(gap_seconds)
            
        except Exception as e:
            self.logger.error(f"Timestamp gap detection error: {e}")
            return False, 0
    
    def validate_kline_data(self, kline: Dict) -> Tuple[bool, str]:
        """验证K线数据"""
        try:
            required_fields = ['open', 'high', 'low', 'close', 'volume', 'time']
            for field in required_fields:
                if field not in kline:
                    return False, f"Missing required field: {field}"
            
            open_price = float(kline['open'])
            high_price = float(kline['high'])
            low_price = float(kline['low'])
            close_price = float(kline['close'])
            volume = float(kline['volume'])
            
            # OHLC逻辑检查
            if not (low_price <= open_price <= high_price):
                return False, f"Invalid OHLC: open {open_price} not in [{low_price}, {high_price}]"
            
            if not (low_price <= close_price <= high_price):
                return False, f"Invalid OHLC: close {close_price} not in [{low_price}, {high_price}]"
            
            # 价格范围检查
            if not (self.min_price <= high_price <= self.max_price):
                return False, f"High price out of range: {high_price}"
            
            # 成交量检查
            if volume < 0:
                return False, f"Negative volume: {volume}"
            
            return True, "Valid"
            
        except (ValueError, TypeError) as e:
            return False, f"Kline data type error: {e}"
    
    def calculate_data_quality_score(self, validation_results: List[Dict]) -> float:
        """计算数据质量评分 (0-100)"""
        if not validation_results:
            return 0.0
        
        try:
            total_checks = len(validation_results)
            valid_checks = sum(1 for result in validation_results if result.get('valid', False))
            
            # 基础分数
            base_score = (valid_checks / total_checks) * 100
            
            # 根据异常类型扣分
            penalty = 0
            for result in validation_results:
                if not result.get('valid', False):
                    error_type = result.get('error_type', 'unknown')
                    if error_type == 'price_anomaly':
                        penalty += 5
                    elif error_type == 'volume_spike':
                        penalty += 3
                    elif error_type == 'timestamp_gap':
                        penalty += 2
                    else:
                        penalty += 1
            
            final_score = max(0, base_score - penalty)
            return round(final_score, 2)
            
        except Exception as e:
            self.logger.error(f"Quality score calculation error: {e}")
            return 0.0
    
    def _is_valid_timestamp(self, timestamp) -> bool:
        """检查时间戳有效性"""
        try:
            if isinstance(timestamp, str):
                ts = int(timestamp)
            else:
                ts = int(timestamp)
            
            # 检查时间戳范围 (2020年到2030年)
            if ts < 1577836800:  # 2020-01-01
                return False
            if ts > 1893456000:  # 2030-01-01
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def update_stats(self, validation_result: Dict):
        """更新验证统计信息"""
        self.validation_stats['total_trades'] += 1
        
        if not validation_result.get('valid', True):
            self.validation_stats['invalid_trades'] += 1
            
            error_type = validation_result.get('error_type')
            if error_type == 'price_anomaly':
                self.validation_stats['price_anomalies'] += 1
            elif error_type == 'volume_spike':
                self.validation_stats['volume_anomalies'] += 1
            elif error_type == 'timestamp_gap':
                self.validation_stats['timestamp_gaps'] += 1
        
        self.validation_stats['last_validation'] = datetime.now()
    
    def get_validation_report(self) -> Dict:
        """获取验证报告"""
        total = self.validation_stats['total_trades']
        if total == 0:
            return {
                'data_quality_score': 0,
                'total_validations': 0,
                'validation_rate': 0,
                'anomaly_rate': 0,
                'breakdown': self.validation_stats.copy()
            }
        
        invalid = self.validation_stats['invalid_trades']
        valid_rate = ((total - invalid) / total) * 100
        anomaly_rate = (invalid / total) * 100
        
        return {
            'data_quality_score': 100 - anomaly_rate,
            'total_validations': total,
            'validation_rate': round(valid_rate, 2),
            'anomaly_rate': round(anomaly_rate, 2),
            'breakdown': self.validation_stats.copy()
        }
