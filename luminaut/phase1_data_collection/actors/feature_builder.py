"""
Luminaut Feature Builder Actor

This module implements the LuminautFeatureBuilder actor that collects
real-time market data from exchanges and transforms it into feature vectors
for machine learning model consumption.

Key Requirements:
- Subscribe to L2 Order Book (10-level depth, 1000ms updates)
- Subscribe to tick-by-tick trade data
- Aggregate data every second to create feature vectors
- Calculate VWAP, OFI, LOB imbalance, and other microstructure features
- Store feature vectors in ParquetDataCatalog
- Prevent look-ahead bias (only use data available at decision time)
"""

from collections import defaultdict, deque
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd

from nautilus_trader.common.actor import Actor
from nautilus_trader.common.enums import LogColor
from nautilus_trader.model.data import OrderBookDelta, TradeTick
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.book import OrderBook


class FeatureVector:
    """
    Represents aggregated market features for a single second.
    
    Attributes:
        ts_event: Event timestamp in nanoseconds
        ts_init: Initialization timestamp in nanoseconds
        vwap: Volume-weighted average price
        last_price: Most recent trade price
        mid_price: (bid1 + ask1) / 2
        bid_prices: Top 10 bid prices (numpy array)
        bid_volumes: Top 10 bid volumes (numpy array)
        ask_prices: Top 10 ask prices (numpy array)
        ask_volumes: Top 10 ask volumes (numpy array)
        trade_count: Number of trades in this second
        buy_volume: Total buy-initiated volume
        sell_volume: Total sell-initiated volume
        total_volume: Total trade volume
        buy_ratio: buy_volume / total_volume
        sell_ratio: sell_volume / total_volume
        spread: ask1 - bid1
        spread_bps: spread in basis points from mid
        ofi: Order Flow Imbalance
        lob_imbalance: bid_volume_sum / ask_volume_sum
    """
    
    def __init__(
        self,
        ts_event: int,
        ts_init: int,
        vwap: float,
        last_price: float,
        mid_price: float,
        bid_prices: np.ndarray,
        bid_volumes: np.ndarray,
        ask_prices: np.ndarray,
        ask_volumes: np.ndarray,
        trade_count: int,
        buy_volume: float,
        sell_volume: float,
        total_volume: float,
        buy_ratio: float,
        sell_ratio: float,
        spread: float,
        spread_bps: float,
        ofi: float,
        lob_imbalance: float,
    ):
        self.ts_event = ts_event
        self.ts_init = ts_init
        self.vwap = vwap
        self.last_price = last_price
        self.mid_price = mid_price
        self.bid_prices = bid_prices
        self.bid_volumes = bid_volumes
        self.ask_prices = ask_prices
        self.ask_volumes = ask_volumes
        self.trade_count = trade_count
        self.buy_volume = buy_volume
        self.sell_volume = sell_volume
        self.total_volume = total_volume
        self.buy_ratio = buy_ratio
        self.sell_ratio = sell_ratio
        self.spread = spread
        self.spread_bps = spread_bps
        self.ofi = ofi
        self.lob_imbalance = lob_imbalance
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            'ts_event': self.ts_event,
            'ts_init': self.ts_init,
            'vwap': self.vwap,
            'last_price': self.last_price,
            'mid_price': self.mid_price,
            **{f'bid_price_{i}': self.bid_prices[i] for i in range(len(self.bid_prices))},
            **{f'bid_volume_{i}': self.bid_volumes[i] for i in range(len(self.bid_volumes))},
            **{f'ask_price_{i}': self.ask_prices[i] for i in range(len(self.ask_prices))},
            **{f'ask_volume_{i}': self.ask_volumes[i] for i in range(len(self.ask_volumes))},
            'trade_count': self.trade_count,
            'buy_volume': self.buy_volume,
            'sell_volume': self.sell_volume,
            'total_volume': self.total_volume,
            'buy_ratio': self.buy_ratio,
            'sell_ratio': self.sell_ratio,
            'spread': self.spread,
            'spread_bps': self.spread_bps,
            'ofi': self.ofi,
           'lob_imbalance': self.lob_imbalance,
        }


class LuminautFeatureBuilder(Actor):
    """
    Actor that builds ML features from real-time market data.
    
    This actor subscribes to order book snapshots and trade ticks,
    then aggregates them every second to create feature vectors for
    the embedding model.
    
    Critical Design: To prevent look-ahead bias, features are calculated
    using only data available at the decision time (beginning of second).
    """
    
    def __init__(
        self,
        instrument_id: InstrumentId,
        lob_depth: int = 10,
        snapshot_interval_ms: int = 1000,
    ):
        """
        Initialize the feature builder.
        
        Parameters:
            instrument_id: The instrument to collect data for
            lob_depth: Number of order book levels to track (default: 10)
            snapshot_interval_ms: Order book snapshot interval (default: 1000ms)
        """
        super().__init__()
        
        self.instrument_id = instrument_id
        self.lob_depth = lob_depth
        self.snapshot_interval_ms = snapshot_interval_ms
        
        # Internal state
        self.current_orderbook: Optional[OrderBook] = None
        self.previous_orderbook: Optional[OrderBook] = None
        
        # Trade accumulation buffer (keyed by second timestamp)
        self.current_second_trades: list[TradeTick] = []
        self.current_second = 0
        
        # Feature storage
        self.features_list: list[FeatureVector] = []
        
        # Performance tracking
        self.total_features_generated = 0
        self.last_feature_time = 0
    
    def on_start(self):
        """Actions to perform on actor start."""
        self.log.info(
            f"LuminautFeatureBuilder started for {self.instrument_id}",
            color=LogColor.GREEN,
        )
        
        # Subscribe to order book deltas (will maintain internal order book)
        self.subscribe_order_book_deltas(
            instrument_id=self.instrument_id,
            depth=self.lob_depth,
        )
        
        # Subscribe to trade ticks
        self.subscribe_trade_ticks(
            instrument_id=self.instrument_id,
        )
        
        # Set up 1-second timer for feature aggregation
        self.clock.set_timer(
            name="feature_aggregation",
            interval=pd.Timedelta(seconds=1),
            callback=self.on_timer_1s,
        )
        
        self.log.info("Subscriptions configured successfully")
    
    def on_stop(self):
        """Actions to perform on actor stop."""
        self.log.info(
            f"LuminautFeatureBuilder stopping. Generated {self.total_features_generated} features",
            color=LogColor.YELLOW,
        )
        
        # Save accumulated features to disk if needed
        if self.features_list:
            self._save_features_to_catalog()
    
    def on_order_book_deltas(self, deltas: OrderBookDelta):
        """
        Handle order book delta events.
        
        NautilusTrader automatically maintains an internal order book
        from these deltas, which we can access via self.cache.order_book()
        """
        # Update reference to current order book
        self.current_orderbook = self.cache.order_book(self.instrument_id)
    
    def on_trade_tick(self, tick: TradeTick):
        """
        Handle trade tick events.
        
        Accumulate trades within the current second for aggregation.
        
        Parameters:
            tick: Trade tick event
        """
        # Get the second this trade belongs to
        current_second = tick.ts_event // 1_000_000_000
        
        # If new second, trigger aggregation for previous second
        if self.current_second != 0 and current_second != self.current_second:
            self._aggregate_features(self.current_second)
        
        # Update current second
        self.current_second = current_second
        
        # Add trade to buffer
        self.current_second_trades.append(tick)
    
    def on_timer_1s(self, event):
        """
        Timer callback triggered every second.
        
        This ensures feature aggregation happens even if no trades occur.
        """
        if not self.current_second_trades:
            # No trades in this second, but we can still create features from LOB
            current_second = self.clock.timestamp_ns() // 1_000_000_000
            if current_second != self.current_second:
                self._aggregate_features_no_trades(current_second)
        
        # Log progress periodically
        if self.total_features_generated % 60 == 0 and self.total_features_generated > 0:
            self.log.info(
                f"Generated {self.total_features_generated} features "
                f"({self.total_features_generated // 60} minutes)",
                color=LogColor.BLUE,
            )
    
    def _aggregate_features(self, second_ts: int):
        """
        Aggregate accumulated data into a single feature vector.
        
        Critical: Only uses data available at the beginning of this second
        to prevent look-ahead bias.
        
        Parameters:
            second_ts: The second timestamp to aggregate for
        """
        if not self.current_second_trades:
            return
        
        # Get the order book state at beginning of this second
        # Use previous_orderbook if available, otherwise current
        lob = self.previous_orderbook if self.previous_orderbook else self.current_orderbook
        
        if not lob:
            self.log.warning("No order book available, skipping feature generation")
            self.current_second_trades = []
            return
        
        try:
            # Calculate VWAP from trades
            vwap = self._calculate_vwap(self.current_second_trades)
            
            # Get last trade price
            last_price = float(self.current_second_trades[-1].price)
            
            # Calculate trade volume statistics
            buy_volume = sum(
                float(t.size) for t in self.current_second_trades 
                if t.aggressor_side.name == 'BUY'
            )
            sell_volume = sum(
                float(t.size) for t in self.current_second_trades 
                if t.aggressor_side.name == 'SELL'
            )
            total_volume = buy_volume + sell_volume
            
            buy_ratio = buy_volume / total_volume if total_volume > 0 else 0.5
            sell_ratio = sell_volume / total_volume if total_volume > 0 else 0.5
            
            # Extract LOB features
            bid_prices, bid_volumes = self._extract_lob_side(lob, side='BID')
            ask_prices, ask_volumes = self._extract_lob_side(lob, side='ASK')
            
            # Calculate microstructure features
            mid_price = (bid_prices[0] + ask_prices[0]) / 2 if len(bid_prices) > 0 else last_price
            spread = ask_prices[0] - bid_prices[0] if len(bid_prices) > 0 else 0.0
            spread_bps = (spread / mid_price * 10000) if mid_price > 0 else 0.0
            
            # Calculate OFI (Order Flow Imbalance)
            ofi = self._calculate_ofi(self.previous_orderbook, lob)
            
            # Calculate LOB imbalance
            lob_imbalance = np.sum(bid_volumes) / np.sum(ask_volumes) if np.sum(ask_volumes) > 0 else 1.0
            
            # Create feature vector
            feature = FeatureVector(
                ts_event=second_ts * 1_000_000_000,
                ts_init=self.clock.timestamp_ns(),
                vwap=vwap,
                last_price=last_price,
                mid_price=mid_price,
                bid_prices=bid_prices,
                bid_volumes=bid_volumes,
                ask_prices=ask_prices,
                ask_volumes=ask_volumes,
                trade_count=len(self.current_second_trades),
                buy_volume=buy_volume,
                sell_volume=sell_volume,
                total_volume=total_volume,
                buy_ratio=buy_ratio,
                sell_ratio=sell_ratio,
                spread=spread,
                spread_bps=spread_bps,
                ofi=ofi,
                lob_imbalance=lob_imbalance,
            )
            
            # Store feature
            self.features_list.append(feature)
            self.total_features_generated += 1
            self.last_feature_time = second_ts
            
            # Periodically save to catalog (every 60 seconds)
            if len(self.features_list) >= 60:
                self._save_features_to_catalog()
            
            # Update previous order book for next OFI calculation
            self.previous_orderbook = lob.copy() if lob else None
            
        except Exception as e:
            self.log.error(f"Error aggregating features: {e}")
        
        finally:
            # Clear trades buffer
            self.current_second_trades = []
    
    def _aggregate_features_no_trades(self, second_ts: int):
        """
        Aggregate features when no trades occurred in the second.
        
        Uses LOB-only features with zero trade volume.
        """
        if not self.current_orderbook:
            return
        
        lob = self.current_orderbook
        
        try:
            #Extract LOB features
            bid_prices, bid_volumes = self._extract_lob_side(lob, side='BID')
            ask_prices, ask_volumes = self._extract_lob_side(lob, side='ASK')
            
            mid_price = (bid_prices[0] + ask_prices[0]) / 2 if len(bid_prices) > 0 else 0.0
            spread = ask_prices[0] - bid_prices[0] if len(bid_prices) > 0 else 0.0
            spread_bps = (spread / mid_price * 10000) if mid_price > 0 else 0.0
            
            ofi = self._calculate_ofi(self.previous_orderbook, lob)
            lob_imbalance = np.sum(bid_volumes) / np.sum(ask_volumes) if np.sum(ask_volumes) > 0 else 1.0
            
            feature = FeatureVector(
                ts_event=second_ts * 1_000_000_000,
                ts_init=self.clock.timestamp_ns(),
                vwap=mid_price,  # Use mid price as proxy
                last_price=mid_price,
                mid_price=mid_price,
                bid_prices=bid_prices,
                bid_volumes=bid_volumes,
                ask_prices=ask_prices,
                ask_volumes=ask_volumes,
                trade_count=0,
                buy_volume=0.0,
                sell_volume=0.0,
                total_volume=0.0,
                buy_ratio=0.5,  # Neutral
                sell_ratio=0.5,
                spread=spread,
                spread_bps=spread_bps,
                ofi=ofi,
                lob_imbalance=lob_imbalance,
            )
            
            self.features_list.append(feature)
            self.total_features_generated += 1
            
            if len(self.features_list) >= 60:
                self._save_features_to_catalog()
            
            self.previous_orderbook = lob.copy() if lob else None
            
        except Exception as e:
            self.log.error(f"Error aggregating no-trade features: {e}")
    
    def _calculate_vwap(self, trades: list[TradeTick]) -> float:
        """
        Calculate Volume-Weighted Average Price.
        
        Formula: VWAP = Σ(price_i × volume_i) / Σ(volume_i)
        """
        if not trades:
            return 0.0
        
        total_pv = sum(float(t.price) * float(t.size) for t in trades)
        total_v = sum(float(t.size) for t in trades)
        
        return total_pv / total_v if total_v > 0 else 0.0
    
    def _extract_lob_side(self, lob: OrderBook, side: str) -> tuple[np.ndarray, np.ndarray]:
        """
        Extract prices and volumes from one side of the order book.
        
        Returns:
            (prices, volumes) as numpy arrays of length self.lob_depth
        """
        prices = np.zeros(self.lob_depth, dtype=np.float64)
        volumes = np.zeros(self.lob_depth, dtype=np.float64)
        
        if side == 'BID':
            levels = list(lob.bids())[:self.lob_depth]
        else:  # ASK
            levels = list(lob.asks())[:self.lob_depth]
        
        for i, level in enumerate(levels):
            if i >= self.lob_depth:
                break
            prices[i] = float(level.price)
            volumes[i] = float(level.size)
        
        return prices, volumes
    
    def _calculate_ofi(self, prev_lob: Optional[OrderBook], curr_lob: OrderBook) -> float:
        """
        Calculate Order Flow Imbalance.
        
        Formula: OFI = Σ_levels [Δ(Bid Volume) - Δ(Ask Volume)]
        
        This measures the net change in order book depth between two snapshots.
        Positive OFI indicates buying pressure, negative indicates selling pressure.
        """
        if not prev_lob or not curr_lob:
            return 0.0
        
        ofi = 0.0
        
        # Extract current and previous LOB states
        prev_bid_prices, prev_bid_volumes = self._extract_lob_side(prev_lob, 'BID')
        curr_bid_prices, curr_bid_volumes = self._extract_lob_side(curr_lob, 'BID')
        prev_ask_prices, prev_ask_volumes = self._extract_lob_side(prev_lob, 'ASK')
        curr_ask_prices, curr_ask_volumes = self._extract_lob_side(curr_lob, 'ASK')
        
        # Calculate bid side changes
        for i in range(self.lob_depth):
            if curr_bid_prices[i] > 0 and prev_bid_prices[i] > 0:
                if abs(curr_bid_prices[i] - prev_bid_prices[i]) < 0.01:  # Same price level
                    ofi += (curr_bid_volumes[i] - prev_bid_volumes[i])
        
        # Calculate ask side changes
        for i in range(self.lob_depth):
            if curr_ask_prices[i] > 0 and prev_ask_prices[i] > 0:
                if abs(curr_ask_prices[i] - prev_ask_prices[i]) < 0.01:  # Same price level
                    ofi -= (curr_ask_volumes[i] - prev_ask_volumes[i])
        
        return ofi
    
    def _save_features_to_catalog(self):
        """Save accumulated features to Parquet catalog."""
        if not self.features_list:
            return
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame([f.to_dict() for f in self.features_list])
            
            # Save to catalog (implementation depends on NautilusTrader catalog API)
            # For now, save to CSV as backup
            filename = f"data/catalog/features_{self.instrument_id}_{self.last_feature_time}.csv"
            df.to_csv(filename, index=False)
            
            self.log.info(
                f"Saved {len(self.features_list)} features to {filename}",
                color=LogColor.GREEN,
            )
            
            # Clear the list
            self.features_list = []
            
        except Exception as e:
            self.log.error(f"Error saving features: {e}")
