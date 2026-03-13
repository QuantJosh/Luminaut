# Luminaut Project Requirements Document

**Project Name:** Luminaut  
**Version:** 1.0  
**Date:** 2026-01-03  
**Author:** Luminaut Development Team

---

## 1. Executive Summary

### 1.1 Project Vision
Luminaut is an autonomous cryptocurrency quantitative trading bot that leverages deep learning embeddings and high-frequency market microstructure analysis to execute profitable trades on the Lighter.xyz zero-fee decentralized exchange (DEX).

### 1.2 Core Innovation
The system transforms heterogeneous, high-dimensional financial data (Order Book Depth + Tick-by-Tick trades) into low-dimensional dense vector embeddings that encode maximum market information, enabling prediction of short-term price movements at second-level frequency.

### 1.3 Technology Stack
- **Framework:** NautilusTrader (Rust-core event-driven trading system)
- **ML Pipeline:** PyTorch → ONNX → onnxruntime
- **Deployment:** Lighter.xyz (primary) / Binance (validation)
- **Data Storage:** Parquet-based catalog

---

## 2. Business Requirements

### 2.1 Primary Business Objectives
- **BR-001:** Deploy an autonomous trading bot capable of 24/7 operation without manual intervention
- **BR-002:** Achieve positive risk-adjusted returns (Sharpe Ratio > 1.0) after transaction costs
- **BR-003:** Minimize transaction costs by leveraging zero-fee DEX platforms
- **BR-004:** Operate at capital scales of $500-$5,000 per trade to optimize fee savings

### 2.2 Success Metrics by Phase

#### Phase 1: Data Collection (Week 1-2)
- **BR-011:** Continuous data collection for ≥1 hour without disconnection
- **BR-012:** VWAP accuracy within 0.01% of official K-line close price
- **BR-013:** Data completeness >99% (missing <36 seconds per hour)
- **BR-014:** Order Flow Imbalance (OFI) peaks correlate with price movements

#### Phase 2: Embedding Research (Week 3-5)
- **BR-021:** Reconstruction loss reduction >30% vs baseline model
- **BR-022:** Embedding space shows clear clustering between market regimes (震荡 vs 趋势)
- **BR-023:** Direction prediction accuracy >55% (baseline random=50%)
- **BR-024:** Inference latency <20ms per prediction (99th percentile)

#### Phase 3: Trading Deployment (Week 6-8)
- **BR-031:** Backtest with realistic slippage shows positive expectancy
- **BR-032:** Fill rate >70% on Lighter.xyz testnet
- **BR-033:** Actual slippage vs predicted slippage deviation <20%
- **BR-034:** 48-hour continuous operation without crash or manual intervention

---

## 3. Functional Requirements

### 3.1 Data Collection Module

#### FR-101: Real-time Market Data Ingestion
**Priority:** Critical  
**Description:** System must collect real-time market data from cryptocurrency exchanges

**Requirements:**
- **FR-101.1:** Subscribe to Level 2 Order Book (LOB) snapshots with 10-level depth
- **FR-101.2:** Update LOB at 1000ms intervals
- **FR-101.3:** Subscribe to tick-by-tick trade data with all individual trades
- **FR-101.4:** Capture trade side (Buy/Sell), price, volume, and timestamp
- **FR-101.5:** Support Binance WebSocket API for data validation
- **FR-101.6:** Support Lighter.xyz API for production deployment

**Acceptance Criteria:**
- Zero disconnections during 1-hour test period
- All trade events captured within 50ms of occurrence
- Order book depth always contains 10 levels on bid and ask sides

#### FR-102: Feature Engineering
**Priority:** Critical  
**Description:** Transform raw market data into structured feature vectors

**Requirements:**
- **FR-102.1:** Calculate VWAP (Volume Weighted Average Price) per second
- **FR-102.2:** Compute Order Flow Imbalance (OFI) from LOB changes
- **FR-102.3:** Calculate LOB imbalance (Σ Bid Vol / Σ Ask Vol)
- **FR-102.4:** Compute aggressor ratio (Buy Volume / Total Volume)
- **FR-102.5:** Calculate spread (Ask1 - Bid1)
- **FR-102.6:** Maintain trade count per second
- **FR-102.7:** Generate feature vectors with ~50-60 dimensions per second

**Acceptance Criteria:**
- VWAP calculation matches official exchange close price within 0.01%
- OFI calculation follows academic formula: OFI = Δ(Bid Volume) - Δ(Ask Volume)
- No look-ahead bias in feature calculation (only use data available at decision time)

#### FR-103: Data Storage and Retrieval
**Priority:** Critical  
**Description:** Persist collected data for model training and backtesting

**Requirements:**
- **FR-103.1:** Store feature vectors in Parquet format via NautilusTrader DataCatalog
- **FR-103.2:** Maintain timestamp precision to nanosecond level
- **FR-103.3:** Support efficient range queries by timestamp
- **FR-103.4:** Implement data validation checks on write
- **FR-103.5:** Support incremental data appending

**Acceptance Criteria:**
- Data retrieval latency <100ms for 1-hour dataset
- No data corruption after system restart
- Successfully load data into Pandas DataFrame for analysis

### 3.2 Embedding Model Module

#### FR-201: Model Architecture
**Priority:** Critical  
**Description:** Implement deep learning model for market state embedding

**Requirements:**
- **FR-201.1:** Implement multi-branch fusion architecture:
  - Branch A: LOB Encoder (CNN/ResNet for spatial features)
  - Branch B: Trade Flow Encoder (MLP for dynamics)
  - Fusion Layer: Cross-Attention mechanism
  - Temporal Encoder: Transformer or TCN
- **FR-201.2:** Accept input feature vectors of 50-60 dimensions
- **FR-201.3:** Output dense embeddings of 64 or 128 dimensions
- **FR-201.4:** Support batch inference for backtesting
- **FR-201.5:** Support single-sample inference for live trading

**Acceptance Criteria:**
- Model successfully trains on 1 week of continuous data
- Embedding dimension is configurable (64/128)
- Model can be exported to ONNX format

#### FR-202: Multi-task Training Objectives
**Priority:** Critical  
**Description:** Train model with multiple complementary objectives

**Requirements:**
- **FR-202.1:** Primary task: Masked feature reconstruction (15% random masking)
- **FR-202.2:** Secondary task: Contrastive learning (InfoNCE loss)
- **FR-202.3:** Auxiliary task: 10-second price direction prediction
- **FR-202.4:** Auxiliary task: Future volatility regression
- **FR-202.5:** Combined loss: α×Reconstruction + β×Contrastive + γ×Direction

**Acceptance Criteria:**
- Reconstruction MSE <0.01 (normalized)
- Direction prediction accuracy >55%
- Embedding space visualization shows clear market regime separation
- Silhouette score >0.4 for cluster quality

#### FR-203: Model Performance Optimization
**Priority:** High  
**Description:** Ensure model meets production latency requirements

**Requirements:**
- **FR-203.1:** Inference latency <20ms per prediction (99th percentile)
- **FR-203.2:** Support ONNX export for production deployment
- **FR-203.3:** ONNX model output must match PyTorch model output
- **FR-203.4:** Support both CPU and GPU inference via onnxruntime

**Acceptance Criteria:**
- Benchmark shows <20ms latency on production hardware
- Numerical difference between ONNX and PyTorch <1e-5
- Model loads successfully in onnxruntime

### 3.3 Trading Strategy Module

#### FR-301: Signal Generation
**Priority:** Critical  
**Description:** Generate trading signals from embedding vectors

**Requirements:**
- **FR-301.1:** Load ONNX embedding model on strategy initialization
- **FR-301.2:** Extract signal strength from embedding vectors
- **FR-301.3:** Predict price direction (UP/DOWN/NEUTRAL)
- **FR-301.4:** Calculate confidence score for each prediction
- **FR-301.5:** Filter signals below minimum confidence threshold

**Acceptance Criteria:**
- Signal generation latency <5ms
- Signals are generated only when sufficient confidence exists
- No signals generated when model confidence is below threshold

#### FR-302: Order Execution
**Priority:** Critical  
**Description:** Execute trades based on generated signals

**Requirements:**
- **FR-302.1:** Support limit orders only (no market orders)
- **FR-302.2:** Estimate fill probability based on LOB depth and queue position
- **FR-302.3:** Model realistic slippage for order sizing
- **FR-302.4:** Implement pre-trade risk checks:
  - Maximum position size validation
  - Maximum order size validation
  - Daily loss limit check
  - Fill probability threshold check
- **FR-302.5:** Auto-cancel orders if slippage exceeds threshold
- **FR-302.6:** Handle partial fills correctly

**Acceptance Criteria:**
- Fill probability estimation accuracy >80%
- Pre-trade risk checks prevent >95% of rule violations
- Orders are auto-cancelled when slippage threshold exceeded
- Partial fills are correctly tracked and accounted

#### FR-303: Risk Management
**Priority:** Critical  
**Description:** Implement comprehensive risk controls

**Requirements:**
- **FR-303.1:** Enforce maximum position size per instrument
- **FR-303.2:** Enforce maximum daily loss threshold (auto-shutdown)
- **FR-303.3:** Implement second-level stop-loss logic
- **FR-303.4:** Monitor heartbeat and restart if no data for >10 seconds
- **FR-303.5:** Log all risk events with severity levels

**Acceptance Criteria:**
- System auto-shuts down when daily loss exceeds threshold
- Stop-loss orders execute within 1 second of threshold breach
- System auto-restarts after heartbeat timeout
- All risk events are logged with timestamp and context

#### FR-304: Exchange Integration
**Priority:** Critical  
**Description:** Integrate with Lighter.xyz and Binance exchanges

**Requirements:**
- **FR-304.1:** Implement Lighter.xyz ExecutionClient adapter
- **FR-304.2:** Support Lighter.xyz order lifecycle:
  - Submit order
  - Cancel order
  - Modify order
  - Query order status
- **FR-304.3:** Handle WebSocket authentication and session management
- **FR-304.4:** Subscribe to order update events
- **FR-304.5:** Handle partial fill notifications
- **FR-304.6:** Support Binance API for data validation

**Acceptance Criteria:**
- Successfully submit orders to Lighter testnet
- Receive order fill notifications within 500ms
- Handle WebSocket reconnection without data loss
- Order state is always synchronized with exchange

### 3.4 Backtesting Module

#### FR-401: Historical Simulation
**Priority:** High  
**Description:** Simulate trading strategy on historical data

**Requirements:**
- **FR-401.1:** Load historical data from Parquet catalog
- **FR-401.2:** Replay market events in chronological order
- **FR-401.3:** Simulate order matching with realistic fill model:
  - Model queue position
  - Model partial fills based on LOB depth
  - Model slippage based on order size vs available depth
- **FR-401.4:** Apply zero fees for Lighter.xyz simulation
- **FR-401.5:** Track all performance metrics in real-time

**Acceptance Criteria:**
- Backtest completes 1 week of data in <5 minutes
- Fill simulation matches >90% of actual testnet fills
- Slippage model predicts actual slippage within 20%

#### FR-402: Performance Analytics
**Priority:** High  
**Description:** Generate comprehensive performance reports

**Requirements:**
- **FR-402.1:** Calculate total return
- **FR-402.2:** Calculate Sharpe ratio (target >1.0)
- **FR-402.3:** Calculate maximum drawdown
- **FR-402.4:** Calculate win rate
- **FR-402.5:** Calculate average slippage per trade
- **FR-402.6:** Calculate fill rate
- **FR-402.7:** Generate equity curve visualization
- **FR-402.8:** Compare strategy vs buy-and-hold benchmark

**Acceptance Criteria:**
- All metrics calculated correctly
- Report generated within 10 seconds of backtest completion
- Visualizations are clear and informative

### 3.5 Monitoring and Observability

#### FR-501: Real-time Monitoring
**Priority:** High  
**Description:** Monitor system health and performance in production

**Requirements:**
- **FR-501.1:** Track current PnL in real-time
- **FR-501.2:** Track current position in real-time
- **FR-501.3:** Track open orders
- **FR-501.4:** Monitor heartbeat (last data received timestamp)
- **FR-501.5:** Monitor data ingestion rate (events/second)
- **FR-501.6:** Monitor inference latency
- **FR-501.7:** Monitor order submission latency
- **FR-501.8:** Monitor memory and CPU usage

**Acceptance Criteria:**
- Dashboard updates every second
- All metrics visible on single screen
- Historical data retained for 7 days

#### FR-502: Alerting System
**Priority:** High  
**Description:** Alert operators of critical events

**Requirements:**
- **FR-502.1:** Critical alerts (SMS/PagerDuty):
  - Daily loss exceeds threshold
  - No data received for >10 seconds
  - System error/exception
- **FR-502.2:** Warning alerts (Slack):
  - Fill rate drops below 50%
  - Slippage exceeds 2× expected
  - Inference latency >30ms

**Acceptance Criteria:**
- Critical alerts delivered within 10 seconds
- Warning alerts delivered within 60 seconds
- No false positive alerts for 48-hour test period

---

## 4. Non-Functional Requirements

### 4.1 Performance Requirements

#### NFR-101: Latency
- **NFR-101.1:** Data-to-decision latency <50ms (95th percentile)
- **NFR-101.2:** Model inference latency <20ms (99th percentile)
- **NFR-101.3:** Order submission latency <100ms (95th percentile)
- **NFR-101.4:** WebSocket message processing <10ms

#### NFR-102: Throughput
- **NFR-102.1:** Handle ≥1000 order book updates per second
- **NFR-102.2:** Handle ≥500 trade tick events per second
- **NFR-102.3:** Process ≥100 signals per second during backtest

#### NFR-103: Resource Utilization
- **NFR-103.1:** Maximum memory usage <8GB during live trading
- **NFR-103.2:** Maximum CPU usage <50% on 4-core system
- **NFR-103.3:** Disk I/O <100MB/s sustained

### 4.2 Reliability Requirements

#### NFR-201: Availability
- **NFR-201.1:** System uptime >99% during trading hours
- **NFR-201.2:** Auto-restart capability after crashes
- **NFR-201.3:** Graceful shutdown on termination signals

#### NFR-202: Data Integrity
- **NFR-202.1:** Zero data loss during normal operations
- **NFR-202.2:** Checksums for all persisted data
- **NFR-202.3:** Atomic writes to prevent partial data corruption

#### NFR-203: Fault Tolerance
- **NFR-203.1:** Automatic WebSocket reconnection with exponential backoff
- **NFR-203.2:** Graceful degradation when exchange API is slow
- **NFR-203.3:** Continue operation with stale data for up to 10 seconds

### 4.3 Maintainability Requirements

#### NFR-301: Code Quality
- **NFR-301.1:** All modules have unit test coverage >80%
- **NFR-301.2:** All critical paths have integration tests
- **NFR-301.3:** Code follows PEP 8 style guidelines
- **NFR-301.4:** All public APIs have docstrings

#### NFR-302: Documentation
- **NFR-302.1:** Architecture documented in Markdown
- **NFR-302.2:** API documentation generated from code
- **NFR-302.3:** Deployment runbook maintained
- **NFR-302.4:** Troubleshooting guide maintained

#### NFR-303: Modularity
- **NFR-303.1:** Components are loosely coupled
- **NFR-303.2:** Each module has single responsibility
- **NFR-303.3:** Easy to swap ML models without changing strategy code
- **NFR-303.4:** Easy to add new exchange adapters

### 4.4 Security Requirements

#### NFR-401: API Key Management
- **NFR-401.1:** API keys stored in environment variables or secure vault
- **NFR-401.2:** API keys never logged or displayed
- **NFR-401.3:** API keys encrypted at rest

#### NFR-402: Data Privacy
- **NFR-402.1:** No sensitive data in logs
- **NFR-402.2:** Secure transmission of all exchange communications (TLS)

### 4.5 Scalability Requirements

#### NFR-501: Horizontal Scalability
- **NFR-501.1:** Support multiple instruments with single instance
- **NFR-501.2:** Support adding new instruments without restart

#### NFR-502: Data Scalability
- **NFR-502.1:** Efficiently store 30 days of historical data
- **NFR-502.2:** Query performance remains constant as data grows

---

## 5. Technical Constraints

### 5.1 Framework Constraints
- **TC-001:** Must use NautilusTrader as core trading framework
- **TC-002:** Must use NautilusTrader's event-driven architecture
- **TC-003:** Must use NautilusTrader's ParquetDataCatalog for storage

### 5.2 Data Constraints
- **TC-011:** Must NOT use OHLCV data as primary input (ex-post aggregated data prohibited)
- **TC-012:** Must use L2 Order Book + Tick-by-Tick trades only
- **TC-013:** Must prevent look-ahead bias in all feature calculations
- **TC-014:** Must align OrderBook and TradeTick events within same logical second

### 5.3 Model Constraints
- **TC-021:** Model must be exportable to ONNX format
- **TC-022:** Model must support CPU inference (GPU optional)
- **TC-023:** Model input dimension approximately 50-60 features
- **TC-024:** Model output dimension 64 or 128 embeddings

### 5.4 Execution Constraints
- **TC-031:** Must use limit orders only (no market orders)
- **TC-032:** Must model realistic slippage and fill probability
- **TC-033:** Must NOT assume "price touched = order filled"
- **TC-034:** Must model queue position at each price level

### 5.5 Deployment Constraints
- **TC-041:** Primary deployment platform: Lighter.xyz
- **TC-042:** Data validation platform: Binance
- **TC-043:** Operating capital per trade: $500-$5,000
- **TC-044:** Must operate on Linux, Windows, and macOS

---

## 6. Data Requirements

### 6.1 Input Data

#### Level 2 Order Book (LOB)
- **Depth:** Top 10 levels (Bid & Ask)
- **Update Frequency:** 1000ms snapshots
- **Required Fields:**
  - Price (float64)
  - Volume (float64)
  - Side (Bid/Ask)
  - Timestamp (nanosecond precision)

#### Tick-by-Tick Trades
- **Granularity:** All individual trades
- **Required Fields:**
  - Price (float64)
  - Volume (float64)
  - Side (Buy/Sell)
  - Timestamp (nanosecond precision)
  - Trade ID (string)

### 6.2 Derived Features (per second)
- **VWAP** (Volume Weighted Average Price)
- **Trade Count** (integer)
- **Aggressor Ratio** (Buy Volume / Total Volume)
- **OFI** (Order Flow Imbalance): Δ(Bid Vol) - Δ(Ask Vol)
- **LOB Imbalance** (Σ Bid Vol / Σ Ask Vol)
- **Spread** (Ask1 - Bid1)
- **Mid Price** ((Bid1 + Ask1) / 2)
- **Last Price** (most recent trade price)

### 6.3 Data Quality Requirements
- **Completeness:** >99% (missing <36 seconds per hour)
- **Accuracy:** VWAP within 0.01% of official exchange data
- **Timeliness:** Events processed within 50ms of occurrence
- **Consistency:** No timestamp gaps >2 seconds

---

## 7. Interface Requirements

### 7.1 Exchange APIs

#### Binance (Data Validation)
- **WebSocket:** wss://stream.binance.com:9443/ws
- **REST:** https://api.binance.com/api/v3
- **Endpoints:**
  - Order Book Depth
  - Recent Trades
  - Kline/Candlestick Data (for validation only)

#### Lighter.xyz (Production)
- **WebSocket:** TBD (to be specified by Lighter.xyz documentation)
- **REST:** TBD
- **Endpoints:**
  - Submit Order
  - Cancel Order
  - Modify Order
  - Query Order Status
  - Order Book Stream
  - Trade Stream

### 7.2 Model Interfaces

#### Training Interface (PyTorch)
```python
model = LuminautEmbedder(input_dim=50, embed_dim=128)
embeddings = model(features)  # (batch, 128)
```

#### Inference Interface (ONNX)
```python
session = ort.InferenceSession("model.onnx")
output = session.run(None, {'input': features.numpy()})
embeddings = output[0]  # (1, 128)
```

### 7.3 Data Storage Interface

#### Write Interface
```python
catalog.write_data(
    data_cls=FeatureVector,
    instrument_id=instrument_id,
    data=features
)
```

#### Read Interface
```python
data = catalog.read_data(
    data_cls=FeatureVector,
    instrument_id=instrument_id,
    start=start_timestamp,
    end=end_timestamp
)
```

---

## 8. Testing Requirements

### 8.1 Unit Testing
- **UT-001:** All feature calculation functions have unit tests
- **UT-002:** All model components have unit tests
- **UT-003:** All risk check functions have unit tests
- **UT-004:** Test coverage >80% for all modules

### 8.2 Integration Testing
- **IT-001:** End-to-end data collection test (5 minutes)
- **IT-002:** End-to-end embedding inference pipeline test
- **IT-003:** Backtest execution test (1 week of data)
- **IT-004:** Exchange adapter connectivity test

### 8.3 Performance Testing
- **PT-001:** Inference latency benchmark (<20ms requirement)
- **PT-002:** Data ingestion throughput test (>1000 updates/sec)
- **PT-003:** Backtest speed benchmark (1 week in <5 minutes)

### 8.4 Validation Testing
- **VT-001:** VWAP accuracy validation (<0.01% error)
- **VT-002:** OFI correlation validation (visual inspection)
- **VT-003:** ONNX model equivalence validation (<1e-5 difference)
- **VT-004:** Fill simulation validation (>90% match with testnet)

---

## 9. Deployment Requirements

### 9.1 Phase 1: Data Collection (Week 1-2)
- Deploy data collection script on cloud instance
- Run continuously for 1 hour minimum
- Generate validation report
- Sign-off required before Phase 2

### 9.2 Phase 2: Embedding Research (Week 3-5)
- Train model on Jupyter Notebook or Google Colab
- Track experiments in Weights & Biases
- Export best model to ONNX
- Validate inference latency <20ms
- Sign-off required before Phase 3

### 9.3 Phase 3: Trading Deployment (Week 6-8)

#### Stage 3.1: Backtest
- Run backtest with realistic slippage
- Achieve Sharpe ratio >1.0
- Sign-off required before testnet

#### Stage 3.2: Shadow Trading (Testnet)
- Deploy on Lighter testnet
- Run without submitting real orders
- Monitor fill probability predictions
- Run for 24 hours minimum
- Sign-off required before live

#### Stage 3.3: Live Deployment (Small Scale)
- Deploy with $100-200 capital
- Monitor continuously for 48 hours
- Verify all metrics within acceptable ranges
- Scale up gradually after success

---

## 10. Risks and Mitigations

### 10.1 Technical Risks

| Risk ID | Risk Description | Probability | Impact | Mitigation |
|---------|------------------|-------------|--------|------------|
| TR-001 | Look-ahead bias in features | Medium | Critical | Strict timestamp validation in unit tests |
| TR-002 | Model overfitting to training period | High | High | Walk-forward validation on multiple regimes |
| TR-003 | Inference latency exceeds 20ms | Medium | High | Early performance benchmarking, ONNX optimization |
| TR-004 | WebSocket disconnections | Medium | Medium | Auto-reconnection with exponential backoff |
| TR-005 | Data loss during system crash | Low | High | Atomic writes, checksums, regular snapshots |

### 10.2 Market Risks

| Risk ID | Risk Description | Probability | Impact | Mitigation |
|---------|------------------|-------------|--------|------------|
| MR-001 | Lighter.xyz low liquidity | High | High | Start with small orders, monitor slippage |
| MR-002 | Slippage exceeds predictions | Medium | Medium | Conservative slippage model, auto-cancel threshold |
| MR-003 | Fill rate below 70% | Medium | Medium | Fill probability model, order sizing optimization |
| MR-004 | Strategy stops working (regime change) | Low | Critical | Regular model retraining, manual monitoring |

### 10.3 Operational Risks

| Risk ID | Risk Description | Probability | Impact | Mitigation |
|---------|------------------|-------------|--------|------------|
| OR-001 | System crash during trading hours | Low | High | Auto-restart, comprehensive monitoring |
| OR-002 | API rate limiting | Medium | Medium | Implement rate limiting, use WebSocket primarily |
| OR-003 | Incorrect order submission | Low | Critical | Pre-trade validation, shadow trading phase |

---

## 11. Acceptance Criteria

### 11.1 Phase 1 Acceptance
- ✓ 1 hour continuous collection without errors
- ✓ VWAP within 0.01% of official close price
- ✓ OFI peaks correlate with price jumps (visual inspection)
- ✓ Data completeness >99%
- ✓ All unit tests passing

### 11.2 Phase 2 Acceptance
- ✓ Reconstruction MSE <0.01 (normalized)
- ✓ Silhouette score >0.4 (cluster quality)
- ✓ Direction prediction accuracy >55%
- ✓ Inference latency <20ms (99th percentile)
- ✓ ONNX export successful and equivalent
- ✓ Model training documented in W&B

### 11.3 Phase 3 Acceptance
- ✓ Backtest Sharpe ratio >1.0
- ✓ Backtest with slippage shows positive returns
- ✓ Testnet shadow trading: fill rate >70%
- ✓ Live trading: 48 hours without crash
- ✓ Live slippage within 20% of predicted
- ✓ All integration tests passing

### 11.4 Overall Project Acceptance
- ✓ Embedding model demonstrably captures market state
- ✓ Strategy has positive expectancy after costs
- ✓ System is production-ready (stable, monitored, safe)
- ✓ All documentation complete
- ✓ Code passes all quality checks

---

## 12. Dependencies

### 12.1 External Dependencies
- **NautilusTrader** (≥1.200.0): Core trading framework
- **PyTorch** (≥2.0): Model development
- **ONNX** (≥1.14) + **onnxruntime** (≥1.16): Production inference
- **Pandas** (≥2.0): Data manipulation
- **Plotly** (≥5.0): Visualization
- **Weights & Biases** (wandb): Experiment tracking

### 12.2 Exchange Dependencies
- **Binance API**: Available and stable for data collection
- **Lighter.xyz API**: Documentation available, testnet accessible

### 12.3 Infrastructure Dependencies
- **Compute**: Linux/Windows/macOS system with ≥4 cores, ≥8GB RAM
- **Storage**: ≥100GB SSD for data catalog
- **Network**: Stable internet connection with <100ms latency to exchanges

---

## 13. Glossary

| Term | Definition |
|------|------------|
| **LOB** | Level 2 Order Book - market depth showing top N price levels with volumes |
| **OFI** | Order Flow Imbalance - difference between bid and ask volume changes |
| **VWAP** | Volume Weighted Average Price - average price weighted by volume |
| **Embedding** | Low-dimensional dense vector representation of market state |
| **Slippage** | Difference between expected and actual execution price |
| **Fill Probability** | Estimated likelihood that a limit order will execute |
| **Sharpe Ratio** | Risk-adjusted return metric (excess return / volatility) |
| **ONNX** | Open Neural Network Exchange - cross-platform ML model format |
| **Look-ahead Bias** | Using future information in past decisions (data leakage) |

---

## 14. References

1. NautilusTrader Documentation: https://nautilustrader.io/
2. Lighter.xyz Documentation: https://lighter.xyz/docs
3. Binance API Documentation: https://binance-docs.github.io/
4. ONNX Runtime Documentation: https://onnxruntime.ai/
5. Order Flow Imbalance Research: Academic papers on market microstructure

---

**Document Control:**
- **Version:** 1.0
- **Status:** Approved
- **Next Review:** After Phase 1 completion
- **Change History:**
  - 2026-01-03: Initial version created

