"""
Binance 历史数据下载器

下载历史 K线和交易数据，用于模型训练和回测

支持的数据类型：
1. 历史交易数据（Trades）- tick-by-tick
2. 历史K线数据（Klines）- 1分钟级别（仅用于验证）
3. 历史聚合交易数据（Aggression Trades）

注意：Binance 不提供历史订单簿快照的免费下载
      需要通过持续采集或购买第三方数据
"""

import asyncio
import gzip
import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
import logging

import pandas as pd
import requests
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BinanceHistoricalDownloader:
    """Binance 历史数据下载器"""
    
    BASE_URL = "https://data.binance.vision/data/spot/daily"
    
    def __init__(self, symbol: str = "BTCUSDT", output_dir: str = "data/historical"):
        self.symbol = symbol
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"初始化历史数据下载器: {symbol}")
        logger.info(f"输出目录: {self.output_dir}")
    
    def download_trades(self, start_date: str, end_date: str) -> List[str]:
        """
        下载历史交易数据（tick-by-tick）
        
        Parameters:
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
        
        Returns:
            下载的文件路径列表
        """
        logger.info("=" * 70)
        logger.info(f"📥 下载历史交易数据: {start_date} 到 {end_date}")
        logger.info("=" * 70)
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        downloaded_files = []
        current = start
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            
            # 构建下载URL
            # 格式: https://data.binance.vision/data/spot/daily/trades/BTCUSDT/BTCUSDT-trades-2024-01-01.zip
            url = f"{self.BASE_URL}/trades/{self.symbol}/{self.symbol}-trades-{date_str}.zip"
            
            # 本地文件路径
            zip_file = self.output_dir / f"{self.symbol}-trades-{date_str}.zip"
            csv_file = self.output_dir / f"{self.symbol}-trades-{date_str}.csv"
            
            # 如果CSV已存在，跳过
            if csv_file.exists():
                logger.info(f"✅ {date_str} - 已存在，跳过")
                downloaded_files.append(str(csv_file))
                current += timedelta(days=1)
                continue
            
            # 下载文件
            try:
                logger.info(f"📥 下载 {date_str}...")
                response = requests.get(url, stream=True)
                
                if response.status_code == 200:
                    # 保存ZIP文件
                    total_size = int(response.headers.get('content-length', 0))
                    
                    with open(zip_file, 'wb') as f:
                        with tqdm(total=total_size, unit='B', unit_scale=True, desc=date_str) as pbar:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                                pbar.update(len(chunk))
                    
                    # 解压
                    logger.info(f"📦 解压 {date_str}...")
                    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                        zip_ref.extractall(self.output_dir)
                    
                    # 删除ZIP文件
                    zip_file.unlink()
                    
                    logger.info(f"✅ {date_str} - 下载完成")
                    downloaded_files.append(str(csv_file))
                    
                elif response.status_code == 404:
                    logger.warning(f"⚠️  {date_str} - 数据不存在（可能是未来日期或数据未发布）")
                else:
                    logger.error(f"❌ {date_str} - 下载失败: HTTP {response.status_code}")
            
            except Exception as e:
                logger.error(f"❌ {date_str} - 错误: {e}")
            
            current += timedelta(days=1)
        
        logger.info("=" * 70)
        logger.info(f"✅ 下载完成！共 {len(downloaded_files)} 个文件")
        logger.info("=" * 70)
        
        return downloaded_files
    
    def download_klines(self, start_date: str, end_date: str, interval: str = "1m") -> List[str]:
        """
        下载历史K线数据（用于验证VWAP等）
        
        Parameters:
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            interval: K线间隔，默认 '1m'（1分钟）
        
        Returns:
            下载的文件路径列表
        """
        logger.info("=" * 70)
        logger.info(f"📥 下载历史K线数据: {start_date} 到 {end_date} ({interval})")
        logger.info("=" * 70)
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        downloaded_files = []
        current = start
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            
            # URL格式: https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01-01.zip
            url = f"{self.BASE_URL}/klines/{self.symbol}/{interval}/{self.symbol}-{interval}-{date_str}.zip"
            
            zip_file = self.output_dir / f"{self.symbol}-{interval}-{date_str}.zip"
            csv_file = self.output_dir / f"{self.symbol}-{interval}-{date_str}.csv"
            
            if csv_file.exists():
                logger.info(f"✅ {date_str} - 已存在，跳过")
                downloaded_files.append(str(csv_file))
                current += timedelta(days=1)
                continue
            
            try:
                logger.info(f"📥 下载 {date_str}...")
                response = requests.get(url, stream=True)
                
                if response.status_code == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    
                    with open(zip_file, 'wb') as f:
                        with tqdm(total=total_size, unit='B', unit_scale=True, desc=date_str) as pbar:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                                pbar.update(len(chunk))
                    
                    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                        zip_ref.extractall(self.output_dir)
                    
                    zip_file.unlink()
                    
                    logger.info(f"✅ {date_str} - 下载完成")
                    downloaded_files.append(str(csv_file))
                    
                elif response.status_code == 404:
                    logger.warning(f"⚠️  {date_str} - 数据不存在")
                else:
                    logger.error(f"❌ {date_str} - 下载失败: HTTP {response.status_code}")
            
            except Exception as e:
                logger.error(f"❌ {date_str} - 错误: {e}")
            
            current += timedelta(days=1)
        
        logger.info("=" * 70)
        logger.info(f"✅ 下载完成！共 {len(downloaded_files)} 个文件")
        logger.info("=" * 70)
        
        return downloaded_files
    
    def merge_trades(self, files: List[str], output_file: str = None) -> str:
        """
        合并多个交易数据文件
        
        Parameters:
            files: CSV文件路径列表
            output_file: 输出文件路径（可选）
        
        Returns:
            合并后的文件路径
        """
        if not files:
            logger.warning("没有文件需要合并")
            return None
        
        logger.info(f"📦 合并 {len(files)} 个文件...")
        
        if output_file is None:
            output_file = self.output_dir / f"{self.symbol}_trades_merged.csv"
        
        # 读取并合并所有文件
        dfs = []
        for file in tqdm(files, desc="读取文件"):
            try:
                df = pd.read_csv(file, header=None)
                dfs.append(df)
            except Exception as e:
                logger.error(f"读取文件失败 {file}: {e}")
        
        if not dfs:
            logger.error("没有成功读取任何文件")
            return None
        
        # 合并
        merged = pd.concat(dfs, ignore_index=True)
        
        # 添加列名
        merged.columns = [
            'trade_id', 'price', 'quantity', 'quote_quantity',
            'timestamp', 'is_buyer_maker', 'is_best_match'
        ]
        
        # 转换时间戳
        merged['datetime'] = pd.to_datetime(merged['timestamp'], unit='ms')
        
        # 保存
        merged.to_csv(output_file, index=False)
        
        logger.info(f"✅ 合并完成: {output_file}")
        logger.info(f"   总记录数: {len(merged):,}")
        logger.info(f"   时间范围: {merged['datetime'].min()} 到 {merged['datetime'].max()}")
        logger.info(f"   文件大小: {Path(output_file).stat().st_size / 1024 / 1024:.2f} MB")
        
        return str(output_file)
    
    def generate_summary(self, files: List[str]) -> pd.DataFrame:
        """生成数据摘要"""
        logger.info("📊 生成数据摘要...")
        
        summaries = []
        
        for file in files:
            try:
                df = pd.read_csv(file, header=None, nrows=1000)  # 只读前1000行估算
                file_size = Path(file).stat().st_size / 1024 / 1024  # MB
                
                summaries.append({
                    'file': Path(file).name,
                    'size_mb': file_size,
                    'estimated_rows': len(df) * (Path(file).stat().st_size / 1000),  # 粗略估算
                })
            except Exception as e:
                logger.error(f"处理文件失败 {file}: {e}")
        
        summary_df = pd.DataFrame(summaries)
        
        logger.info("\n" + str(summary_df))
        logger.info(f"\n总大小: {summary_df['size_mb'].sum():.2f} MB")
        
        return summary_df


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Binance 历史数据下载器")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="交易对符号")
    parser.add_argument("--start-date", type=str, required=True, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, required=True, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--data-type", type=str, default="trades", choices=["trades", "klines", "both"], help="数据类型")
    parser.add_argument("--merge", action="store_true", help="是否合并文件")
    
    args = parser.parse_args()
    
    downloader = BinanceHistoricalDownloader(symbol=args.symbol)
    
    # 下载交易数据
    if args.data_type in ["trades", "both"]:
        trade_files = downloader.download_trades(args.start_date, args.end_date)
        
        if args.merge and trade_files:
            downloader.merge_trades(trade_files)
    
    # 下载K线数据
    if args.data_type in ["klines", "both"]:
        downloader.download_klines(args.start_date, args.end_date, interval="1m")
    
    logger.info("\n🎉 所有下载任务完成！")


if __name__ == "__main__":
    main()
