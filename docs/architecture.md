# Luminaut System Architecture

**Version:** 1.0  
**Date:** 2026-01-03

---

## 1. Overall System Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                          LUMINAUT SYSTEM                               │
│                   Cryptocurrency Quantitative Trading Bot             │
└───────────────────────────────────────────────────────────────────────┘

                                   │
                ┌──────────────────┴──────────────────┐
                │                                     │
                ▼                                     ▼
     ┌──────────────────┐                  ┌──────────────────┐
     │ DATA COLLECTION  │                  │   LIVE TRADING   │
     │   (Binance)      │                  │  (Lighter.xyz)   │
     │   WebSocket      │                  │   WebSocket      │
     └──────────────────┘                  └──────────────────┘
                │                                     │
                │ L2 OrderBook + Trades               │ Orders & Fills
                ▼                                     ▼
     ┌─────────────────────────────────────────────────────────────┐
     │           PHASE 1: DATA INFRASTRUCTURE                      │
     │  ┌────────────────────────────────────────────────────┐    │
     │  │      LuminautFeatureBuilder (Actor)                 │    │
     │  │                                                     │    │
     │  │  • Subscribe to OrderBook deltas (1000ms)          │    │
     │  │  • Subscribe to TradeTicks (real-time)             │    │
     │  │  • Aggregate per second                            │    │
     │  │  • Calculate 50+ features                          │    │
     │  │  • Output: FeatureVector                           │    │
     │  └────────────────────────────────────────────────────┘    │
     │                          │                                  │
     │                          │ FeatureVector (50-60 dim)        │
     │                          ▼                                  │
     │            ┌──────────────────────────┐                     │
     │            │  ParquetDataCatalog      │                     │
     │            │  (Persistent Storage)    │                     │
     │            └──────────────────────────┘                     │
     └─────────────────────────────────────────────────────────────┘
                                   │
                                   │ Historical Data
                                   ▼
     ┌─────────────────────────────────────────────────────────────┐
     │           PHASE 2: EMBEDDING MODEL                          │
     │                                                              │
     │  ┌────────────────────────────────────────────────────┐    │
     │  │          LuminautEmbedder (PyTorch)                 │    │
     │  │                                                     │    │
     │  │    Input: FeatureVector (50-60 dim)                │    │
     │  │    ├─ LOB Encoder (CNN)                            │    │
     │  │    ├─ Trade Flow Encoder (MLP)                     │    │
     │  │    ├─ Cross-Attention Fusion                       │    │
     │  │    └─ Transformer Temporal Encoder                 │    │
     │  │    Output: Embedding (64/128 dim)                  │    │
     │  │                                                     │    │
     │  │    Training:                                        │    │
     │  │    • Masked Reconstruction (MSE)                   │    │
     │  │    • Contrastive Learning (InfoNCE)                │    │
     │  │    • Direction Prediction (CrossEntropy)           │    │
     │  └────────────────────────────────────────────────────┘    │
     │                          │                                  │
     │                          │ Export                           │
     │                          ▼                                  │
     │              ┌────────────────────────┐                     │
     │              │ production_embedder    │                     │
     │              │      .onnx             │                     │
     │              │  (<20ms inference)     │                     │
     │              └────────────────────────┘                     │
     └─────────────────────────────────────────────────────────────┘
                                   │
                                   │ Load Model
                                   ▼
     ┌─────────────────────────────────────────────────────────────┐
     │           PHASE 3: TRADING STRATEGY                         │
     │                                                              │
     │  ┌────────────────────────────────────────────────────┐    │
     │  │      LuminautStrategy (Strategy)                    │    │
     │  │                                                     │    │
     │  │  Real-time Data → Features → Embedding → Signal    │    │
     │  │                                                     │    │
     │  │  Components:                                        │    │
     │  │  1. Feature Builder (inline)                       │    │
     │  │  2. ONNX Model Inference                           │    │
     │  │  3. Signal Extraction                              │    │
     │  │  4. Risk Checks                                    │    │
     │  │  5. Order Execution                                │    │
     │  └────────────────────────────────────────────────────┘    │
     │                          │                                  │
     │                          │ Orders                           │
     │                          ▼                                  │
     │  ┌────────────────────────────────────────────────────┐    │
     │  │      LighterExecutionClient                         │    │
     │  │      (Exchange Adapter)                             │    │
     │  │                                                     │    │
     │  │  • Submit/Cancel/Modify Orders                     │    │
     │  │  • WebSocket Order Updates                         │    │
     │  │  • Fill Notifications                              │    │
     │  └────────────────────────────────────────────────────┘    │
     └─────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow Architecture (Phase 1)

```
EXCHANGE                      FEATURE BUILDER                    STORAGE
(Binance)                    (Actor)                         (Parquet)

┌─────────┐
│ L2 Book │────┐
│ 1000ms  │    │
└─────────┘    │
               │    ┌───────────────────────────────────┐
┌─────────┐    │    │                                   │
│  Trade  │────┼───→│  on_order_book_deltas()          │
│  Ticks  │    │    │  • Update current_orderbook      │
└─────────┘    │    │                                   │
               │    │  on_trade_tick()                  │
               │    │  • Accumulate in buffer           │
               │    │  • Trigger aggregation on new sec │
               │    │                                   │
               │    │  on_timer_1s()                    │
               └───→│  • Fallback aggregation           │
                    │                                   │
                    │  _aggregate_features()            │
                    │  ┌─────────────────────────────┐ │
                    │  │ 1. Extract LOB (10 levels)  │ │
                    │  │ 2. Calculate VWAP           │ │
                    │  │ 3. Calculate OFI            │ │
                    │  │ 4. Calculate spreads        │ │
                    │  │ 5. Calculate ratios         │ │
                    │  │ 6. Create FeatureVector     │ │
                    │  └─────────────────────────────┘ │
                    │          │                        │
                    └──────────┼────────────────────────┘
                               │
                               │ FeatureVector
                               │ (50-60 dimensions)
                               ▼
                    ┌────────────────────┐
                    │  SaveToFile()      │
                    │  • CSV backup      │
                    │  • Parquet catalog │
                    └────────────────────┘
                               │
                               ▼
                    ┌────────────────────┐
                    │ data/catalog/      │
                    │ features_*.csv     │
                    └────────────────────┘
```

---

## 3. Feature Vector Schema

```
FeatureVector (per second, ~50-60 dimensions)
│
├─ Timestamps (2)
│  ├─ ts_event: int64 (nanoseconds)
│  └─ ts_init: int64 (nanoseconds)
│
├─ Price Features (3)
│  ├─ vwap: float64
│  ├─ last_price: float64
│  └─ mid_price: float64
│
├─ Order Book Features (40)
│  ├─ bid_prices: float64[10]
│  ├─ bid_volumes: float64[10]
│  ├─ ask_prices: float64[10]
│  └─ ask_volumes: float64[10]
│
├─ Trade Flow Features (6)
│  ├─ trade_count: int
│  ├─ buy_volume: float64
│  ├─ sell_volume: float64
│  ├─ total_volume: float64
│  ├─ buy_ratio: float64
│  └─ sell_ratio: float64
│
└─ Microstructure Features (4)
   ├─ spread: float64
   ├─ spread_bps: float64
   ├─ ofi: float64 (Order Flow Imbalance)
   └─ lob_imbalance: float64

TOTAL: 55 dimensions
```

---

## 4. Embedding Model Architecture (Phase 2)

```
Input: FeatureVector (55 dim)
│
├─────────────────┬─────────────────┬─────────────────┐
│                 │                 │                 │
▼                 ▼                 ▼                 ▼
LOB               Trade             Price             Derived
Features          Flow              Features          Features
(40 dim)          (6 dim)           (3 dim)           (6 dim)
│                 │                 │                 │
▼                 ▼                 ▼                 ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│   CNN    │   │   MLP    │   │   MLP    │   │   MLP    │
│ Encoder  │   │ Encoder  │   │ Encoder  │   │ Encoder  │
│          │   │          │   │          │   │          │
│ 40→64    │   │ 6→16     │   │ 3→8      │   │ 6→16     │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
      │              │              │              │
      └──────────────┴──────────────┴──────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Cross-Attention │
            │  Fusion Layer   │
            │   (104 → 128)   │
            └─────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  Transformer    │
            │ Temporal Encoder│
            │    (Lº=4)       │
            └─────────────────┘
                     │
                     ▼
              Embedding
              (128 dim)
                     │
      ┌──────────────┼──────────────┐
      │              │              │
      ▼              ▼              ▼
Reconstruction  Contrastive   Direction
   Decoder      Learning      Classifier
      │              │              │
      ▼              ▼              ▼
   MSE Loss    InfoNCE Loss   CE Loss
      │              │              │
      └──────────────┴──────────────┘
                     │
                     ▼
            Combined Loss
     α·Recon + β·Contra + γ·Direction
```

---

## 5. Trading Strategy Decision Flow (Phase 3)

```
Real-time Market Data
         │
         ▼
┌────────────────────┐
│ Feature Builder    │
│ (inline in         │
│  LuminautStrategy) │
└────────────────────┘
         │
         │ FeatureVector (55 dim)
         ▼
┌────────────────────┐
│ ONNX Inference     │
│ production_        │
│ embedder.onnx      │
└────────────────────┘
         │
         │ Embedding (128 dim)
         ▼
┌────────────────────┐
│ Signal Extraction  │
│ • Direction: UP/DN │
│ • Confidence: 0-1  │
└────────────────────┘
         │
         ▼
    Confidence
    > Threshold?
         │
    ┌────┴────┐
    NO        YES
    │         │
    ▼         ▼
 Return   ┌────────────────────┐
          │ Fill Probability   │
          │ Estimation         │
          │ • Queue position   │
          │ • LOB depth        │
          └────────────────────┘
                    │
                    ▼
               Fill Prob
               > 0.7?
                    │
               ┌────┴────┐
               NO        YES
               │         │
               ▼         ▼
            Return   ┌────────────────────┐
                     │ Risk Checks        │
                     │ • Position limit   │
                     │ • Daily loss       │
                     │ • Slippage est.    │
                     └────────────────────┘
                              │
                              ▼
                         All Pass?
                              │
                         ┌────┴────┐
                         NO        YES
                         │         │
                         ▼         ▼
                      Return   ┌────────────────────┐
                               │ Order Submission   │
                               │ • Limit order only │
                               │ • Lighter.xyz      │
                               └────────────────────┘
                                        │
                                        ▼
                               ┌────────────────────┐
                               │ Monitor Fill       │
                               │ • WebSocket events │
                               │ • Update position  │
                               └────────────────────┘
```

---

## 6. Technology Stack

```
┌─────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER                       │
├─────────────────────────────────────────────────────────┤
│ Python 3.10+                                            │
│ • luminaut/ (custom logic)                              │
│ • scripts/ (entry points)                               │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              FRAMEWORK & LIBRARIES                       │
├─────────────────────────────────────────────────────────┤
│ TRADING:         NautilusTrader (Rust-core)             │
│ ML TRAINING:     PyTorch 2.0+                           │
│ ML INFERENCE:    ONNX + onnxruntime                     │
│ DATA:            Pandas, NumPy                          │
│ VIZ:             Plotly                                 │
│ EXPERIMENTS:     Weights & Biases                       │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 DATA STORAGE                             │
├─────────────────────────────────────────────────────────┤
│ FORMAT:          Apache Parquet (columnar)              │
│ CATALOG:         NautilusTrader ParquetDataCatalog      │
│ LOCATION:        data/catalog/                          │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               EXTERNAL SERVICES                          │
├─────────────────────────────────────────────────────────┤
│ DATA SOURCE:     Binance (WebSocket + REST)             │
│ LIVE TRADING:    Lighter.xyz (WebSocket + REST)         │
│ MONITORING:      Weights & Biases (cloud)               │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Deployment Infrastructure

```
┌───────────────────────────────────────────────────────┐
│              PRODUCTION SERVER                        │
│          (Linux/Windows, 4+ cores, 8GB+ RAM)          │
├───────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────────────────────────────┐   │
│  │ scripts/run_phase3_live.py                    │   │
│  │ (Main entry point)                            │   │
│  └──────────────────────────────────────────────┘   │
│                      │                                │
│                      ▼                                │
│  ┌──────────────────────────────────────────────┐   │
│  │ NautilusTrader TradingNode                    │   │
│  │ ├─ LuminautStrategy                           │   │
│  │ ├─ LighterExecutionClient                     │   │
│  │ └─ RiskEngine                                 │   │
│  └──────────────────────────────────────────────┘   │
│                      │                                │
│     ┌────────────────┼────────────────┐              │
│     │                │                │              │
│     ▼                ▼                ▼              │
│  ┌─────┐       ┌─────────┐      ┌────────┐         │
│  │Model│       │  Data   │      │  Logs  │         │
│  │.onnx│       │Catalog  │      │ Files  │         │
│  └─────┘       └─────────┘      └────────┘         │
│                                                        │
└───────────────────────────────────────────────────────┘
          │                         │
          │ Orders/Data             │ Metrics
          ▼                         ▼
   ┌─────────────┐          ┌──────────────┐
   │ Lighter.xyz │          │   Monitoring │
   │  Exchange   │          │   Dashboard  │
   └─────────────┘          └──────────────┘
```

---

## 8. Latency Budget

```
Total End-to-End Latency: <100ms (target)

┌─────────────────────────────────────────────────────┐
│                                                      │
│  Exchange Event → Decision → Order Submission       │
│                                                      │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐│
│  │ Net  │→ │Feature│→│ONNX  │→ │Signal│→ │Order ││
│  │<20ms │  │<10ms  │  │<20ms │  │<5ms  │  │<45ms ││
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘│
│                                                      │
└─────────────────────────────────────────────────────┘

Optimization Techniques:
• ONNX (3-5× faster than PyTorch)
• NumPy vectorization (no Python loops)
• Pre-allocated buffers (avoid allocation)
• Connection pooling (reuse WebSockets)
• Asynchronous I/O (non-blocking)
```

---

## 9. Security Architecture

```
┌───────────────────────────────────────────────┐
│           SECURITY LAYERS                      │
├───────────────────────────────────────────────┤
│                                                │
│  API Credentials:                              │
│  ┌──────────────────────────────────────┐    │
│  │ • Stored in .env (local)             │    │
│  │ • Environment variables (prod)       │    │
│  │ • Never logged or displayed          │    │
│  │ • Encrypted at rest                  │    │
│  └──────────────────────────────────────┘    │
│                                                │
│  Network:                                      │
│  ┌──────────────────────────────────────┐    │
│  │ • TLS/SSL for all exchange comms     │    │
│  │ • WebSocket WSS (encrypted)          │    │
│  │ • API signature verification         │    │
│  └──────────────────────────────────────┘    │
│                                                │
│  Risk Controls:                                │
│  ┌──────────────────────────────────────┐    │
│  │ • Max position limits                │    │
│  │ • Daily loss auto-shutdown           │    │
│  │ • Pre-trade risk checks              │    │
│  │ • Slippage thresholds                │    │
│  └──────────────────────────────────────┘    │
│                                                │
└───────────────────────────────────────────────┘
```

---

## 10. Monitoring & Observability

```
┌────────────────────────────────────────────────────┐
│         LUMINAUT MONITORING DASHBOARD              │
├────────────────────────────────────────────────────┤
│                                                     │
│  ┌────────────────────┐  ┌───────────────────┐   │
│  │  System Health     │  │  Trading Metrics  │   │
│  ├────────────────────┤  ├───────────────────┤   │
│  │ • CPU Usage        │  │ • Current PnL     │   │
│  │ • Memory Usage     │  │ • Win Rate        │   │
│  │ • Disk I/O         │  │ • Fill Rate       │   │
│  │ • Network Latency  │  │ • Avg Slippage    │   │
│  │ • Heartbeat (<10s) │  │ • Open Orders     │   │
│  └────────────────────┘  └───────────────────┘   │
│                                                     │
│  ┌────────────────────┐  ┌───────────────────┐   │
│  │  Data Quality      │  │  Model Performance│   │
│  ├────────────────────┤  ├───────────────────┤   │
│  │ • Events/sec       │  │ • Inference ms    │   │
│  │ • Missing data %   │  │ • Signal strength │   │
│  │ • VWAP accuracy    │  │ • Prediction acc  │   │
│  │ • OFI correlation  │  │ • Embedding drift │   │
│  └────────────────────┘  └───────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │  Alerts (Last 24h)                           │ │
│  ├──────────────────────────────────────────────┤ │
│  │  [CRITICAL] Daily loss exceeded threshold    │ │
│  │  [WARNING] Fill rate dropped to 45%          │ │
│  │  [INFO] Model inference latency 18ms         │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
└────────────────────────────────────────────────────┘

Alerting Channels:
├─ CRITICAL → SMS/PagerDuty (<10s)
├─ WARNING  → Slack (<60s)
└─ INFO     → Log files
```

---

**Document Status:** Complete  
**Last Updated:** 2026-01-03  
**Version:** 1.0

