#!/usr/bin/env python3
"""
简化版 UI 管理器
避免复杂的 JavaScript 注入
"""

class SimpleUIManager:
    """简化的 UI 管理器"""
    
    def __init__(self, chart):
        self.chart = chart
        self.layout_initialized = False
        print("🎨 简化 UI 管理器初始化")
    
    def create_simple_layout(self):
        """创建简单的布局"""
        if self.layout_initialized:
            return
        
        try:
            # 使用最简单的脚本注入
            simple_script = """
            console.log('Simple UI initialized');
            window.updatePrice = function(price, change) {
                console.log('Price update:', price, change);
            };
            """
            
            self.chart.run_script(simple_script)
            self.layout_initialized = True
            print("✅ 简单 UI 布局创建成功")
            
        except Exception as e:
            print(f"⚠️ UI 布局创建失败: {e}")
            # 不抛出异常，继续运行
    
    def update_price(self, price, change_percent=0):
        """更新价格显示"""
        if not self.layout_initialized:
            return
        
        try:
            # 简单的价格更新
            print(f"💰 价格更新: {price} ({change_percent:+.2f}%)")
        except Exception as e:
            print(f"⚠️ 价格更新失败: {e}")
    
    def update_orderbook(self, bids, asks):
        """更新订单簿"""
        try:
            if bids and asks:
                best_bid = bids[0][0] if bids else 0
                best_ask = asks[0][0] if asks else 0
                spread = best_ask - best_bid if best_ask > best_bid else 0
                print(f"📊 订单簿更新: 买一={best_bid}, 卖一={best_ask}, 价差={spread}")
        except Exception as e:
            print(f"⚠️ 订单簿更新失败: {e}")
    
    def add_trade(self, time, price, qty, side):
        """添加成交记录"""
        try:
            print(f"🔄 成交: {side.upper()} {price} x {qty}")
        except Exception as e:
            print(f"⚠️ 成交记录添加失败: {e}")
