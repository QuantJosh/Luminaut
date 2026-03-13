"""
Lighter.xyz 数据适配器

这个模块提供了一个简单的 Lighter.xyz 数据采集器，用于收集订单簿和交易数据。
注意：这是一个独立的采集器，不依赖 NautilusTrader，用于快速验证 Lighter.xyz API。

使用方法:
    python scripts/test_lighter_data.py --duration-minutes 5
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LighterDataCollector:
    """
    Lighter.xyz 数据采集器
    
    收集订单簿快照和交易数据，保存为CSV格式
    """
    
    def __init__(
        self,
        market_ids: List[int] = None,
        output_dir: str = "data/catalog",
    ):
        """
        初始化数据采集器
        
        Parameters:
            market_ids: 要订阅的市场ID列表（默认: [0] - BTC/USDC）
            output_dir: 数据输出目录
        """
        self.market_ids = market_ids if market_ids else [0]  # 默认订阅 BTC/USDC
        self.output_dir = output_dir
        
        # 数据存储
        self.order_books: Dict[int, dict] = {}
        self.order_book_history: List[dict] = []
        self.trade_history: List[dict] = []
        
        # 统计信息
        self.start_time = None
        self.order_book_updates = 0
        self.total_updates = 0
        
        logger.info(f"初始化 Lighter 数据采集器")
        logger.info(f"订阅市场ID: {self.market_ids}")
        logger.info(f"输出目录: {self.output_dir}")
    
    def on_order_book_update(self, market_id: int, order_book: dict):
        """
        订单簿更新回调
        
        Parameters:
            market_id: 市场ID
            order_book: 订单簿数据
        """
        try:
            # 更新内部状态
            self.order_books[market_id] = order_book
            self.order_book_updates += 1
            self.total_updates += 1
            
            # 记录时间戳
            timestamp = time.time()
            dt = datetime.fromtimestamp(timestamp)
            
            # 提取订单簿数据
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            # 计算基本指标
            best_bid = float(bids[0]['price']) if bids else 0.0
            best_ask = float(asks[0]['price']) if asks else 0.0
            mid_price = (best_bid + best_ask) / 2 if (best_bid > 0 and best_ask > 0) else 0.0
            spread = best_ask - best_bid if (best_bid > 0 and best_ask > 0) else 0.0
            spread_bps = (spread / mid_price * 10000) if mid_price > 0 else 0.0
            
            # 计算订单簿深度
            bid_volume = sum(float(b.get('size', 0)) for b in bids[:10])
            ask_volume = sum(float(a.get('size', 0)) for a in asks[:10])
            lob_imbalance = bid_volume / ask_volume if ask_volume > 0 else 1.0
            
            # 保存快照
            snapshot = {
                'timestamp': timestamp,
                'datetime': dt.isoformat(),
                'market_id': market_id,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'mid_price': mid_price,
                'spread': spread,
                'spread_bps': spread_bps,
                'bid_volume_10': bid_volume,
                'ask_volume_10': ask_volume,
                'lob_imbalance': lob_imbalance,
                'bid_levels': len(bids),
                'ask_levels': len(asks),
            }
            
            # 添加前10档报价
            for i in range(min(10, len(bids))):
                snapshot[f'bid_price_{i}'] = float(bids[i].get('price', 0))
                snapshot[f'bid_size_{i}'] = float(bids[i].get('size', 0))
            
            for i in range(min(10, len(asks))):
                snapshot[f'ask_price_{i}'] = float(asks[i].get('price', 0))
                snapshot[f'ask_size_{i}'] = float(asks[i].get('size', 0))
            
            self.order_book_history.append(snapshot)
            
            # 定期日志
            if self.order_book_updates % 60 == 0:
                logger.info(
                    f"📊 市场 {market_id} | "
                    f"中间价: ${mid_price:.2f} | "
                    f"价差: {spread_bps:.2f}bps | "
                    f"已更新: {self.order_book_updates}次"
                )
            
        except Exception as e:
            logger.error(f"处理订单簿更新时出错: {e}")
    
    async def run(self, duration_seconds: int = 300):
        """
        运行数据采集
        
        Parameters:
            duration_seconds: 采集持续时间（秒）
        """
        try:
            # 尝试导入 lighter SDK
            try:
                import lighter
            except ImportError:
                logger.error("❌ lighter-python SDK 未安装")
                logger.error("请运行: pip install lighter-python")
                return
            
            self.start_time = time.time()
            
            logger.info("=" * 60)
            logger.info("🚀 开始 Lighter.xyz 数据采集")
            logger.info("=" * 60)
            logger.info(f"持续时间: {duration_seconds} 秒 ({duration_seconds//60} 分钟)")
            logger.info(f"市场ID: {self.market_ids}")
            
            # 创建 WebSocket 客户端
            client = lighter.WsClient(
                order_book_ids=self.market_ids,
                on_order_book_update=self.on_order_book_update,
            )
            
            # 运行客户端（在后台线程）
            import threading
            
            def run_client():
                try:
                    client.run()
                except Exception as e:
                    logger.error(f"WebSocket 客户端错误: {e}")
            
            thread = threading.Thread(target=run_client, daemon=True)
            thread.start()
            
            logger.info("✅ WebSocket 连接已建立")
            logger.info(f"⏱️  将运行 {duration_seconds//60} 分钟...")
            
            # 等待指定时间
            elapsed = 0
            while elapsed < duration_seconds:
                await asyncio.sleep(10)
                elapsed += 10
                
                # 进度报告
                if elapsed % 60 == 0:
                    minutes = elapsed // 60
                    total_minutes = duration_seconds // 60
                    logger.info(f"⏳ {minutes}/{total_minutes} 分钟已完成...")
            
            logger.info("⏱️  采集时间已到，正在保存数据...")
            
        except KeyboardInterrupt:
            logger.info("\n\n🛑 用户中断，正在保存数据...")
        except Exception as e:
            logger.error(f"运行时错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 保存数据
            self.save_data()
    
    def save_data(self):
        """保存采集的数据到CSV"""
        import os
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # 保存订单簿历史
            if self.order_book_history:
                df_orderbook = pd.DataFrame(self.order_book_history)
                filename = f"{self.output_dir}/lighter_orderbook_{timestamp}.csv"
                df_orderbook.to_csv(filename, index=False)
                logger.info(f"✅ 订单簿数据已保存: {filename}")
                logger.info(f"   共 {len(df_orderbook)} 条记录")
            else:
                logger.warning("⚠️  无订单簿数据可保存")
            
            # 统计报告
            elapsed = time.time() - self.start_time if self.start_time else 0
            logger.info("=" * 60)
            logger.info("📊 采集统计")
            logger.info("=" * 60)
            logger.info(f"运行时长: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
            logger.info(f"订单簿更新: {self.order_book_updates} 次")
            logger.info(f"平均更新频率: {self.order_book_updates/elapsed:.2f} 次/秒" if elapsed > 0 else "N/A")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"保存数据时出错: {e}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Lighter.xyz 数据采集测试")
    parser.add_argument(
        "--duration-minutes",
        type=int,
        default=5,
        help="采集持续时间（分钟，默认5）"
    )
    parser.add_argument(
        "--market-id",
        type=int,
        default=0,
        help="市场ID（默认0 = BTC/USDC）"
    )
    
    args = parser.parse_args()
    
    collector = LighterDataCollector(
        market_ids=[args.market_id],
        output_dir="data/catalog",
    )
    
    await collector.run(duration_seconds=args.duration_minutes * 60)


if __name__ == "__main__":
    asyncio.run(main())
