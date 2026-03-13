# Luminaut Data Viewer 设计文档

**版本:** 1.0  
**日期:** 2026-01-03  
**状态:** 已实现

## 1. 概述

### 1.1 目标
创建一个TradingView风格的数据查看器，用于：
- 验证采集数据的准确性
- 检测数据异常
- 回放历史市场状态
- 实时监控数据流

### 1.2 技术选型
- **K线图引擎:** lightweight-charts-python
- **后端语言:** Python 3.10+
- **数据格式:** CSV / Parquet
- **依赖:** minimal (lightweight-charts, pandas, websockets)

## 2. 架构设计

### 目录结构
```
luminaut/
├── viewer/
│   ├── app.py               # 主应用 (含GUI逻辑)
│   ├── data/
│   │   ├── data_loader.py   # 历史数据加载
│   │   └── live_stream.py   # 实时WebSocket流
│   └── components/          # (已合并入app.py简化架构)
```

### 核心功能

1.  **历史模式**:
    - 加载 CSV 交易数据
    - 重采样为 K 线 (1m, 5m 等)
    - 完整图表显示

## 4. UI 布局与组件规范 (UI Layout Specification)

本查看器旨在模拟 **TradingView** 的标准布局，以符合交易员的使用习惯。

### 4.1 整体布局 (Grid Layout)
界面划分为三个主要区域：
1.  **Header (顶部导航栏)**: 显示当前交易对、最新价格、24h涨跌幅。
2.  **Main Chart (主图表区)**: 占据屏幕左侧 75% 宽度，显示 K 线与指标。
3.  **Side Panel (右侧信息栏)**: 占据屏幕右侧 25% 宽度，垂直排列深度与成交。

### 4.2 组件详情

#### A. 主图表 (Main Chart)
- **位置**: 左侧主区域
- **内容**:
    - **Candlestick Series**: 1m/5m K线。
    - **Volume Series**: 底部显示的成交量柱状图。
    - **Overlays**: VWAP 线、均线 (MA)。
- **交互**: 鼠标滚轮缩放，拖拽平移，十字光标 (Luminaut Crosshair)。

#### B. 订单簿面板 (Order Book Panel)
- **位置**: 右侧栏上半部分 (Top-Right)
- **显示模式**:
    - **Depth Graph**: 红绿面积图，直观展示多空堆积。
    - **Bid/Ask Table**: 列表显示前 10 档买卖单价格与数量。
- **视觉**: 买单绿色 (#00C853)，卖单红色 (#FF3D00)。

#### C. 实时成交列表 (Market Trades)
- **位置**: 右侧栏下半部分 (Bottom-Right)
- **显示内容**: 滚动的实时成交明细。
- **列表项**: `Time | Price | Amount`。
- **高亮**: 大单 (Whale Trades) 使用加粗字体或特殊背景色高亮。

## 5. 现阶段实现策略 (Implementation Strategy)
鉴于 `lightweight-charts-python` 的限制，Phase 1 采用如下过渡方案，逐步逼近上述目标布局：
1.  **Step 1 (Current)**:
    - Main Chart: 完整实现。
    - Order Book: 简化显示在 Window Title。
    - Trades: 简化显示在 Console。
2.  **Step 2 (Next)**:
    - 使用 `Subplot` 或多窗口模式，尝试将 Order Book 可视化为独立的 Bar Chart。
3.  **Step 3 (Target)**:
    - 集成 PyQt 或 Webview，实现完整的 HTML/CSS 侧边栏布局。

