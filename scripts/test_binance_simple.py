"""
简化版 Binance 数据采集测试

直接使用 Binance WebSocket API 采集数据，不依赖 NautilusTrader
用于快速验证数据采集功能
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict
import pandas as pd
import websockets
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleBinanceCollector:
    """简化版 Binance 数据采集器"""
    
    def __init__(self, symbol: str = "btcusdt"):
        self.symbol = symbol.lower()
        self.order_book_data: List[dict] = []
        self.trade_data: List[dict] = []
        self.start_time = None
        
        # WebSocket URLs
        self.orderbook_ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@depth10@1000ms"
        self.trade_ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@trade"
        
        logger.info(f"初始化 Binance 数据采集器: {symbol.upper()}")
    
    async def collect_orderbook(self, duration_seconds: int):
        """采集订单簿数据"""
        logger.info(f"📊 开始采集订单簿数据: {self.orderbook_ws_url}")
        
        try:
            async with websockets.connect(self.orderbook_ws_url) as websocket:
                logger.info("✅ 订单簿 WebSocket 连接成功")
                
                count = 0
                start = time.time()
                
                while (time.time() - start) < duration_seconds:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)
                        
                        # 提取订单簿数据
                        if 'bids' in data and 'asks' in data:
                            timestamp = time.time()
                            
                            bids = [[float(p), float(q)] for p, q in data['bids']]
                            asks = [[float(p), float(q)] for p, q in data['asks']]
                            
                            # 计算指标
                            best_bid = bids[0][0] if bids else 0
                            best_ask = asks[0][0] if asks else 0
                            mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
                            spread = best_ask - best_bid if best_bid and best_ask else 0
                            spread_bps = (spread / mid_price * 10000) if mid_price > 0 else 0
                            
                            bid_volume = sum(q for _, q in bids[:10])
                            ask_volume = sum(q for _, q in asks[:10])
                            lob_imbalance = bid_volume / ask_volume if ask_volume > 0 else 1.0
                            
                            snapshot = {
                                'timestamp': timestamp,
                                'datetime': datetime.fromtimestamp(timestamp).isoformat(),
                                'best_bid': best_bid,
                                'best_ask': best_ask,
                                'mid_price': mid_price,
                                'spread': spread,
                                'spread_bps': spread_bps,
                                'bid_volume_10': bid_volume,
                                'ask_volume_10': ask_volume,
                                'lob_imbalance': lob_imbalance,
                            }
                            
                            # 添加10档报价
                            for i in range(min(10, len(bids))):
                                snapshot[f'bid_price_{i}'] = bids[i][0]
                                snapshot[f'bid_volume_{i}'] = bids[i][1]
                            
                            for i in range(min(10, len(asks))):
                                snapshot[f'ask_price_{i}'] = asks[i][0]
                                snapshot[f'ask_volume_{i}'] = asks[i][1]
                            
                            self.order_book_data.append(snapshot)
                            count += 1
                            
                            # 每分钟报告一次
                            if count % 60 == 0:
                                logger.info(
                                    f"📊 订单簿更新 #{count} | "
                                    f"中间价: ${mid_price:.2f} | "
                                    f"价差: {spread_bps:.2f}bps"
                                )
                    
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"处理订单簿消息错误: {e}")
                
                logger.info(f"✅ 订单簿采集完成: {count} 条记录")
        
        except Exception as e:
            logger.error(f"订单簿 WebSocket 错误: {e}")
    
    async def collect_trades(self, duration_seconds: int):
        """采集交易数据"""
        logger.info(f"💱 开始采集交易数据: {self.trade_ws_url}")
        
        try:
            async with websockets.connect(self.trade_ws_url) as websocket:
                logger.info("✅ 交易 WebSocket 连接成功")
                
                count = 0
                start = time.time()
                
                while (time.time() - start) < duration_seconds:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        data = json.loads(message)
                        
                        if 'p' in data and 'q' in data:  # price and quantity
                            trade = {
                                'timestamp': data['T'] / 1000,  # 转换为秒
                                'datetime': datetime.fromtimestamp(data['T'] / 1000).isoformat(),
                                'price': float(data['p']),
                                'quantity': float(data['q']),
                                'is_buyer_maker': data['m'],  # True = 卖单, False = 买单
                                'trade_id': data['t'],
                            }
                            
                            self.trade_data.append(trade)
                            count += 1
                            
                            # 每100笔交易报告一次
                            if count % 100 == 0:
                                logger.info(f"💱 交易更新 #{count} | 价格: ${trade['price']:.2f}")
                    
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"处理交易消息错误: {e}")
                
                logger.info(f"✅ 交易采集完成: {count} 条记录")
        
        except Exception as e:
            logger.error(f"交易 WebSocket 错误: {e}")
    
    async def run(self, duration_minutes: int = 5):
        """运行数据采集"""
        self.start_time = time.time()
        duration_seconds = duration_minutes * 60
        
        logger.info("=" * 70)
        logger.info(f"🚀 开始 Binance 数据采集: {self.symbol.upper()}")
        logger.info("=" * 70)
        logger.info(f"持续时间: {duration_minutes} 分钟 ({duration_seconds} 秒)")
        logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        # 并行采集订单簿和交易数据
        try:
            await asyncio.gather(
                self.collect_orderbook(duration_seconds),
                self.collect_trades(duration_seconds),
            )
        except KeyboardInterrupt:
            logger.info("\n\n🛑 用户中断，正在保存数据...")
        except Exception as e:
            logger.error(f"运行错误: {e}")
        finally:
            self.save_data()
    
    def save_data(self):
        """保存数据到CSV"""
        import os
        os.makedirs("data/catalog", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存订单簿数据
        if self.order_book_data:
            df_ob = pd.DataFrame(self.order_book_data)
            filename = f"data/catalog/binance_orderbook_{self.symbol}_{timestamp}.csv"
            df_ob.to_csv(filename, index=False)
            logger.info(f"✅ 订单簿数据已保存: {filename}")
            logger.info(f"   共 {len(df_ob)} 条记录")
        else:
            logger.warning("⚠️  无订单簿数据")
        
        # 保存交易数据
        if self.trade_data:
            df_trade = pd.DataFrame(self.trade_data)
            filename = f"data/catalog/binance_trades_{self.symbol}_{timestamp}.csv"
            df_trade.to_csv(filename, index=False)
            logger.info(f"✅ 交易数据已保存: {filename}")
            logger.info(f"   共 {len(df_trade)} 条记录")
            
            # 计算 VWAP
            if len(df_trade) > 0:
                total_pv = (df_trade['price'] * df_trade['quantity']).sum()
                total_v = df_trade['quantity'].sum()
                vwap = total_pv / total_v if total_v > 0 else 0
                logger.info(f"   VWAP: ${vwap:.2f}")
        else:
            logger.warning("⚠️  无交易数据")
        
        # 统计报告
        elapsed = time.time() - self.start_time if self.start_time else 0
        logger.info("=" * 70)
        logger.info("📊 采集统计")
        logger.info("=" * 70)
        logger.info(f"运行时长: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
        logger.info(f"订单簿更新: {len(self.order_book_data)} 次")
        logger.info(f"交易笔数: {len(self.trade_data)} 笔")
        if elapsed > 0:
            logger.info(f"订单簿频率: {len(self.order_book_data)/elapsed:.2f} 次/秒")
            logger.info(f"交易频率: {len(self.trade_data)/elapsed:.2f} 笔/秒")
        logger.info("=" * 70)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Binance 数据采集测试（简化版）")
    parser.add_argument(
        "--symbol",
        type=str,
        default="BTCUSDT",
        help="交易对符号（默认: BTCUSDT）"
    )
    parser.add_argument(
        "--duration-minutes",
        type=int,
        default=5,
        help="采集持续时间（分钟，默认5）"
    )
    
    args = parser.parse_args()
    
    collector = SimpleBinanceCollector(symbol=args.symbol)
    await collector.run(duration_minutes=args.duration_minutes)


if __name__ == "__main__":
    asyncio.run(main())
