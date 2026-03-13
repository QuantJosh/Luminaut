# Luminaut System Design Document

**Version:** 1.0  
**Date:** 2026-01-03  
**Status:** Draft

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      LUMINAUT SYSTEM                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   Phase 1    │   │   Phase 2    │   │   Phase 3    │        │
│  │     Data     │──>│  Embedding   │──>│   Trading    │        │
│  │  Collection  │   │   Research   │   │  Deployment  │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Overview

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Data Layer** | NautilusTrader + Parquet | Real-time data ingestion & storage |
| **Feature Engineering** | Python + NumPy | Transform raw data to ML features |
| **Embedding Model** | PyTorch → ONNX | Market state compression |
| **Trading Strategy** | NautilusTrader Strategy | Signal generation & execution |
| **Exchange Adapters** | WebSocket + REST | Binance/Lighter.xyz integration |
| **Monitoring** | Logging + Metrics | System observability |

---

## 2. Phase 1: Data Collection Architecture

### 2.1 Component Diagram

```
Exchange (Binance)
      │
      ├─ WebSocket: Order Book (1000ms)
      ├─ WebSocket: Trade Ticks
      │
      ↓
┌─────────────────────────────────┐
│  LuminautFeatureBuilder (Actor) │
├─────────────────────────────────┤
│  - on_order_book_snapshots()    │
│  - on_trade_tick()               │
│  - on_timer_1s()                 │
└─────────────────────────────────┘
      │
      ↓ (every 1s)
┌─────────────────────────────────┐
│     Feature Vector (50-60 dim)  │
│  - VWAP, OFI, Spread, etc.      │
└─────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────┐
│   ParquetDataCatalog            │
│   (Persistent Storage)          │
└─────────────────────────────────┘
```

### 2.2 Data Flow

**Step 1: Order Book Update**
```python
def on_order_book_snapshots(self, snapshot: OrderBookSnapshot):
    # Store latest 10-level bid/ask
    self.current_lob = snapshot
    self.lob_history.append(snapshot)
```

**Step 2: Trade Tick Accumulation**
```python
def on_trade_tick(self, tick: TradeTick):
    current_second = tick.ts_event // 1_000_000_000
    self.trades_buffer[current_second].append(tick)
```

**Step 3: Second-Level Aggregation**
```python
def on_timer_1s(self):
    # Calculate features from accumulated data
    features = FeatureVector(
        vwap=self._calculate_vwap(),
        ofi=self._calculate_ofi(),
        spread=self.current_lob.spread,
        # ... more features
    )
    # Write to catalog
    self.catalog.write_data(features)
```

### 2.3 Critical Design Decisions

**Decision 1: Event-Driven vs Polling**
- **Choice:** Event-driven (NautilusTrader Actor)
- **Rationale:** Lower latency, natural alignment with exchange events

**Decision 2: Feature Calculation Timing**
- **Choice:** Use data available at beginning of second
- **Rationale:** Prevents look-ahead bias

**Decision 3: Storage Format**
- **Choice:** Parquet via NautilusTrader catalog
- **Rationale:** Fast columnar queries, native integration

---

## 3. Phase 2: Embedding Model Architecture

### 3.1 Model Architecture Diagram

```
Input Features (50-60 dim)
      │
      ├─────────────────┬─────────────────┐
      │                 │                 │
      ↓                 ↓                 ↓
┌──────────┐    ┌──────────┐    ┌──────────┐
│   LOB    │    │  Trade   │    │ Derived  │
│ Encoder  │    │  Flow    │    │ Features │
│  (CNN)   │    │ Encoder  │    │  (MLP)   │
└──────────┘    └──────────┘    └──────────┘
      │                 │                 │
      └─────────────────┴─────────────────┘
                        │
                        ↓
              ┌──────────────────┐
              │ Cross-Attention  │
              │  Fusion Layer    │
              └──────────────────┘
                        │
                        ↓
              ┌──────────────────┐
              │   Transformer    │
              │ Temporal Encoder │
              └──────────────────┘
                        │
                        ↓
              Embedding (64/128 dim)
                        │
      ├─────────────────┼─────────────────┐
      │                 │                 │
      ↓                 ↓                 ↓
Reconstruction    Contrastive       Direction
   (MSE)           (InfoNCE)      Prediction
```

### 3.2 Implementation Details

**LOB Encoder**
```python
class LOBEncoder(nn.Module):
    def __init__(self):
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        
    def forward(self, lob_data):
        # lob_data: (batch, 1, 10, 4)  # 10 levels × 4 fields
        x = F.relu(self.conv1(lob_data))
        x = F.relu(self.conv2(x))
        x = self.pool(x).flatten(1)
        return x
```

**Multi-task Loss**
```python
total_loss = (
    1.0 * reconstruction_loss +
    0.5 * contrastive_loss +
    0.3 * direction_loss
)
```

### 3.3 Training Pipeline

```
Historical Data (Parquet)
      ↓
Feature Extraction
      ↓
Data Augmentation (temporal jittering, noise)
      ↓
Batch Formation (256 samples)
      ↓
Forward Pass → Multi-task Loss
      ↓
Backward Pass → Optimizer Step
      ↓
Validation (every epoch)
      ↓
ONNX Export (best model)
```

---

## 4. Phase 3: Trading Strategy Architecture

### 4.1 Strategy Component Diagram

```
┌──────────────────────────────────────────┐
│      LuminautStrategy (Strategy)         │
├──────────────────────────────────────────┤
│                                          │
│  ┌────────────────────────────────┐     │
│  │  Feature Builder (inline)      │     │
│  │  - Replicate Phase 1 logic     │     │
│  └────────────────────────────────┘     │
│              │                           │
│              ↓                           │
│  ┌────────────────────────────────┐     │
│  │  ONNX Model Inference          │     │
│  │  - Load production_embedder    │     │
│  └────────────────────────────────┘     │
│              │                           │
│              ↓                           │
│  ┌────────────────────────────────┐     │
│  │  Signal Extraction             │     │
│  │  - Predict direction           │     │
│  │  - Calculate confidence        │     │
│  └────────────────────────────────┘     │
│              │                           │
│              ↓                           │
│  ┌────────────────────────────────┐     │
│  │  Execution Logic               │     │
│  │  - Fill probability model      │     │
│  │  - Risk checks                 │     │
│  │  - Order submission            │     │
│  └────────────────────────────────┘     │
│                                          │
└──────────────────────────────────────────┘
              │
              ↓
    ┌──────────────────┐
    │ Lighter Adapter  │
    │ (ExecutionClient)│
    └──────────────────┘
              │
              ↓
    Lighter.xyz Exchange
```

### 4.2 Key Algorithms

**Fill Probability Estimation**
```python
def estimate_fill_probability(
    target_price: float,
    order_size: float,
    lob: OrderBook
) -> float:
    """
    Estimate P(fill) for limit order
    
    Key: DO NOT assume price touched = filled
    Must model queue position
    """
    level = lob.get_level(target_price)
    if not level:
        return 0.0
        
    # Estimate our position (assume middle of queue)
    queue_position = level.volume / 2
    
    # Get historical trade volume at this level
    avg_volume = get_historical_volume(target_price)
    
    # Calculate fill probability
    if queue_position + order_size <= avg_volume:
        return 1.0
    elif queue_position >= avg_volume:
        return 0.0
    else:
        return (avg_volume - queue_position) / order_size
```

**Slippage Estimation**
```python
def estimate_slippage(
    side: OrderSide,
    quantity: float,
    lob: OrderBook
) -> float:
    """Walk through order book to estimate market impact"""
    remaining = quantity
    total_cost = 0.0
    
    levels = lob.asks if side == BUY else lob.bids
    
    for level in levels:
        if remaining <= 0:
            break
        fill_qty = min(remaining, level.volume)
        total_cost += fill_qty * level.price
        remaining -= fill_qty
        
    if remaining > 0:
        return float('inf')  # Cannot fill
        
    avg_price = total_cost / quantity
    mid_price = lob.mid_price()
    return abs(avg_price - mid_price) / mid_price
```

### 4.3 Risk Management

**Pre-Trade Checks**
```python
def pre_trade_checks(signal_strength, fill_prob, position):
    checks = {
        'signal_threshold': signal_strength > 0.6,
        'fill_probability': fill_prob > 0.7,
        'position_limit': abs(position) < MAX_POSITION,
        'daily_loss': current_pnl > -MAX_DAILY_LOSS,
    }
    return all(checks.values()), checks
```

---

## 5. Data Models

### 5.1 FeatureVector Schema

```python
@dataclass
class FeatureVector:
    ts_event: int  # nanoseconds
    ts_init: int
    
    # Price features
    vwap: float
    last_price: float
    mid_price: float
    
    # LOB features (10 levels each)
    bid_prices: np.ndarray  # shape: (10,)
    bid_volumes: np.ndarray
    ask_prices: np.ndarray
    ask_volumes: np.ndarray
    
    # Trade flow features
    trade_count: int
    buy_ratio: float
    sell_ratio: float
    total_volume: float
    
    # Microstructure features
    spread: float
    ofi: float  # Order Flow Imbalance
    lob_imbalance: float
```

### 5.2 Database Schema (Parquet)

```
catalog/
├── data/
│   └── feature_vector.parquet/
│       ├── instrument_id=BTCUSDT/
│       │   ├── date=20260103/
│       │   │   └── part-0.parquet
│       │   └── date=20260104/
│       └── instrument_id=ETHUSDT/
```

---

## 6. Integration Points

### 6.1 Exchange Integration

**Binance (Data Collection)**
- **Endpoint:** WebSocket wss://stream.binance.com:9443
- **Streams:** 
  - `btcusdt@depth10@1000ms` (Order Book)
  - `btcusdt@trade` (Trades)
- **Authentication:** Not required for public streams

**Lighter.xyz (Live Trading)**
- **Adapter:** Custom `LighterExecutionClient`
- **Methods:**
  - `submit_order()`
  - `cancel_order()`
  - `modify_order()`
- **Events:** Order fills, updates, cancellations

### 6.2 Model Integration

**Training → Inference Pipeline**
```
PyTorch Model (.pt)
    ↓
ONNX Export
    ↓
production_embedder.onnx
    ↓
onnxruntime.InferenceSession
    ↓
Loaded in Strategy.on_start()
```

---

## 7. Deployment Architecture

### 7.1 System Deployment

```
Production Server (Linux/Windows)
    │
    ├─ data/catalog/  (Parquet storage)
    ├─ luminaut/
    │   ├─ phase1_data_collection/
    │   ├─ phase2_embedding_research/
    │   └─ phase3_trading_deployment/
    │       ├─ strategies/
    │       ├─ adapters/
    │       └─ models/production_embedder.onnx
    │
    └─ scripts/
        ├─ run_phase3_live.py  ← Main entry point
        └─ monitoring_dashboard.py
```

### 7.2 Monitoring Stack

```
Strategy (metrics) → Logs → File/Console
                  → Alerts → Slack/SMS
                  → Dashboard → Web UI (Plotly)
```

---

## 8. Performance Considerations

### 8.1 Latency Budget

```
Total Latency (<100ms target):
├─ Exchange → Local: <20ms
├─ Feature Calculation: <10ms
├─ Model Inference: <20ms
├─ Decision Logic: <5ms
└─ Order Submission: <45ms
```

### 8.2 Optimization Strategies

1. **ONNX Inference:** 3-5× faster than PyTorch
2. **NumPy Vectorization:** Avoid Python loops in features
3. **Buffer Reuse:** Pre-allocate arrays
4. **Connection Pooling:** Reuse WebSocket/HTTP connections

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/test_feature_builder.py
def test_ofi_calculation():
    prev_lob = create_lob(bids=[...], asks=[...])
    curr_lob = create_lob(bids=[...], asks=[...])
    ofi = calculate_ofi(prev_lob, curr_lob)
    assert ofi == expected_value
```

### 9.2 Integration Tests

```python
# tests/test_strategy.py
def test_end_to_end_backtest():
    engine = BacktestEngine(...)
    engine.add_strategy(LuminautStrategy(...))
    engine.run()
    assert engine.trader.statistics.sharpe_ratio > 1.0
```

---

## 10. Security & Compliance

### 10.1 API Key Management
- Store in environment variables (not code)
- Use `.env` file for local development
- Use secret management in production (AWS Secrets Manager, etc.)

### 10.2 Data Privacy
- No PII collected
- Trade data kept locally
- Encrypted data at rest (optional)

---

## 11. Appendices

### A. Technology Choices Rationale

| Choice | Alternatives | Reason |
|--------|-------------|--------|
| NautilusTrader | Freqtrade, Hummingbot | Only supports LOB+Tick, event-driven |
| ONNX | TorchScript, TensorRT | Cross-platform, mature ecosystem |
| Parquet | HDF5, CSV | Columnar format, fast queries |
| Lighter.xyz | Binance | Zero fees for small orders |

### B. Key Formulas

**VWAP:**
```
VWAP = Σ(Price_i × Volume_i) / Σ(Volume_i)
```

**OFI (Order Flow Imbalance):**
```
OFI_t = Σ_levels [ΔBidVol_t - ΔAskVol_t]
```

**Sharpe Ratio:**
```
Sharpe = (R_strategy - R_risk_free) / σ_strategy
```

---

**Document Status:** Ready for Implementation  
**Next Steps:** Begin Phase 1 implementation with `LuminautFeatureBuilder`

