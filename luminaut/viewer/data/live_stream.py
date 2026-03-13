import asyncio
import json
import websockets
import pandas as pd
from datetime import datetime
import threading
import time
import logging

class LiveStream:
    def __init__(self, symbol='btcusdt', callback=None, depth_callback=None, trades_callback=None):
        self.symbol = symbol.lower()
        self.callback = callback  # K线更新回调
        self.depth_callback = depth_callback # 订单簿更新回调
        self.trades_callback = trades_callback # 成交明细更新回调
        
        # 组合流 URL: 同时订阅 trade 和 depth10
        # 格式: /stream?streams=<stream1>/<stream2>
        base_url = "wss://stream.binance.com:9443/stream?streams="
        streams = f"{self.symbol}@trade/{self.symbol}@depth10@100ms"
        self.ws_url = f"{base_url}{streams}"
        
        self.running = False
        self._thread = None
        
        # 实时K线聚合状态
        self.current_bar = None
        self.last_update_time = None
        
        # 错误处理和重连机制
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # seconds
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _run_loop(self):
        while self.running:
            try:
                asyncio.run(self._listen())
            except Exception as e:
                self.logger.error(f"WebSocket loop error: {e}")
                if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
                    self._schedule_reconnect()
                else:
                    self.logger.error("Max reconnection attempts reached. Stopping.")
                    self.running = False
                    break
    
    def _schedule_reconnect(self):
        """安排重连"""
        self.reconnect_attempts += 1
        delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))  # 指数退避
        self.logger.info(f"Scheduling reconnect attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
        
        time.sleep(delay)
        if self.running:
            self.logger.info(f"Attempting to reconnect... (attempt {self.reconnect_attempts})")
    
    def _check_heartbeat(self):
        """检查心跳，如果超时则触发重连"""
        if time.time() - self.last_heartbeat > self.heartbeat_interval:
            self.logger.warning("Heartbeat timeout, triggering reconnect")
            raise ConnectionError("Heartbeat timeout")

    async def _listen(self):
        # 注意: 组合流返回的数据格式略有不同 {"stream": "...", "data": {...}}
        websocket = None
        try:
            websocket = await asyncio.wait_for(websockets.connect(self.ws_url), timeout=10)
            self.logger.info(f"🟢 Connected to {self.ws_url}")
            self.reconnect_attempts = 0  # 重置重连计数
            self.last_heartbeat = time.time()
            
            while self.running:
                try:
                    # 设置接收超时
                    msg = await asyncio.wait_for(websocket.recv(), timeout=self.heartbeat_interval)
                    payload = json.loads(msg)
                    
                    # 更新心跳
                    self.last_heartbeat = time.time()
                    
                    stream_name = payload.get('stream', '')
                    data = payload.get('data', {})
                    
                    if 'trade' in stream_name:
                        self._process_trade(data)
                    elif 'depth' in stream_name:
                        self._process_depth(data)
                        
                except asyncio.TimeoutError:
                    self._check_heartbeat()
                    continue
                except json.JSONDecodeError as e:
                    self.logger.warning(f"JSON decode error: {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Message processing error: {e}")
                    import traceback
                    traceback.print_exc()
                    break
                    
        except websockets.exceptions.ConnectionClosed as e:
            self.logger.error(f"WebSocket connection closed: {e}")
            raise
        except websockets.exceptions.InvalidURI as e:
            self.logger.error(f"Invalid WebSocket URI: {e}")
            raise
        except asyncio.TimeoutError:
            self.logger.error("Connection timeout")
            raise
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
            raise
        finally:
            if websocket:
                await websocket.close()
                self.logger.info("WebSocket connection closed")

    def _process_depth(self, data):
        """处理订单簿数据"""
        try:
            # 验证数据格式
            if not isinstance(data, dict) or 'bids' not in data or 'asks' not in data:
                self.logger.warning(f"Invalid depth data format: {data}")
                return
            
            bids = data.get('bids', [])
            asks = data.get('asks', [])
            
            # 验证订单簿数据
            if not bids or not asks:
                self.logger.warning("Empty order book data")
                return
            
            # 数据格式: [[price, quantity], ...]
            # 验证价格和数量
            for bid in bids[:5]:  # 只验证前5档
                if len(bid) < 2 or float(bid[0]) <= 0 or float(bid[1]) < 0:
                    self.logger.warning(f"Invalid bid data: {bid}")
                    return
                    
            for ask in asks[:5]:  # 只验证前5档
                if len(ask) < 2 or float(ask[0]) <= 0 or float(ask[1]) < 0:
                    self.logger.warning(f"Invalid ask data: {ask}")
                    return
            
            # 调用回调
            if self.depth_callback:
                try:
                    self.depth_callback(data)
                except Exception as e:
                    self.logger.error(f"Depth callback error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Depth data processing error: {e}, data: {data}")
            
    def _process_trade(self, trade_data):
        try:
            # 验证必要字段
            required_fields = ['p', 'q', 'T', 'm']
            if not all(field in trade_data for field in required_fields):
                self.logger.warning(f"Invalid trade data: missing required fields {trade_data}")
                return
            
            # trade_data format form binance @trade:
            # "p": "price", "q": "quantity", "T": trade time (ms), "m": is_buyer_maker
            price = float(trade_data['p'])
            qty = float(trade_data['q'])
            ts_ms = trade_data['T']
            is_buyer_maker = trade_data['m']
            
            # 数据验证
            if price <= 0 or qty <= 0:
                self.logger.warning(f"Invalid trade values: price={price}, qty={qty}")
                return
            
            # 1. 触发成交明细回调
            if self.trades_callback:
                trade_info = {
                    'time': ts_ms, 
                    'price': price, 
                    'qty': qty, 
                    'side': 'SELL' if is_buyer_maker else 'BUY' # maker是买单 -> taker是卖单
                }
                try:
                    self.trades_callback(trade_info)
                except Exception as e:
                    self.logger.error(f"Trade callback error: {e}")
            
            # 2. 聚合K线逻辑 (同前)
            ts_sec = ts_ms // 1000
            bar_time = (ts_sec // 60) * 60
            
            if self.current_bar is None or self.current_bar['time'] != bar_time:
                # 新K线
                self.current_bar = {
                    'time': bar_time,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': qty
                }
            else:
                # 更新当前K线
                self.current_bar['high'] = max(self.current_bar['high'], price)
                self.current_bar['low'] = min(self.current_bar['low'], price)
                self.current_bar['close'] = price
                self.current_bar['volume'] += qty
                
            # K线回调
            if self.callback:
                try:
                    self.callback(self.current_bar)
                except Exception as e:
                    self.logger.error(f"K-line callback error: {e}")
                    
        except (ValueError, KeyError) as e:
            self.logger.error(f"Trade data processing error: {e}, data: {trade_data}")
        except Exception as e:
            self.logger.error(f"Unexpected error in trade processing: {e}")
