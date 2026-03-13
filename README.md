# Luminaut

**Cryptocurrency Quantitative Trading Bot with Deep Learning Embeddings**

---

## 🎯 Project Overview

Luminaut is an autonomous trading bot that uses deep learning embeddings to capture market microstructure signals and execute profitable trades on zero-fee DEX platforms.

### Core Features

- **Deep Learning Embeddings**: Transform high-dimensional market data (Order Book + Trades) into compact, information-rich vectors
- **High-Frequency Analysis**: Second-level market microstructure analysis
- **Zero-Fee Trading**: Optimized for Lighter.xyz DEX with zero transaction fees
- **Production-Ready**: Built on NautilusTrader's enterprise-grade trading framework

### Key Technologies

- **Framework**: [NautilusTrader](https://nautilustrader.io/) (Rust-core event-driven system)
- **ML Pipeline**: PyTorch → ONNX → onnxruntime
- **Deployment**: Lighter.xyz (primary) / Binance (validation)

---

## 📁 Project Structure

```
luminaut/
├── docs/                          # Documentation
│   ├── requirements.md            # Detailed requirements
│   ├── design.md                  # System design
│   └── implementation_plan.md     # 8-week implementation plan
│
├── luminaut/
│   ├── phase1_data_collection/    # Phase 1: Data Layer
│   │   ├── actors/
│   │   │   └── feature_builder.py # Real-time feature engineering
│   │   ├── config/
│   │   └── validators/
│   │
│   ├── phase2_embedding_research/ # Phase 2: ML Research
│   │   ├── notebooks/
│   │   ├── models/
│   │   └── experiments/
│   │
│   └── phase3_trading_deployment/ # Phase 3: Trading Strategy
│       ├── strategies/
│       ├── adapters/
│       └── models/
│
├── data/catalog/                  # Parquet data storage
├── scripts/                       # Entry point scripts
└── tests/                         # Unit & integration tests
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- 8GB+ RAM
- Stable internet connection

### Installation

```bash
# Clone the repository
cd Luminaut

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create logs directory
mkdir -p logs
```

### Phase 1: Data Collection

Collect 1 hour of market data from Binance:

```bash
python scripts/run_phase1_collection.py \
    --instrument BTCUSDT \
    --duration-minutes 60
```

**Expected Output:**
- Console logs showing data collection progress
- Feature files saved to `data/catalog/`
- Log file at `logs/luminaut_phase1.log`

**Success Criteria:**
- ✓ Runs for 1 hour without disconnection
- ✓ VWAP within 0.01% of official exchange data
- ✓ Data completeness >99%

---

## 📊 Three-Phase Development

### Phase 1: Data Collection & Validation (Week 1-2)

**Goal**: Establish reliable second-level market data pipeline

**Key Components:**
- `LuminautFeatureBuilder`: Actor that transforms raw LOB/Trades into ML features
- Feature Vector: 50-60 dimensions including VWAP, OFI, spread, etc.
- Data Validation: Ensure quality with statistical checks

**Deliverables:**
- ✅ Working data collection pipeline
- ✅ 1-hour dataset in Parquet format
- ✅ Validation report confirming data quality

### Phase 2: Embedding Research (Week 3-5)

**Goal**: Train deep learning model to embed market state

**Key Components:**
- Multi-branch architecture (LOB Encoder + Trade Flow Encoder)
- Multi-task learning (Reconstruction + Contrastive + Direction Prediction)
- ONNX export for production deployment

**Deliverables:**
- ⏳ Trained PyTorch model
- ⏳ ONNX model with <20ms inference latency
- ⏳ Validation showing >55% direction prediction accuracy

### Phase 3: Trading Deployment (Week 6-8)

**Goal**: Deploy autonomous trading bot

**Key Components:**
- `LuminautStrategy`: Trading strategy using embeddings for signals
- `LighterExecutionClient`: Adapter for Lighter.xyz DEX
- Risk management and monitoring

**Deliverables:**
- ⏳ Backtest with Sharpe ratio >1.0
- ⏳ Testnet validation with >70% fill rate
- ⏳ Live trading: 48 hours without crash

---

## 🧪 Testing

Run unit tests:

```bash
pytest tests/ -v
```

Run with coverage:

```bash
pytest tests/ --cov=luminaut --cov-report=html
```

---

## 📖 Documentation

- **[Requirements Document](docs/requirements.md)**: Detailed functional and non-functional requirements
- **[Design Document](docs/design.md)**: System architecture and technical design
- **[Implementation Plan](docs/implementation_plan.md)**: 8-week development roadmap

---

## ⚠️ Critical Design Principles

### 1. No OHLCV Data
We **DO NOT** use OHLCV (candlestick) data because it is ex-post aggregated and loses critical microstructure information.

**Instead we use:**
- L2 Order Book (10-level depth, 1000ms snapshots)
- Tick-by-Tick Trades (all individual trades)

### 2. Prevent Look-Ahead Bias
All features use **only data available at decision time**. Features are calculated from the beginning of each second, never using future information.

### 3. Realistic Execution Modeling
We **DO NOT** assume "price touched = order filled". Instead:
- Model queue position at each price level
- Estimate fill probability based on historical depth
- Calculate realistic slippage for order sizing

---

## 📈 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Data Collection Uptime | >99% | ⏳ Testing  |
| VWAP Accuracy | <0.01% error | ⏳ Testing |
| Model Inference Latency | <20ms | ⏳ Phase 2 |
| Backtest Sharpe Ratio | >1.0 | ⏳ Phase 3 |
| Live Fill Rate | >70% | ⏳ Phase 3 |

---

## 🛠️ Development Status

- ✅ **Requirements & Design**: Complete
- ✅ **Phase 1 Implementation**: Core components complete
- ⏳ **Phase 1 Validation**: In progress
- ⏳ **Phase 2**: Not started
- ⏳ **Phase 3**: Not started

---

## 📝 License

This project is proprietary and confidential.

---

## 👥 Team

Luminaut Development Team

---

## 🔗 References

- [NautilusTrader Documentation](https://nautilustrader.io/)
- [Lighter.xyz](https://lighter.xyz/)
- [Binance API](https://binance-docs.github.io/)

---

**Current Version:** 0.1.0  
**Last Updated:** 2026-01-03
