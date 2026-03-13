"""
Luminaut Phase 1: Simple Binance Data Collection Test

This script tests the Binance WebSocket connection and collects
order book and trade data for validation.

Usage:
    python scripts/quick_data_test.py --duration-minutes 5 --instrument BTCUSDT
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BinanceDataCollector:
    """Simple Binance data collector for testing."""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.orderbook_updates = []
        self.trade_updates = []
        self.feature_vectors = []
        self.start_time = None
        
    async def collect_data(self, duration_minutes: int = 5):
        """Collect data from Binance WebSocket."""
        try:
            import websockets
            
            # WebSocket URLs
            ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@depth10@1000ms/{self.symbol.lower()}@trade"
            
            logger.info(f"Connecting to Binance WebSocket: {ws_url}")
            logger.info(f"Collecting data for {duration_minutes} minutes...")
            
            self.start_time = time.time()
            end_time = self.start_time + (duration_minutes * 60)
            
            async with websockets.connect(ws_url) as websocket:
                logger.info("Connected to Binance WebSocket")
                
                while time.time() < end_time:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(), 
                            timeout=10.0
                        )
                        
                        import json
                        data = json.loads(message)
                        
                        # Process order book update
                        if 'bids' in data and 'asks' in data:
                            self._process_orderbook(data)
                        
                        # Process trade
                        elif 'e' in data and data['e'] == 'trade':
                            self._process_trade(data)
                        
                        # Print progress every minute
                        elapsed = (time.time() - self.start_time) / 60
                        if int(elapsed) > 0 and int(elapsed) % 1 == 0:
                            logger.info(f"Progress: {int(elapsed)}/{duration_minutes} minutes")
                            logger.info(f"  - Orderbook updates: {len(self.orderbook_updates)}")
                            logger.info(f"  - Trade updates: {len(self.trade_updates)}")
                        
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing message: {e}")
                        continue
            
            logger.info(f"\nCollection complete! Duration: {duration_minutes} minutes")
            logger.info(f"Total orderbook updates: {len(self.orderbook_updates)}")
            logger.info(f"Total trade updates: {len(self.trade_updates)}")
            
            # Generate summary report
            self._generate_report()
            
        except ImportError:
            logger.error("websockets package not installed. Installing...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
            logger.info("Please re-run the script")
        except Exception as e:
            logger.error(f"Error during data collection: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_orderbook(self, data: dict):
        """Process order book update."""
        try:
            bids = [(float(p), float(q)) for p, q in data.get('bids', [])]
            asks = [(float(p), float(q)) for p, q in data.get('asks', [])]
            
            if bids and asks:
                best_bid = bids[0][0]
                best_ask = asks[0][0]
                mid_price = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
                spread_bps = (spread / mid_price) * 10000
                
                self.orderbook_updates.append({
                    'timestamp': datetime.now().isoformat(),
                    'ts_event': int(time.time() * 1e9),
                    'best_bid': best_bid,
                    'best_ask': best_ask,
                    'mid_price': mid_price,
                    'spread': spread,
                    'spread_bps': spread_bps,
                    'bid_depth': sum(q for _, q in bids),
                    'ask_depth': sum(q for _, q in asks),
                })
        except Exception as e:
            logger.debug(f"Error processing orderbook: {e}")
    
    def _process_trade(self, data: dict):
        """Process trade tick."""
        try:
            trade = {
                'timestamp': datetime.now().isoformat(),
                'ts_event': int(time.time() * 1e9),
                'price': float(data.get('p', 0)),
                'quantity': float(data.get('q', 0)),
                'is_buyer_maker': data.get('m', False),
            }
            self.trade_updates.append(trade)
        except Exception as e:
            logger.debug(f"Error processing trade: {e}")
    
    def _generate_report(self):
        """Generate data quality report."""
        print("\n" + "=" * 60)
        print("DATA COLLECTION REPORT")
        print("=" * 60)
        
        # Orderbook statistics
        if self.orderbook_updates:
            df_ob = pd.DataFrame(self.orderbook_updates)
            print(f"\nOrderbook Updates: {len(df_ob)}")
            print(f"  Mid Price - Mean: {df_ob['mid_price'].mean():.2f}, "
                  f"Std: {df_ob['mid_price'].std():.2f}")
            print(f"  Spread (bps) - Mean: {df_ob['spread_bps'].mean():.2f}, "
                  f"Std: {df_ob['spread_bps'].std():.2f}")
            print(f"  Bid Depth - Mean: {df_ob['bid_depth'].mean():.4f}, "
                  f"Std: {df_ob['bid_depth'].std():.4f}")
            print(f"  Ask Depth - Mean: {df_ob['ask_depth'].mean():.4f}, "
                  f"Std: {df_ob['ask_depth'].std():.4f}")
            
            # Check for data gaps
            if len(df_ob) > 1:
                time_diffs = df_ob['ts_event'].diff().dropna()
                avg_interval = time_diffs.mean() / 1e9  # Convert to seconds
                print(f"  Avg Update Interval: {avg_interval:.2f} seconds")
        
        # Trade statistics
        if self.trade_updates:
            df_trades = pd.DataFrame(self.trade_updates)
            print(f"\nTrade Updates: {len(df_trades)}")
            print(f"  Price - Mean: {df_trades['price'].mean():.2f}, "
                  f"Std: {df_trades['price'].std():.2f}")
            print(f"  Quantity - Mean: {df_trades['quantity'].mean():.4f}, "
                  f"Std: {df_trades['quantity'].std():.4f}")
            
            buy_volume = df_trades[~df_trades['is_buyer_maker']]['quantity'].sum()
            sell_volume = df_trades[df_trades['is_buyer_maker']]['quantity'].sum()
            total_volume = buy_volume + sell_volume
            if total_volume > 0:
                print(f"  Buy Ratio: {buy_volume / total_volume:.2%}")
                print(f"  Sell Ratio: {sell_volume / total_volume:.2%}")
        
        # Save data to CSV
        output_dir = Path("data/catalog")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if self.orderbook_updates:
            ob_file = output_dir / f"orderbook_test_{timestamp}.csv"
            pd.DataFrame(self.orderbook_updates).to_csv(ob_file, index=False)
            print(f"\nOrderbook data saved to: {ob_file}")
        
        if self.trade_updates:
            trade_file = output_dir / f"trades_test_{timestamp}.csv"
            pd.DataFrame(self.trade_updates).to_csv(trade_file, index=False)
            print(f"Trade data saved to: {trade_file}")
        
        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Quick Binance data collection test"
    )
    parser.add_argument(
        "--instrument",
        type=str,
        default="BTCUSDT",
        help="Trading pair symbol (default: BTCUSDT)",
    )
    parser.add_argument(
        "--duration-minutes",
        type=int,
        default=5,
        help="Collection duration in minutes (default: 5)",
    )
    
    args = parser.parse_args()
    
    collector = BinanceDataCollector(symbol=args.instrument)
    
    try:
        asyncio.run(collector.collect_data(duration_minutes=args.duration_minutes))
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")


if __name__ == "__main__":
    main()
