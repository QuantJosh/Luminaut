"""
Luminaut Phase 1: Data Collection Runner

This script runs the data collection process for the specified duration.
It connects to Binance, subscribes to order book and trade data, and
saves aggregated features to disk.

Usage:
    python run_phase1_collection.py --duration-minutes 60 --instrument BTCUSDT
"""

import argparse
import asyncio
import signal
import sys
import logging
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nautilus_trader.adapters.binance.config import BinanceDataClientConfig
from nautilus_trader.adapters.binance.factories import BinanceLiveDataClientFactory
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import MessageBus, Clock
from nautilus_trader.config import LoggingConfig, TradingNodeConfig
from nautilus_trader.core.datetime import unix_nanos_to_dt
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId, Venue

from luminaut.phase1_data_collection.actors.feature_builder import LuminautFeatureBuilder


class DataCollectionRunner:
    """Manages the data collection process."""
    
    def __init__(
        self,
        instrument: str,
        duration_minutes: int,
        binance_api_key: str = "",
        binance_api_secret: str = "",
    ):
        """
        Initialize the data collection runner.
        
        Parameters:
            instrument: Trading pair symbol (e.g., 'BTCUSDT')
            duration_minutes: How long to collect data
            binance_api_key: Binance API key (optional for public data)
            binance_api_secret: Binance API secret (optional for public data)
        """
        self.instrument = instrument
        self.duration_minutes = duration_minutes
        self.binance_api_key = binance_api_key
        self.binance_api_secret = binance_api_secret
        self.node: Optional[TradingNode] = None
        self.shutdown_requested = False
        
        print("=" * 40)
        print("Luminaut Data Collection")
        print("=" * 40)
        print(f"Instrument: {instrument}")
        print(f"Duration: {duration_minutes} minutes")
        print("=" * 40)
    
    def setup_signal_handlers(self):
        """Set up graceful shutdown on Ctrl+C."""
        def signal_handler(sig, frame):
            print("\n\n[WARN] Shutdown requested. Stopping gracefully...")
            self.shutdown_requested = True
            if self.node:
                asyncio.create_task(self.node.stop_async())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Run the data collection process."""
        try:
            # Configure logging
            logging_config = LoggingConfig(
                log_level="INFO",
            )
            
            # Configure Binance data client
            binance_config = BinanceDataClientConfig(
                api_key=self.binance_api_key if self.binance_api_key else None,
                api_secret=self.binance_api_secret if self.binance_api_secret else None,
                account_type="spot",  # Use spot market
            )
            
            # Configure trading node
            node_config = TradingNodeConfig(
                data_clients={
                    "BINANCE": binance_config,
                },
                logging=logging_config,
                timeout_connection=30.0,
                timeout_reconciliation=10.0,
                timeout_portfolio=10.0,
                timeout_disconnection=10.0,
            )
            
            # Create trading node
            self.node = TradingNode(config=node_config)
            
            # Create instrument ID
            instrument_id = InstrumentId.from_str(f"{self.instrument}.BINANCE")
            
            # Create feature builder actor
            feature_builder = LuminautFeatureBuilder(
                instrument_id=instrument_id,
                lob_depth=10,
                snapshot_interval_ms=1000,
            )
            
            # Add actor to node
            self.node.add_actor(feature_builder)
            
            # Start the node
            print("[INFO] Starting data collection...")
            await self.node.start_async()
            
            print("[INFO] Connected to Binance. Collecting data...")
            print(f"[INFO] Will run for {self.duration_minutes} minutes (or until Ctrl+C)")
            
            # Run for specified duration
            duration_seconds = self.duration_minutes * 60
            for elapsed in range(0, duration_seconds, 10):
                if self.shutdown_requested:
                    break
                
                await asyncio.sleep(10)
                
                # Print progress every minute
                if (elapsed + 10) % 60 == 0:
                    minutes_elapsed = (elapsed + 10) // 60
                    print(f"[INFO] {minutes_elapsed}/{self.duration_minutes} minutes elapsed...")
            
            if not self.shutdown_requested:
                print(f"\n[INFO] Collection complete! Ran for {self.duration_minutes} minutes")
            
        except Exception as e:
            print(f"\n[ERROR] Error during data collection: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Stop the node
            if self.node:
                print("[INFO] Stopping trading node...")
                await self.node.stop_async()
                print("[INFO] Shutdown complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Luminaut Phase 1 data collection"
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
        default=60,
        help="Collection duration in minutes (default: 60)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="Binance API key (optional for public data)",
    )
    parser.add_argument(
        "--api-secret",
        type=str,
        default="",
        help="Binance API secret (optional for public data)",
    )
    
    args = parser.parse_args()
    
    # Create runner
    runner = DataCollectionRunner(
        instrument=args.instrument,
        duration_minutes=args.duration_minutes,
        binance_api_key=args.api_key,
        binance_api_secret=args.api_secret,
    )
    
    # Set up signal handlers
    runner.setup_signal_handlers()
    
    # Run collection
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")


if __name__ == "__main__":
    main()
