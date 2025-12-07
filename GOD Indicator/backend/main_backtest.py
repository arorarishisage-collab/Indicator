"""
Main Backtest Script
Orchestrates data fetching, zone detection, signal generation, and backtesting.
Produces comprehensive reports and visualizations.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime
import json
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from data_fetch import DataFetcher
from zone_detector import ZoneDetector
from signal_generator import SignalGenerator
from backtester import SimpleBacktester, export_trades_csv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktestOrchestrator:
    """Orchestrates complete backtesting workflow."""
    
    def __init__(
        self,
        symbol: str = 'GC=F',
        start_date: str = '2020-01-01',
        end_date: str = None,
        timeframes: list = ['1h', '4h'],
        lookback_bars: int = 500
    ):
        """
        Initialize backtesting orchestrator.
        
        Args:
            symbol: Ticker symbol (default: GC=F for gold)
            start_date: Start date for backtest
            end_date: End date (defaults to today)
            timeframes: List of timeframes to backtest
            lookback_bars: Number of bars to analyze
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        self.timeframes = timeframes
        self.lookback_bars = lookback_bars
        self.reports_dir = Path(__file__).parent.parent / 'reports'
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_full_backtest(self) -> dict:
        """
        Execute complete backtest workflow.
        
        Returns:
            Dictionary with results for each timeframe
        """
        results = {}
        
        logger.info(f"\n{'='*70}")
        logger.info(f"INITIATING GOLD (XAU/USD) TRADING SIGNAL BACKTEST")
        logger.info(f"Period: {self.start_date} to {self.end_date}")
        logger.info(f"Timeframes: {self.timeframes}")
        logger.info(f"{'='*70}\n")
        
        # Step 1: Fetch data
        logger.info("STEP 1: Fetching historical data...")
        fetcher = DataFetcher()
        
        try:
            data_dict = fetcher.fetch_multiple_timeframes(
                symbol=self.symbol,
                timeframes=self.timeframes,
                start_date=self.start_date,
                end_date=self.end_date
            )
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return {}
        
        # Process each timeframe
        for tf, df in data_dict.items():
            logger.info(f"\n{'─'*70}")
            logger.info(f"PROCESSING TIMEFRAME: {tf}")
            logger.info(f"Candles: {len(df)}")
            logger.info(f"{'─'*70}\n")
            
            # Step 2: Add indicators
            logger.info("Adding technical indicators...")
            df = fetcher.add_technical_indicators(df)
            
            # Validate data
            if not fetcher.validate_data(df):
                logger.warning(f"Data validation failed for {tf}")
                continue
            
            # Use recent data for analysis
            df = df.tail(self.lookback_bars).copy()
            
            # Step 3: Detect zones
            logger.info("Detecting supply/demand zones...")
            detector = ZoneDetector(lookback=20, atr_multiplier=1.5)
            
            swing_highs, swing_lows = detector.detect_swings(df)
            zones = detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
            zones = detector.update_zone_mitigation(zones, df)
            
            # Step 4: Detect ICT elements
            logger.info("Detecting ICT elements (Order Blocks, FVGs)...")
            
            obs = detector.detect_order_blocks(df)
            fvgs = detector.detect_fair_value_gaps(df)
            srl = detector.detect_support_resistance(df, n_recent=5)
            
            logger.info(f"S/R Levels: Resistance={srl['resistance'][:3]}, Support={srl['support'][:3]}")
            
            # Step 5: Generate signals
            logger.info("Generating trading signals...")
            generator = SignalGenerator(
                min_risk_reward=1.5,
                ema_fast=30,
                ema_slow=200
            )
            
            df = generator.generate_signals(df, zones, obs, fvgs, srl, lookback=len(df))
            
            # Step 6: Run backtest
            logger.info("Running backtest with slippage & spread...")
            backtester = SimpleBacktester(
                initial_capital=10000,
                position_size=0.95,
                slippage_pips=1.0,
                spread_pips=0.5
            )
            
            backtest_results = backtester.run_backtest(df)
            
            # Step 7: Print report
            report = backtester.print_backtest_report(backtest_results)
            logger.info(report)
            
            # Store results
            results[tf] = {
                'dataframe': df,
                'backtest_results': backtest_results,
                'zones': zones,
                'order_blocks': obs,
                'fvgs': fvgs,
                'support_resistance': srl
            }
            
            # Export trades
            if backtest_results['trades']:
                trades_file = self.reports_dir / f'trades_{tf}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                export_trades_csv(backtest_results['trades'], str(trades_file))
        
        # Summary comparison
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: dict) -> None:
        """Print summary comparison across timeframes."""
        if not results:
            return
        
        logger.info(f"\n{'='*70}")
        logger.info("BACKTEST SUMMARY - MULTI-TIMEFRAME COMPARISON")
        logger.info(f"{'='*70}\n")
        
        summary_data = []
        for tf, data in results.items():
            br = data['backtest_results']
            summary_data.append({
                'Timeframe': tf,
                'Trades': br['total_trades'],
                'Win Rate %': f"{br['win_rate']:.1f}%",
                'PF': f"{br['profit_factor']:.2f}",
                'Total P&L': f"${br['total_pnl']:.0f}",
                'Max DD %': f"{br['max_drawdown_pct']:.1f}%",
                'Sharpe': f"{br['sharpe_ratio']:.2f}"
            })
        
        summary_df = pd.DataFrame(summary_data)
        logger.info(summary_df.to_string(index=False))
        
        logger.info("\n" + "="*70)
        logger.info("KEY METRICS THRESHOLDS:")
        logger.info("  ✓ Win Rate > 55%")
        logger.info("  ✓ Profit Factor > 1.5")
        logger.info("  ✓ Max Drawdown < 20%")
        logger.info("="*70 + "\n")
    
    def export_results_json(self, results: dict, filename: str = None) -> str:
        """
        Export results to JSON (excluding large DataFrames).
        
        Args:
            results: Results dictionary
            filename: Output filename (auto-generated if None)
        
        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.reports_dir / filename
        
        # Extract exportable data
        export_data = {}
        for tf, data in results.items():
            export_data[tf] = {
                'backtest_results': {
                    k: v for k, v in data['backtest_results'].items()
                    if k != 'trades'
                },
                'num_zones': len(data['zones']),
                'num_order_blocks': len(data['order_blocks']),
                'num_fvgs': len(data['fvgs'])
            }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Results exported to {filepath}")
        return str(filepath)


def main():
    """Main entry point for backtest."""
    
    # Configuration
    CONFIG = {
        'symbol': 'GC=F',
        'start_date': '2020-01-01',
        'end_date': None,  # Today
        'timeframes': ['1h', '4h'],
        'lookback_bars': 500
    }
    
    # Run backtest
    orchestrator = BacktestOrchestrator(**CONFIG)
    results = orchestrator.run_full_backtest()
    
    # Export results
    if results:
        orchestrator.export_results_json(results)
        logger.info(f"\n✓ Backtest complete. Reports saved to {orchestrator.reports_dir}")
    else:
        logger.error("Backtest failed or produced no results.")
        sys.exit(1)


if __name__ == "__main__":
    main()
