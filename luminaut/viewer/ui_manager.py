class UIManager:
    """管理 TradingView 风格的 UI 布局"""
    
    def __init__(self, chart):
        self.chart = chart
        self.layout_initialized = False
        
        # 性能优化：批量更新和节流
        self.update_queue = {
            'price': None,
            'orderbook': None,
            'trades': []
        }
        self.update_pending = False
        self.last_update_time = 0
        self.update_interval = 100  # 100ms 最小更新间隔
        
        # DOM 缓存
        self.dom_cache = {}
        
    def create_tradingview_layout(self):
        """创建完整的 TradingView 风格布局"""
        if self.layout_initialized:
            return
            
        # 注入 CSS 和 HTML 结构
        css = self._get_layout_css()
        html = self._get_layout_html()
        js = self._get_layout_js()
        
        # 执行初始化脚本
        init_script = f"""
        (function() {{
            // 注入 CSS
            const style = document.createElement('style');
            style.textContent = `{css}`;
            document.head.appendChild(style);
            
            // 创建布局容器
            const container = document.createElement('div');
            container.innerHTML = `{html}`;
            document.body.appendChild(container);
            
            // 初始化交互功能
            {js}
            
            console.log('TradingView layout initialized');
        }})();
        """
        
        try:
            self.chart.run_script(init_script)
            self.layout_initialized = True
            print("✅ TradingView layout initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize layout: {e}")
    
    def _get_layout_css(self):
        """获取布局 CSS 样式"""
        return """
        /* 重置和基础样式 */
        .luminaut-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #1e1e1e;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #d1d5db;
            z-index: 1000;
            pointer-events: none;
        }
        
        /* Header 样式 */
        .luminaut-header {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 40px;
            background: #131722;
            border-bottom: 1px solid #2a2e39;
            display: flex;
            align-items: center;
            padding: 0 16px;
            pointer-events: auto;
        }
        
        .luminaut-symbol {
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
            margin-right: 16px;
        }
        
        .luminaut-price {
            font-size: 18px;
            font-weight: 700;
            margin-right: 12px;
        }
        
        .luminaut-change {
            font-size: 14px;
            padding: 2px 8px;
            border-radius: 4px;
        }
        
        .luminaut-change.positive {
            background: #00c853;
            color: white;
        }
        
        .luminaut-change.negative {
            background: #ff5252;
            color: white;
        }
        
        /* 侧边栏样式 */
        .luminaut-sidebar {
            position: absolute;
            top: 40px;
            right: 0;
            width: 300px;
            height: calc(100% - 40px);
            background: #131722;
            border-left: 1px solid #2a2e39;
            display: flex;
            flex-direction: column;
            pointer-events: auto;
        }
        
        /* 订单簿面板 */
        .luminaut-orderbook {
            flex: 1;
            border-bottom: 1px solid #2a2e39;
            overflow: hidden;
        }
        
        .luminaut-panel-header {
            height: 32px;
            background: #1a1f2e;
            border-bottom: 1px solid #2a2e39;
            display: flex;
            align-items: center;
            padding: 0 12px;
            font-size: 12px;
            font-weight: 600;
            color: #9ca3af;
        }
        
        .luminaut-orderbook-content {
            height: calc(100% - 32px);
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 11px;
        }
        
        .luminaut-orderbook-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .luminaut-orderbook-table td {
            padding: 2px 8px;
            text-align: right;
            border-bottom: 1px solid #2a2e3910;
        }
        
        .luminaut-orderbook-table td:first-child {
            text-align: left;
        }
        
        .luminaut-bid {
            color: #00e676;
        }
        
        .luminaut-ask {
            color: #ff5252;
        }
        
        /* 成交明细面板 */
        .luminaut-trades {
            flex: 1;
            overflow: hidden;
        }
        
        .luminaut-trades-content {
            height: calc(100% - 32px);
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 11px;
        }
        
        .luminaut-trade-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 2px 8px;
            border-bottom: 1px solid #2a2e3910;
            margin-bottom: 1px;
        }
        
        .luminaut-trade-time {
            color: #6b7280;
            font-size: 10px;
        }
        
        .luminaut-trade-price {
            flex: 1;
            text-align: center;
        }
        
        .luminaut-trade-qty {
            text-align: right;
            color: #9ca3af;
        }
        
        .luminaut-trade-buy {
            background: rgba(0, 230, 118, 0.1);
        }
        
        .luminaut-trade-sell {
            background: rgba(255, 82, 82, 0.1);
        }
        
        /* 滚动条样式 */
        ::-webkit-scrollbar {
            width: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a1f2e;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #4b5563;
            border-radius: 3px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #6b7280;
        }
        """
    
    def _get_layout_html(self):
        """获取布局 HTML 结构"""
        return """
        <div class="luminaut-container">
            <!-- Header -->
            <div class="luminaut-header">
                <div class="luminaut-symbol">BTC/USDT</div>
                <div class="luminaut-price" id="current-price">0.00</div>
                <div class="luminaut-change" id="price-change">+0.00%</div>
            </div>
            
            <!-- Sidebar -->
            <div class="luminaut-sidebar">
                <!-- Order Book Panel -->
                <div class="luminaut-orderbook">
                    <div class="luminaut-panel-header">Order Book</div>
                    <div class="luminaut-orderbook-content">
                        <table class="luminaut-orderbook-table" id="orderbook-table">
                            <!-- 动态填充 -->
                        </table>
                    </div>
                </div>
                
                <!-- Trades Panel -->
                <div class="luminaut-trades">
                    <div class="luminaut-panel-header">Recent Trades</div>
                    <div class="luminaut-trades-content" id="trades-list">
                        <!-- 动态填充 -->
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _get_layout_js(self):
        """获取布局 JavaScript 功能"""
        return """
        // 初始化数据存储
        window.luminautData = {
            currentPrice: 0,
            priceChange: 0,
            orderBook: { bids: [], asks: [] },
            trades: []
        };
        
        // 更新价格显示
        window.updatePrice = function(price, change) {
            const priceEl = document.getElementById('current-price');
            const changeEl = document.getElementById('price-change');
            
            if (priceEl) {
                priceEl.textContent = price ? price.toFixed(2) : '0.00';
            }
            
            if (changeEl) {
                const changePercent = (change || 0);
                changeEl.textContent = (changePercent >= 0 ? '+' : '') + changePercent.toFixed(2) + '%';
                changeEl.className = 'luminaut-change ' + (changePercent >= 0 ? 'positive' : 'negative');
            }
        };
        
        // 更新订单簿
        window.updateOrderBook = function(bids, asks) {
            const table = document.getElementById('orderbook-table');
            if (!table) return;
            
            let html = '';
            
            // 显示前5档卖单
            for (let i = asks.length - 1; i >= Math.max(0, asks.length - 5); i--) {
                const [price, qty] = asks[i];
                html += `<tr>
                    <td class="luminaut-ask">${parseFloat(price).toFixed(2)}</td>
                    <td class="luminaut-ask">${parseFloat(qty).toFixed(4)}</td>
                </tr>`;
            }
            
            // 分隔线
            html += '<tr><td colspan="2" style="height: 4px;"></td></tr>';
            
            // 显示前5档买单
            for (let i = 0; i < Math.min(5, bids.length); i++) {
                const [price, qty] = bids[i];
                html += `<tr>
                    <td class="luminaut-bid">${parseFloat(price).toFixed(2)}</td>
                    <td class="luminaut-bid">${parseFloat(qty).toFixed(4)}</td>
                </tr>`;
            }
            
            table.innerHTML = html;
        };
        
        // 添加新的成交记录
        window.addTrade = function(time, price, qty, side) {
            const list = document.getElementById('trades-list');
            if (!list) return;
            
            const timeStr = new Date(time).toLocaleTimeString();
            const tradeClass = side === 'BUY' ? 'luminaut-trade-buy' : 'luminaut-trade-sell';
            const priceClass = side === 'BUY' ? 'luminaut-bid' : 'luminaut-ask';
            
            const tradeHtml = `
                <div class="luminaut-trade-item ${tradeClass}">
                    <span class="luminaut-trade-time">${timeStr}</span>
                    <span class="luminaut-trade-price ${priceClass}">${parseFloat(price).toFixed(2)}</span>
                    <span class="luminaut-trade-qty">${parseFloat(qty).toFixed(4)}</span>
                </div>
            `;
            
            list.insertAdjacentHTML('afterbegin', tradeHtml);
            
            // 保持最多50条记录
            while (list.children.length > 50) {
                list.removeChild(list.lastChild);
            }
        };
        
        console.log('Luminaut UI functions initialized');
        
        // 性能优化：批量更新函数
        window.batchUpdate = function(priceData, orderbookData, tradesData) {
            try {
                // 批量更新价格
                if (priceData) {
                    window.updatePrice(priceData.price, priceData.change);
                }
                
                // 批量更新订单簿
                if (orderbookData) {
                    const bidsStr = '[' + orderbookData.bids.map(p => `[${p[0]},${p[1]}]`).join(',') + ']';
                    const asksStr = '[' + orderbookData.asks.map(p => `[${p[0]},${p[1]}]`).join(',') + ']';
                    window.updateOrderBook(bidsStr, asksStr);
                }
                
                // 批量添加成交记录
                if (tradesData && tradesData.length > 0) {
                    tradesData.forEach(trade => {
                        window.addTrade(trade.time, trade.price, trade.qty, trade.side);
                    });
                }
            } catch(e) {
                console.error('Batch update error:', e);
            }
        };
        """
    
    def update_price(self, price, change_percent=0):
        """更新价格显示（批量更新）"""
        if not self.layout_initialized:
            return
        
        self.update_queue['price'] = {
            'price': price,
            'change': change_percent
        }
        self._schedule_update()
    
    def update_orderbook(self, bids, asks):
        """更新订单簿显示（批量更新）"""
        if not self.layout_initialized:
            return
        
        self.update_queue['orderbook'] = {
            'bids': bids[:10],
            'asks': asks[:10]
        }
        self._schedule_update()
    
    def add_trade(self, time, price, qty, side):
        """添加成交记录（批量更新）"""
        if not self.layout_initialized:
            return
        
        # 添加到队列，限制队列大小
        self.update_queue['trades'].append({
            'time': time,
            'price': price,
            'qty': qty,
            'side': side
        })
        
        # 保持队列大小合理
        if len(self.update_queue['trades']) > 20:
            self.update_queue['trades'] = self.update_queue['trades'][-20:]
        
        self._schedule_update()
    
    def _schedule_update(self):
        """安排批量更新（节流）"""
        import time
        current_time = time.time() * 1000  # 转换为毫秒
        
        if current_time - self.last_update_time < self.update_interval:
            if not self.update_pending:
                self.update_pending = True
                # 延迟执行
                import threading
                def delayed_update():
                    time.sleep(self.update_interval / 1000)
                    self._execute_batch_update()
                threading.Thread(target=delayed_update, daemon=True).start()
        else:
            self._execute_batch_update()
    
    def _execute_batch_update(self):
        """执行批量更新"""
        import time
        if not any(self.update_queue.values()):
            return
        
        try:
            # 准备批量更新数据
            price_data = self.update_queue.get('price')
            orderbook_data = self.update_queue.get('orderbook')
            trades_data = self.update_queue.get('trades', [])
            
            # 构建批量更新 JavaScript
            if price_data or orderbook_data or trades_data:
                # 安全地序列化数据
                price_js = f"price: {price_data['price']}, change: {price_data['change']}" if price_data else "null"
                
                if orderbook_data:
                    bids_str = '[' + ','.join([f"[{p},{q}]" for p, q in orderbook_data['bids']]) + ']'
                    asks_str = '[' + ','.join([f"[{p},{q}]" for p, q in orderbook_data['asks']]) + ']'
                    orderbook_js = f"bids: {bids_str}, asks: {asks_str}"
                else:
                    orderbook_js = "null"
                
                trades_js = '[' + ','.join([
                    f"{{time: {t['time']}, price: {t['price']}, qty: {t['qty']}, side: '{t['side']}'}}"
                    for t in trades_data
                ]) + ']' if trades_data else '[]'
                
                js = f"window.batchUpdate({{price: {{{price_js}}}, orderbook: {{{orderbook_js}}}, trades: {trades_js}}});"
                
                self.chart.run_script(js)
            
            # 清空队列
            self.update_queue = {
                'price': None,
                'orderbook': None,
                'trades': []
            }
            
            self.last_update_time = time.time() * 1000
            self.update_pending = False
            
        except Exception as e:
            print(f"Batch update error: {e}")
            self.update_pending = False
