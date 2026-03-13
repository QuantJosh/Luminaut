# Luminaut Implementation Plan

**Version:** 1.0  
**Date:** 2026-01-03  
**Timeline:** 8 weeks

---

## Phase 1: Data Collection & Validation (Week 1-2)

### Week 1: Core Infrastructure

**Day 1-2: Environment Setup**
- [ ] Clone NautilusTrader to `.nautilus_source/`
- [ ] Create project directory structure
- [ ] Install dependencies (`nautilus_trader`, `pandas`, `plotly`, etc.)
- [ ] Configure Python environment (venv/conda)
- [ ] Set up Git repository

**Day 3-5: LuminautFeatureBuilder Implementation**
- [ ] Create `luminaut/phase1_data_collection/actors/feature_builder.py`
- [ ] Implement `LuminautFeatureBuilder` class inheriting from `Actor`
- [ ] Implement `on_order_book_snapshots()` method
- [ ] Implement `on_trade_tick()` method
- [ ] Implement `on_timer_1s()` aggregation logic
- [ ] Implement feature calculations:
  - VWAP
  - OFI
  - LOB imbalance
  - Spread
  - Aggressor ratio

**Day 6-7: Data Collection Runner**
- [ ] Create `scripts/run_phase1_collection.py`
- [ ] Configure Binance WebSocket connection
- [ ] Implement graceful shutdown
- [ ] Test 5-minute collection run
- [ ] Test 1-hour collection run

### Week 2: Validation & Quality Assurance

**Day 8-10: Data Validation**
- [ ] Create `luminaut/phase1_data_collection/validators/data_quality_check.py`
- [ ] Implement VWAP vs K-line comparison (Plotly chart)
- [ ] Implement OFI correlation analysis
- [ ] Implement timestamp gap histogram
- [ ] Implement data completeness report
- [ ] Generate validation report HTML

**Day 11-12: Unit Testing**
- [ ] Create `tests/test_feature_builder.py`
- [ ] Test OFI calculation correctness
- [ ] Test VWAP calculation accuracy
- [ ] Test timestamp alignment (no look-ahead bias)
- [ ] Achieve >80% code coverage

**Day 13-14: Documentation & Sign-off**
- [ ] Document Phase 1 architecture
- [ ] Document data quality findings
- [ ] Create sample validation report
- [ ] **Phase 1 Sign-off Review**

---

## Phase 2: Embedding Model Research (Week 3-5)

### Week 3: Feature Engineering

**Day 15-17: Data Analysis**
- [ ] Create `luminaut/phase2_embedding_research/notebooks/01_feature_engineering.ipynb`
- [ ] Load Phase 1 data from Parquet
- [ ] Exploratory data analysis (distributions, correlations)
- [ ] Feature importance analysis
- [ ] Test different feature combinations

**Day 18-19: Baseline Model**
- [ ] Implement simple autoencoder (baseline)
- [ ] Train on baseline features (VWAP, Volume, Spread)
- [ ] Measure reconstruction loss
- [ ] Visualize embedding space (t-SNE)

**Day 20-21: Enhanced Features**
- [ ] Add OFI and LOB imbalance features
- [ ] Retrain model with enhanced features
- [ ] Compare vs baseline performance
- [ ] Log experiments to Weights & Biases

### Week 4: Model Development

**Day 22-24: Multi-Branch Architecture**
- [ ] Create `luminaut/phase2_embedding_research/models/embedder_v2.py`
- [ ] Implement LOB Encoder (CNN)
- [ ] Implement Trade Flow Encoder (MLP)
- [ ] Implement Cross-Attention Fusion
- [ ] Implement Transformer Temporal Encoder

**Day 25-26: Multi-Task Training**
- [ ] Implement masked reconstruction loss
- [ ] Implement contrastive learning (InfoNCE)
- [ ] Implement direction prediction head
- [ ] Implement combined loss function
- [ ] Configure training hyperparameters

**Day 27-28: Model Training**
- [ ] Train on 1 week of continuous data
- [ ] Monitor training metrics in W&B
- [ ] Implement early stopping
- [ ] Save best model checkpoint

### Week 5: Validation & Export

**Day 29-31: Model Validation**
- [ ] Create `luminaut/phase2_embedding_research/notebooks/03_embedding_validation.ipynb`
- [ ] Evaluate reconstruction quality (MSE <0.01)
- [ ] Evaluate clustering (Silhouette score >0.4)
- [ ] Evaluate direction prediction (accuracy >55%)
- [ ] Benchmark inference latency (<20ms)

**Day 32-33: ONNX Export**
- [ ] Create `scripts/export_model_to_onnx.py`
- [ ] Export PyTorch model to ONNX
- [ ] Verify ONNX numerical equivalence
- [ ] Benchmark ONNX inference speed
- [ ] Save to `luminaut/phase3_trading_deployment/models/production_embedder.onnx`

**Day 34-35: Documentation & Sign-off**
- [ ] Document model architecture
- [ ] Document training procedure
- [ ] Document validation results
- [ ] **Phase 2 Sign-off Review**

---

## Phase 3: Trading Strategy Deployment (Week 6-8)

### Week 6: Strategy Implementation

**Day 36-38: Strategy Core**
- [ ] Create `luminaut/phase3_trading_deployment/strategies/luminaut_strategy.py`
- [ ] Implement `LuminautStrategy` class
- [ ] Migrate feature builder logic from Phase 1
- [ ] Load ONNX model in `on_start()`
- [ ] Implement `on_data()` decision loop

**Day 39-40: Signal Generation**
- [ ] Implement embedding inference
- [ ] Implement signal strength extraction
- [ ] Implement direction prediction
- [ ] Implement confidence scoring
- [ ] Implement signal filtering

**Day 41-42: Risk Management**
- [ ] Implement pre-trade risk checks
- [ ] Implement position size limits
- [ ] Implement daily loss limits
- [ ] Implement stop-loss logic
- [ ] Implement heartbeat monitoring

### Week 7: Exchange Integration & Backtesting

**Day 43-45: Lighter.xyz Adapter**
- [ ] Create `luminaut/phase3_trading_deployment/adapters/lighter_adapter.py`
- [ ] Implement `LighterExecutionClient`
- [ ] Implement order submission
- [ ] Implement order cancellation
- [ ] Implement WebSocket order updates
- [ ] Test on Lighter testnet

**Day 46-47: Fill Probability Model**
- [ ] Implement queue position estimation
- [ ] Implement fill probability calculation
- [ ] Implement slippage estimation
- [ ] Validate against historical data

**Day 48-49: Backtesting**
- [ ] Create `scripts/run_phase3_backtest.py`
- [ ] Configure BacktestEngine
- [ ] Implement realistic fill model
- [ ] Run backtest on 1 week of data
- [ ] Generate performance report
- [ ] Target: Sharpe Ratio >1.0

### Week 8: Testing & Deployment

**Day 50-52: Shadow Trading (Testnet)**
- [ ] Create `scripts/run_phase3_shadow.py`
- [ ] Deploy on Lighter testnet
- [ ] Log intended orders (do NOT submit)
- [ ] Monitor actual market behavior
- [ ] Compare predicted vs actual fills
- [ ] Generate shadow trading report
- [ ] Target: Fill rate >70%

**Day 53-54: Live Deployment (Small Scale)**
- [ ] Create `scripts/run_phase3_live.py`
- [ ] Configure with $100-200 capital
- [ ] Implement real-time monitoring dashboard
- [ ] Implement alerting (critical/warning)
- [ ] Deploy to production server

**Day 55-56: 48-Hour Monitoring**
- [ ] Monitor continuously for 48 hours
- [ ] Track PnL, fill rate, slippage
- [ ] Verify no crashes or errors
- [ ] Compare live vs backtest performance
- [ ] **Phase 3 Sign-off Review**

---

## Deliverables Checklist

### Phase 1 Deliverables
- [x] `LuminautFeatureBuilder` actor implementation
- [x] 1-hour dataset in Parquet format
- [x] Data validation report (all checks passing)
- [x] Unit tests with >80% coverage
- [x] Phase 1 documentation

### Phase 2 Deliverables
- [ ] Trained embedding model (PyTorch checkpoint)
- [ ] ONNX production model (<20ms inference)
- [ ] Embedding validation report (all metrics passing)
- [ ] Feature engineering notebook
- [ ] Model training notebook
- [ ] Experiments logged in W&B
- [ ] Phase 2 documentation

### Phase 3 Deliverables
- [ ] `LuminautStrategy` implementation
- [ ] `LighterExecutionClient` adapter
- [ ] Backtest report (Sharpe >1.0)
- [ ] Shadow trading report (fill rate >70%)
- [ ] Live trading: 48-hour success
- [ ] Monitoring dashboard
- [ ] Integration tests
- [ ] Phase 3 documentation

### Final Deliverables
- [ ] Complete project documentation
- [ ] Deployment runbook
- [ ] Troubleshooting guide
- [ ] Performance benchmark report
- [ ] Final project presentation

---

## Risk Mitigation Plan

### Technical Risks

**Risk:** Look-ahead bias in features  
**Mitigation:** Unit tests for timestamp validation, code review

**Risk:** Model overfitting  
**Mitigation:** Walk-forward validation, multiple market regime testing

**Risk:** Latency exceeds 20ms  
**Mitigation:** Early benchmarking, ONNX optimization, profiling

**Risk:** WebSocket disconnections  
**Mitigation:** Auto-reconnection, buffer management, connection monitoring

### Market Risks

**Risk:** Low liquidity on Lighter.xyz  
**Mitigation:** Start with small orders, monitor slippage, adjust sizing

**Risk:** Slippage exceeds predictions  
**Mitigation:** Conservative slippage model, auto-cancel thresholds

**Risk:** Fill rate below 70%  
**Mitigation:** Fill probability modeling, order placement optimization

### Operational Risks

**Risk:** System crashes during trading  
**Mitigation:** Auto-restart, comprehensive monitoring, alerting

**Risk:** API rate limiting  
**Mitigation:** Rate limiting implementation, primarily use WebSocket

**Risk:** Incorrect order submission  
**Mitigation:** Pre-trade validation, shadow trading phase, small initial capital

---

## Success Criteria by Phase

### Phase 1 Success Criteria
✓ 1 hour continuous collection without errors  
✓ VWAP within 0.01% of official close  
✓ OFI peaks correlate with price jumps  
✓ Data completeness >99%  
✓ All unit tests passing  

### Phase 2 Success Criteria
✓ Reconstruction MSE <0.01  
✓ Silhouette score >0.4  
✓ Direction prediction >55%  
✓ Inference latency <20ms  
✓ ONNX export successful  

### Phase 3 Success Criteria
✓ Backtest Sharpe >1.0  
✓ Testnet fill rate >70%  
✓ Live: 48 hours without crash  
✓ Live slippage within 20% of predicted  

---

## Next Steps

**Immediate Actions:**
1. Set up development environment
2. Clone NautilusTrader repository
3. Create project structure
4. Begin Phase 1, Day 1 tasks

**First Milestone:** Complete Phase 1 in 2 weeks with all success criteria met.

---

**Document Status:** Ready for Execution  
**Last Updated:** 2026-01-03

