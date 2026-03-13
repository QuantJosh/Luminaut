# Luminaut 数据获取完整策略

**更新时间:** 2026-01-03  
**当前状态:** Phase 1 实时数据采集成功，准备获取历史数据

---

## 📊 **数据需求分析**

### **Phase 2 (模型训练) 需要的数据**

| 数据类型 | 需求量 | 用途 | 获取方式 |
|---------|--------|------|---------|
| **历史交易数据** | ≥1周 | 模型训练 | Binance 历史下载 ✅ |
| **历史K线数据** | ≥1周 | VWAP验证 | Binance 历史下载 ✅ |
| **历史订单簿** | ≥1周 | 特征工程 | 需持续采集 ⚠️ |

### **Phase 3 (实时交易) 需要的数据**

| 数据类型 | 需求 | 获取方式 |
|---------|------|---------|
| **实时订单簿** | 1000ms更新 | 实时WebSocket ✅ |
| **实时交易** | tick-by-tick | 实时WebSocket ✅ |

---

## 🎯 **三步数据获取策略**

### **Step 1: 下载历史交易数据（立即执行）** ⭐

**目标:** 获取1周的历史tick-by-tick交易数据

**命令:**
```bash
# 下载最近7天的交易数据
python scripts/download_historical_data.py \
    --symbol BTCUSDT \
    --start-date 2025-12-27 \
    --end-date 2026-01-02 \
    --data-type trades \
    --merge
```

**预期结果:**
- 7个每日CSV文件
- 1个合并文件 `BTCUSDT_trades_merged.csv`
- 总大小: ~500MB - 1GB
- 记录数: ~2-5 百万笔交易

**用途:**
- ✅ 计算每秒VWAP
- ✅ 识别买卖方向
- ✅ 训练方向预测模型

**优点:**
- ✅ 免费
- ✅ 官方数据
- ✅ 完整覆盖

**缺点:**
- ❌ 无订单簿数据

---

### **Step 2: 持续采集订单簿数据（并行执行）** ⏳

**目标:** 开始积累实时订单簿快照

**命令:**
```bash
# 后台运行，持续采集（建议用screen或tmux）
nohup python scripts/test_binance_simple.py \
    --duration-minutes 10080 \  # 7天 = 10080分钟
    --symbol BTCUSDT \
    > logs/orderbook_collection.log 2>&1 &
```

**预期结果:**
- 每天 ~86,400 个订单簿快照
- 7天 ~600,000 个快照
- 总大小: ~200-300MB

**用途:**
- ✅ 计算OFI（Order Flow Imbalance）
- ✅ LOB imbalance
- ✅ 深度分析

**注意事项:**
- ⚠️ 需要保持系统运行
- ⚠️ 监控磁盘空间
- ⚠️ 定期检查日志

**替代方案:**
如果无法持续运行，可以：
- 每天采集1小时
- 分多次采集
- 或购买第三方历史订单簿数据

---

### **Step 3: 下载K线数据用于验证（可选）** ✅

**目标:** 获取1分钟K线用于VWAP验证

**命令:**
```bash
python scripts/download_historical_data.py \
    --symbol BTCUSDT \
    --start-date 2025-12-27 \
    --end-date 2026-01-02 \
    --data-type klines
```

**预期结果:**
- 7个每日CSV文件
- 每天 1,440 根K线（1分钟×24小时×60分钟）
- 总大小: ~10-20MB

**用途:**
- ✅ 验证VWAP计算准确性
- ✅ 对比我们的聚合结果

---

## 📅 **推荐执行时间表**

### **今天（2026-01-03）**

**下午（现在）:**
```bash
# 1. 下载历史交易数据（30分钟）
python scripts/download_historical_data.py \
    --symbol BTCUSDT \
    --start-date 2025-12-27 \
    --end-date 2026-01-02 \
    --data-type both \
    --merge

# 2. 验证下载的数据
python scripts/validate_downloaded_data.py
```

**晚上（如果可以保持电脑运行）:**
```bash
# 开始持续采集订单簿（后台运行）
nohup python scripts/test_binance_simple.py \
    --duration-minutes 1440 \
    --symbol BTCUSDT \
    > logs/overnight_collection.log 2>&1 &

# 查看进程
ps aux | grep test_binance_simple
```

### **本周（Week 2）**

**Day 2-3: 特征工程**
- 从历史数据计算特征
- 生成训练数据集
- 验证数据质量

**Day 4-5: 数据验证**
- VWAP准确性验证
- OFI相关性分析
- 生成验证报告

**Day 6-7: Phase 1 收尾**
- 单元测试
- 文档完善
- Phase 1 Sign-off

---

## 💾 **数据存储规划**

### **目录结构**
```
data/
├── historical/              # 历史数据
│   ├── BTCUSDT-trades-2025-12-27.csv
│   ├── BTCUSDT-trades-2025-12-28.csv
│   ├── ...
│   ├── BTCUSDT_trades_merged.csv  # 合并文件
│   └── BTCUSDT-1m-2025-12-27.csv  # K线
│
├── realtime/                # 实时采集
│   ├── binance_orderbook_btcusdt_20260103_122010.csv
│   ├── binance_trades_btcusdt_20260103_122010.csv
│   └── ...
│
├── processed/               # 处理后的特征
│   ├── features_20251227.parquet
│   ├── features_20251228.parquet
│   └── ...
│
└── catalog/                 # NautilusTrader catalog
    └── (Phase 3 使用)
```

### **存储需求估算**

| 数据类型 | 每天大小 | 7天大小 | 30天大小 |
|---------|----------|---------|----------|
| 历史Trades | 100-150MB | ~1GB | ~4GB |
| 历史Klines | 2-3MB | ~20MB | ~90MB |
| 实时LOB快照 | 40-50MB | ~300MB | ~1.5GB |
| 实时Trades | 150-200MB | ~1.2GB | ~5GB |
| **总计** | ~350MB | **~2.5GB** | **~10.5GB** |

**建议:** 确保至少有 **20GB** 可用空间

---

## 🔧 **历史数据处理流程**

### **1. 下载历史数据**
```bash
python scripts/download_historical_data.py \
    --symbol BTCUSDT \
    --start-date 2025-12-27 \
    --end-date 2026-01-02 \
    --data-type both \
    --merge
```

### **2. 特征提取**
```python
# scripts/process_historical_data.py (待创建)
# 从历史交易数据计算:
# - 每秒VWAP
# - 每秒买卖比例
# - 每秒交易量
# (注意：缺少历史LOB，OFI需从实时采集获得)
```

### **3. 数据验证**
```python
# scripts/validate_features.py (待创建)
# - VWAP vs K线对比
# - 数据完整性检查
# - 异常值检测
```

### **4. 保存为训练格式**
```python
# 保存为Parquet格式，便于快速加载
df.to_parquet('data/processed/features_20251227.parquet')
```

---

## ⚠️ **历史订单簿数据的挑战**

### **问题**
Binance **不提供** 免费的历史订单簿快照下载

### **解决方案**

**方案1: 持续采集（推荐）** ✅
- 从现在开始持续采集
- 7天后有完整数据
- 成本: 时间 + 电力

**方案2: 购买第三方数据** 💰
- [Kaiko](https://www.kaiko.com/)
- [CryptoCompare](https://www.cryptocompare.com/)
- [Tardis](https://tardis.dev/)
- 成本: $$$

**方案3: 仅用交易数据训练** ⚡
- 先用历史交易数据训练direction prediction
- 后续用实时采集的LOB数据训练完整模型
- 分阶段方法

**推荐:** 方案3（先部分训练）+ 方案1（持续采集）

---

## 🎯 **立即行动计划**

### **现在执行（5分钟）**

**1. 安装依赖:**
```bash
.venv\Scripts\activate
pip install tqdm requests  # 下载工具需要
```

**2. 下载最近7天数据:**
```bash
python scripts/download_historical_data.py \
    --symbol BTCUSDT \
    --start-date 2025-12-27 \
    --end-date 2026-01-02 \
    --data-type trades \
    --merge
```

**预计时间:** 20-30分钟（取决于网速）

**3. 验证下载:**
```bash
# 检查文件
ls data/historical/

# 查看合并文件统计
python -c "import pandas as pd; df=pd.read_csv('data/historical/BTCUSDT_trades_merged.csv'); print(f'总记录: {len(df):,}'); print(f'时间范围: {df.datetime.min()} 到 {df.datetime.max()}')"
```

---

### **今晚执行（如果可以）**

**启动持续采集:**
```bash
# 创建screen会话
screen -S luminaut_collection

# 运行采集（24小时）
python scripts/test_binance_simple.py --duration-minutes 1440

# 分离screen: Ctrl+A, D
# 重新连接: screen -r luminaut_collection
```

---

## 📊 **下一步工作（本周）**

### **Day 2-3: 特征工程脚本**
- [ ] 创建 `process_historical_data.py`
- [ ] 从历史交易计算特征
- [ ] 生成训练数据集

### **Day 4-5: 数据验证**
- [ ] 创建 `validate_features.py`
- [ ] VWAP准确性验证
- [ ] 生成验证报告

### **Day 6-7: 单元测试**
- [ ] 特征计算测试
- [ ] 数据完整性测试
- [ ] Phase 1 收尾

---

## 💡 **关键建议**

### **优先级1: 立即下载历史交易数据** ⭐
- 免费可用
- 足够训练基础模型
- 30分钟可完成

### **优先级2: 开始持续采集订单簿**
- 越早开始越好
- 积累数据需要时间
- 后台运行即可

### **优先级3: 特征工程脚本**
- 从历史数据提取特征
- 为Phase 2做准备

---

**准备好开始下载历史数据了吗？** 🚀

执行命令：
```bash
.venv\Scripts\activate
pip install tqdm requests
python scripts/download_historical_data.py --symbol BTCUSDT --start-date 2025-12-27 --end-date 2026-01-02 --data-type trades --merge
```
