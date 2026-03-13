import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

class ConfigManager:
    """配置管理和用户设置"""
    
    def __init__(self, config_file: str = "luminaut_config.json"):
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
        
        # 默认配置
        self.default_config = {
            # 应用程序设置
            "app": {
                "mode": "realtime",  # historical, realtime
                "symbol": "btcusdt",
                "timeframe": "1min",
                "theme": "dark",  # dark, light
                "language": "zh-CN"
            },
            
            # 图表设置
            "chart": {
                "width": 1400,
                "height": 800,
                "show_toolbar": True,
                "show_crosshair": True,
                "show_legend": True,
                "show_grid": True,
                "candlestick_style": "default",  # default, hollow, colored
                "volume_style": "bars"  # bars, line, area
            },
            
            # 数据源设置
            "data_source": {
                "exchange": "binance",  # binance, lighter
                "api_timeout": 10,
                "reconnect_attempts": 5,
                "reconnect_delay": 5,
                "heartbeat_interval": 30
            },
            
            # 技术指标设置
            "indicators": {
                "vwap": {
                    "enabled": True,
                    "window": None,  # None for cumulative
                    "color": "#FF6B6B"
                },
                "sma": {
                    "enabled": True,
                    "periods": [20, 50, 200],
                    "colors": ["#4ECDC4", "#45B7D1", "#96CEB4"]
                },
                "ema": {
                    "enabled": False,
                    "periods": [12, 26],
                    "colors": ["#DDA0DD", "#98D8C8"]
                },
                "bollinger_bands": {
                    "enabled": False,
                    "period": 20,
                    "std_dev": 2.0,
                    "colors": {
                        "upper": "#FF6B6B",
                        "middle": "#4ECDC4",
                        "lower": "#FF6B6B"
                    }
                },
                "rsi": {
                    "enabled": False,
                    "period": 14,
                    "overbought": 70,
                    "oversold": 30,
                    "color": "#9B59B6"
                },
                "macd": {
                    "enabled": False,
                    "fast": 12,
                    "slow": 26,
                    "signal": 9,
                    "colors": {
                        "macd": "#3498DB",
                        "signal": "#E74C3C",
                        "histogram": "#2ECC71"
                    }
                }
            },
            
            # UI 布局设置
            "ui": {
                "sidebar_width": 300,
                "show_orderbook": True,
                "show_trades": True,
                "show_indicators_panel": True,
                "max_trades_display": 50,
                "max_orderbook_levels": 10,
                "update_interval": 100,  # ms
                "animation_duration": 300  # ms
            },
            
            # 数据验证设置
            "validation": {
                "enabled": True,
                "price_change_threshold": 0.20,  # 20%
                "volume_spike_threshold": 10.0,  # 10x
                "gap_threshold": 0.05,  # 5%
                "min_price": 0.001,
                "max_price": 1000000,
                "log_anomalies": True,
                "alert_on_anomaly": False
            },
            
            # 性能设置
            "performance": {
                "batch_updates": True,
                "max_queue_size": 100,
                "gc_interval": 300,  # seconds
                "memory_limit_mb": 512,
                "cache_enabled": True,
                "cache_size_mb": 64
            },
            
            # 日志设置
            "logging": {
                "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
                "file_enabled": True,
                "file_path": "logs/luminaut_viewer.log",
                "max_file_size_mb": 10,
                "backup_count": 5,
                "console_enabled": True
            }
        }
        
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 合并用户配置和默认配置
                config = self._deep_merge(self.default_config.copy(), user_config)
                self.logger.info(f"配置文件加载成功: {self.config_file}")
                return config
            else:
                self.logger.info("配置文件不存在，使用默认配置")
                return self.default_config.copy()
                
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            self.logger.info("使用默认配置")
            return self.default_config.copy()
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置文件保存成功: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值，支持点号路径，如 'app.symbol'"""
        try:
            keys = key_path.split('.')
            value = self.config
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """设置配置值，支持点号路径"""
        try:
            keys = key_path.split('.')
            config = self.config
            
            # 导航到最后一级的父级
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # 设置值
            config[keys[-1]] = value
            
            self.logger.info(f"配置更新: {key_path} = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置配置失败: {key_path} = {value}, 错误: {e}")
            return False
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置节"""
        return self.config.get(section, {})
    
    def update_section(self, section: str, updates: Dict[str, Any]) -> bool:
        """更新配置节"""
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section].update(updates)
            self.logger.info(f"配置节更新: {section}")
            return True
            
        except Exception as e:
            self.logger.error(f"更新配置节失败: {section}, 错误: {e}")
            return False
    
    def reset_to_default(self, section: Optional[str] = None) -> bool:
        """重置为默认配置"""
        try:
            if section:
                if section in self.default_config:
                    self.config[section] = self.default_config[section].copy()
                    self.logger.info(f"配置节重置: {section}")
                    return True
            else:
                self.config = self.default_config.copy()
                self.logger.info("全部配置重置为默认值")
                return True
                
        except Exception as e:
            self.logger.error(f"重置配置失败: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"配置导出成功: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 验证配置格式
            if not isinstance(imported_config, dict):
                raise ValueError("配置文件格式错误")
            
            # 合并配置
            self.config = self._deep_merge(self.default_config.copy(), imported_config)
            self.logger.info(f"配置导入成功: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导入配置失败: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置的有效性"""
        issues = []
        warnings = []
        
        try:
            # 验证应用程序设置
            if self.get('app.mode') not in ['historical', 'realtime']:
                issues.append("app.mode 必须是 'historical' 或 'realtime'")
            
            if self.get('app.timeframe') not in ['1min', '5min', '15min', '1H']:
                warnings.append("app.timeframe 可能不是标准时间周期")
            
            # 验证图表设置
            chart_width = self.get('chart.width')
            if not isinstance(chart_width, int) or chart_width < 800:
                issues.append("chart.width 必须是大于等于800的整数")
            
            chart_height = self.get('chart.height')
            if not isinstance(chart_height, int) or chart_height < 600:
                issues.append("chart.height 必须是大于等于600的整数")
            
            # 验证技术指标设置
            sma_periods = self.get('indicators.sma.periods', [])
            if not all(isinstance(p, int) and p > 0 for p in sma_periods):
                issues.append("indicators.sma.periods 必须是正整数列表")
            
            # 验证性能设置
            update_interval = self.get('ui.update_interval')
            if not isinstance(update_interval, int) or update_interval < 50:
                warnings.append("ui.update_interval 建议大于等于50ms")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'warnings': warnings
            }
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return {
                'valid': False,
                'issues': [f"验证过程出错: {e}"],
                'warnings': []
            }
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_summary(self) -> str:
        """获取配置摘要"""
        try:
            summary = []
            summary.append("=== Luminaut Viewer 配置摘要 ===")
            summary.append(f"模式: {self.get('app.mode')}")
            summary.append(f"交易对: {self.get('app.symbol').upper()}")
            summary.append(f"时间周期: {self.get('app.timeframe')}")
            summary.append(f"主题: {self.get('app.theme')}")
            summary.append(f"图表尺寸: {self.get('chart.width')}x{self.get('chart.height')}")
            summary.append(f"数据源: {self.get('data_source.exchange')}")
            
            enabled_indicators = []
            for indicator, config in self.get_section('indicators').items():
                if isinstance(config, dict) and config.get('enabled', False):
                    enabled_indicators.append(indicator.upper())
            
            if enabled_indicators:
                summary.append(f"启用指标: {', '.join(enabled_indicators)}")
            
            summary.append(f"配置文件: {self.config_file}")
            
            return '\n'.join(summary)
            
        except Exception as e:
            self.logger.error(f"生成配置摘要失败: {e}")
            return "配置摘要生成失败"
