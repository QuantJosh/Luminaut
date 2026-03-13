"""
Luminaut Phase 1: Data Quality Validation Script

This script validates the quality of collected market data by:
1. Checking data completeness (missing timestamps)
2. Validating VWAP calculations
3. Analyzing spread and depth statistics
4. Checking for data anomalies
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


def find_latest_data_files(catalog_dir: str = "data/catalog"):
    """Find the most recent test data files."""
    catalog_path = Path(catalog_dir)
    
    # Find test files
    ob_files = list(catalog_path.glob("orderbook_test_*.csv"))
    trade_files = list(catalog_path.glob("trades_test_*.csv"))
    
    if not ob_files or not trade_files:
        raise FileNotFoundError("No test data files found. Run data collection first.")
    
    # Get latest files
    ob_file = max(ob_files, key=lambda f: f.stat().st_mtime)
    trade_file = max(trade_files, key=lambda f: f.stat().st_mtime)
    
    return ob_file, trade_file


def validate_orderbook_data(df: pd.DataFrame) -> dict:
    """Validate orderbook data quality."""
    results = {}
    
    # 1. Check data completeness
    df['ts_event'] = pd.to_numeric(df['ts_event'])
    time_diffs = df['ts_event'].diff().dropna() / 1e9  # Convert to seconds
    
    missing_updates = (time_diffs > 2).sum()
    avg_interval = time_diffs.mean()
    max_gap = time_diffs.max()
    
    results['completeness'] = {
        'total_updates': len(df),
        'missing_updates': int(missing_updates),
        'avg_interval_sec': round(avg_interval, 4),
        'max_gap_sec': round(max_gap, 4),
        'completeness_pct': round((1 - missing_updates / len(df)) * 100, 2) if len(df) > 0 else 0
    }
    
    # 2. Price statistics
    results['price_stats'] = {
        'min_price': round(df['mid_price'].min(), 2),
        'max_price': round(df['mid_price'].max(), 2),
        'avg_price': round(df['mid_price'].mean(), 2),
        'price_std': round(df['mid_price'].std(), 2),
        'price_range_pct': round((df['mid_price'].max() - df['mid_price'].min()) / df['mid_price'].mean() * 100, 4)
    }
    
    # 3. Spread analysis
    results['spread_stats'] = {
        'avg_spread_bps': round(df['spread_bps'].mean(), 6),
        'min_spread_bps': round(df['spread_bps'].min(), 6),
        'max_spread_bps': round(df['spread_bps'].max(), 6),
        'spread_std_bps': round(df['spread_bps'].std(), 6)
    }
    
    # 4. Depth analysis
    results['depth_stats'] = {
        'avg_bid_depth': round(df['bid_depth'].mean(), 4),
        'avg_ask_depth': round(df['ask_depth'].mean(), 4),
        'depth_imbalance': round(df['bid_depth'].mean() / df['ask_depth'].mean(), 4) if df['ask_depth'].mean() > 0 else 0
    }
    
    # 5. Anomaly detection
    price_jumps = (df['mid_price'].pct_change().abs() > 0.01).sum()  # >1% jumps
    results['anomalies'] = {
        'price_jumps_gt_1pct': int(price_jumps),
        'zero_spread_count': int((df['spread'] == 0).sum()),
        'negative_spread_count': int((df['spread'] < 0).sum())
    }
    
    return results


def validate_trade_data(df: pd.DataFrame) -> dict:
    """Validate trade data quality."""
    results = {}
    
    # 1. Trade statistics
    results['trade_stats'] = {
        'total_trades': len(df),
        'buy_trades': int((~df['is_buyer_maker']).sum()),
        'sell_trades': int(df['is_buyer_maker'].sum()),
        'buy_ratio': round((~df['is_buyer_maker']).mean() * 100, 2),
        'sell_ratio': round(df['is_buyer_maker'].mean() * 100, 2)
    }
    
    # 2. Volume analysis
    buy_vol = df[~df['is_buyer_maker']]['quantity'].sum()
    sell_vol = df[df['is_buyer_maker']]['quantity'].sum()
    total_vol = buy_vol + sell_vol
    
    results['volume_stats'] = {
        'total_volume': round(total_vol, 4),
        'buy_volume': round(buy_vol, 4),
        'sell_volume': round(sell_vol, 4),
        'buy_volume_ratio': round(buy_vol / total_vol * 100, 2) if total_vol > 0 else 0,
        'sell_volume_ratio': round(sell_vol / total_vol * 100, 2) if total_vol > 0 else 0,
        'avg_trade_size': round(df['quantity'].mean(), 6),
        'max_trade_size': round(df['quantity'].max(), 6)
    }
    
    # 3. Price statistics
    results['price_stats'] = {
        'min_price': round(df['price'].min(), 2),
        'max_price': round(df['price'].max(), 2),
        'avg_price': round(df['price'].mean(), 2),
        'vwap': round((df['price'] * df['quantity']).sum() / df['quantity'].sum(), 2) if df['quantity'].sum() > 0 else 0
    }
    
    return results


def compare_prices(orderbook_df: pd.DataFrame, trade_df: pd.DataFrame) -> dict:
    """Compare prices between orderbook and trade data."""
    results = {}
    
    # Merge on timestamp (approximate)
    ob_prices = orderbook_df.set_index('timestamp')['mid_price']
    trade_prices = trade_df.set_index('timestamp')['price']
    
    # Find common timestamps (within 1 second)
    common_count = 0
    price_diffs = []
    
    for ts, trade_price in trade_prices.items():
        # Find closest orderbook price
        if ts in ob_prices.index:
            ob_price = ob_prices.loc[ts]
            diff_pct = abs(trade_price - ob_price) / ob_price * 100
            price_diffs.append(diff_pct)
            common_count += 1
    
    if price_diffs:
        results['price_comparison'] = {
            'common_samples': common_count,
            'avg_price_diff_pct': round(np.mean(price_diffs), 6),
            'max_price_diff_pct': round(np.max(price_diffs), 6),
            'min_price_diff_pct': round(np.min(price_diffs), 6)
        }
    else:
        results['price_comparison'] = {
            'common_samples': 0,
            'note': 'No common timestamps found'
        }
    
    return results


def generate_report(ob_results: dict, trade_results: dict, price_results: dict) -> str:
    """Generate a formatted validation report."""
    report = []
    report.append("=" * 70)
    report.append("LUMINAUT PHASE 1: DATA QUALITY VALIDATION REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    report.append("")
    
    # Orderbook section
    report.append("ORDERBOOK DATA QUALITY")
    report.append("-" * 70)
    
    comp = ob_results['completeness']
    report.append(f"Data Completeness:")
    report.append(f"  - Total updates: {comp['total_updates']}")
    report.append(f"  - Missing updates: {comp['missing_updates']}")
    report.append(f"  - Completeness: {comp['completeness_pct']}%")
    report.append(f"  - Avg interval: {comp['avg_interval_sec']} seconds")
    report.append(f"  - Max gap: {comp['max_gap_sec']} seconds")
    report.append("")
    
    price = ob_results['price_stats']
    report.append(f"Price Statistics:")
    report.append(f"  - Range: {price['min_price']} - {price['max_price']}")
    report.append(f"  - Average: {price['avg_price']}")
    report.append(f"  - Std Dev: {price['price_std']}")
    report.append(f"  - Range %: {price['price_range_pct']}%")
    report.append("")
    
    spread = ob_results['spread_stats']
    report.append(f"Spread Statistics (basis points):")
    report.append(f"  - Average: {spread['avg_spread_bps']} bps")
    report.append(f"  - Range: {spread['min_spread_bps']} - {spread['max_spread_bps']} bps")
    report.append("")
    
    anomaly = ob_results['anomalies']
    report.append(f"Anomaly Detection:")
    report.append(f"  - Price jumps >1%: {anomaly['price_jumps_gt_1pct']}")
    report.append(f"  - Zero spread count: {anomaly['zero_spread_count']}")
    report.append(f"  - Negative spread count: {anomaly['negative_spread_count']}")
    report.append("")
    
    # Trade section
    report.append("TRADE DATA QUALITY")
    report.append("-" * 70)
    
    trade_stats = trade_results['trade_stats']
    report.append(f"Trade Statistics:")
    report.append(f"  - Total trades: {trade_stats['total_trades']}")
    report.append(f"  - Buy trades: {trade_stats['buy_trades']} ({trade_stats['buy_ratio']}%)")
    report.append(f"  - Sell trades: {trade_stats['sell_trades']} ({trade_stats['sell_ratio']}%)")
    report.append("")
    
    vol = trade_results['volume_stats']
    report.append(f"Volume Statistics:")
    report.append(f"  - Total volume: {vol['total_volume']}")
    report.append(f"  - Buy volume: {vol['buy_volume']} ({vol['buy_volume_ratio']}%)")
    report.append(f"  - Sell volume: {vol['sell_volume']} ({vol['sell_volume_ratio']}%)")
    report.append(f"  - Avg trade size: {vol['avg_trade_size']}")
    report.append(f"  - Max trade size: {vol['max_trade_size']}")
    report.append("")
    
    trade_price = trade_results['price_stats']
    report.append(f"Trade Price Statistics:")
    report.append(f"  - Range: {trade_price['min_price']} - {trade_price['max_price']}")
    report.append(f"  - VWAP: {trade_price['vwap']}")
    report.append("")
    
    # Price comparison section
    report.append("PRICE COMPARISON (Orderbook vs Trades)")
    report.append("-" * 70)
    
    price_comp = price_results.get('price_comparison', {})
    if 'common_samples' in price_comp and price_comp['common_samples'] > 0:
        report.append(f"  - Common samples: {price_comp['common_samples']}")
        report.append(f"  - Avg price diff: {price_comp['avg_price_diff_pct']}%")
        report.append(f"  - Max price diff: {price_comp['max_price_diff_pct']}%")
    else:
        report.append(f"  - {price_comp.get('note', 'N/A')}")
    report.append("")
    
    # Summary and recommendations
    report.append("VALIDATION SUMMARY")
    report.append("-" * 70)
    
    # Calculate overall score
    score = 100
    issues = []
    
    if comp['completeness_pct'] < 99:
        score -= 10
        issues.append("Data completeness below 99%")
    
    if comp['max_gap_sec'] > 5:
        score -= 5
        issues.append("Large gaps in orderbook updates")
    
    if spread['avg_spread_bps'] > 10:
        score -= 5
        issues.append("Unusually high average spread")
    
    if anomaly['price_jumps_gt_1pct'] > 0:
        score -= 5
        issues.append("Price jumps detected")
    
    if anomaly['negative_spread_count'] > 0:
        score -= 10
        issues.append("Negative spread detected (data error)")
    
    report.append(f"Overall Quality Score: {score}/100")
    report.append("")
    
    if issues:
        report.append("Issues Found:")
        for issue in issues:
            report.append(f"  - {issue}")
    else:
        report.append("[OK] No significant issues detected")
    
    report.append("")
    report.append("=" * 70)
    
    return "\n".join(report)


def main():
    """Main validation function."""
    print("Luminaut Data Quality Validator")
    print("=" * 50)
    
    try:
        # Find latest data files
        print("\nFinding latest data files...")
        ob_file, trade_file = find_latest_data_files()
        print(f"Orderbook file: {ob_file.name}")
        print(f"Trade file: {trade_file.name}")
        
        # Load data
        print("\nLoading data...")
        ob_df = pd.read_csv(ob_file)
        trade_df = pd.read_csv(trade_file)
        
        print(f"Loaded {len(ob_df)} orderbook updates")
        print(f"Loaded {len(trade_df)} trades")
        
        # Validate
        print("\nValidating data quality...")
        ob_results = validate_orderbook_data(ob_df)
        trade_results = validate_trade_data(trade_df)
        price_results = compare_prices(ob_df, trade_df)
        
        # Generate report
        report = generate_report(ob_results, trade_results, price_results)
        
        # Save report
        report_file = Path("logs") / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.parent.mkdir(exist_ok=True)
        report_file.write_text(report, encoding='utf-8')
        
        print("\n" + report)
        print(f"\nReport saved to: {report_file}")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please run data collection first: python scripts/quick_data_test.py --duration-minutes 5")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
