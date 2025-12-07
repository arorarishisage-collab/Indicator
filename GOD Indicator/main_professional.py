#!/usr/bin/env python3
"""
Gold Trading Signal System - Professional Backtesting Integration
Complete end-to-end trading tool with 4-step professional backtesting methodology,
charting, live data support, and signal generation.

FEATURES:
- 4-step professional backtesting (Data → Strategy → Backtest → Analysis)
- yfinance integration for NSE stocks
- Technical indicators library (10+ indicators)
- Realistic execution modeling (commissions, slippage, position sizing)
- 20+ performance metrics
- Live market data monitoring
- Multi-strategy comparison and ranking
"""

import sys
import os
import traceback
import platform
from pathlib import Path

# Ensure output is unbuffered for immediate display
sys.stdout = os.__stdout__
sys.stderr = os.__stderr__

# Add project root to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Check for command line flags
headless_mode = '--headless' in sys.argv or '--backend' in sys.argv or '--test' in sys.argv
cli_mode = '--cli' in sys.argv
professional_mode = '--professional' in sys.argv or '--backtest-pro' in sys.argv
live_mode = '--live' in sys.argv

# Clean up sys.argv
sys.argv = [arg for arg in sys.argv if arg not in ['--headless', '--backend', '--test', '--cli', '--professional', '--backtest-pro', '--live']]

print("🚀 Gold Trading Signal System Starting...", flush=True)


def run_professional_backtest():
    """
    Run professional 4-step backtesting workflow
    
    Steps:
    1. 📊 Data Acquisition - Fetch from yfinance
    2. 📝 Strategy Implementation - Apply technical indicators
    3. 🧪 Backtesting - Execute with realistic costs
    4. 📈 Performance Analysis - Calculate 20+ metrics
    """
    print("\n" + "="*80, flush=True)
    print("📊 PROFESSIONAL 4-STEP BACKTESTING WORKFLOW", flush=True)
    print("="*80, flush=True)
    
    try:
        # Import professional modules
        print("\n📦 Importing professional backtesting modules...", flush=True)
        from backend.data_manager import DataManager
        from backend.technical_indicators import TechnicalIndicators
        from backend.professional_backtester import ProfessionalBacktester, BacktestConfig
        from backend.performance_metrics import PerformanceAnalyzer, StrategyComparator
        import pandas as pd
        print("   ✓ All modules imported successfully", flush=True)
        
        # ==================== STEP 1: DATA ACQUISITION ====================
        print("\n" + "─"*80)
        print("📊 STEP 1: DATA ACQUISITION")
        print("─"*80)
        
        data_manager = DataManager(use_cache=True)
        
        # Ask user for stock selection (or use default)
        print("\nAvailable NSE stocks:", flush=True)
        available_stocks = data_manager.list_available_nse_stocks()
        for i, stock in enumerate(available_stocks[:5], 1):
            print(f"  {i}. {stock}", flush=True)
        print(f"  ... and more (total: {len(available_stocks)})", flush=True)
        
        # Use RELIANCE as default for demonstration
        symbol = 'RELIANCE'
        print(f"\nFetching historical data for {symbol}.NS (1 year daily)...", flush=True)
        
        df = data_manager.fetch_historical_data(
            symbol=symbol,
            start_date='2023-01-01',
            end_date='2024-01-01',
            timeframe='1d',
            is_nse=True
        )
        
        if df.empty:
            print("⚠️  No data available, generating sample data...", flush=True)
            df = _generate_sample_data()
        
        # Validate data
        is_valid, message = data_manager.validate_data(df)
        print(f"Data validation: {message}", flush=True)
        
        if not is_valid:
            print("❌ Data validation failed. Exiting.", flush=True)
            return
        
        print(f"✓ Loaded {len(df)} bars of OHLCV data", flush=True)
        print(f"  Price range: ₹{df['Low'].min():.2f} - ₹{df['High'].max():.2f}", flush=True)
        print(f"  Date range: {df['DateTime'].min()} to {df['DateTime'].max()}", flush=True)
        
        # ==================== STEP 2: STRATEGY IMPLEMENTATION ====================
        print("\n" + "─"*80)
        print("📝 STEP 2: STRATEGY IMPLEMENTATION")
        print("─"*80)
        
        print("\nCalculating technical indicators...", flush=True)
        
        # Define indicator configuration
        indicators_config = {
            'SMA_20': {'type': 'sma', 'period': 20},
            'SMA_50': {'type': 'sma', 'period': 50},
            'RSI_14': {'type': 'rsi', 'period': 14},
            'MACD': {'type': 'macd'},
            'BB_20': {'type': 'bollinger_bands', 'period': 20},
            'ATR_14': {'type': 'atr', 'period': 14},
        }
        
        df_indicators = TechnicalIndicators.calculate_indicators(df.copy(), indicators_config)
        print("✓ Indicators calculated: SMA, RSI, MACD, Bollinger Bands, ATR", flush=True)
        
        # Generate trading signals - MA Crossover Strategy
        print("\nGenerating trading signals (MA Crossover: SMA20 > SMA50)...", flush=True)
        
        signals = pd.Series(0, index=range(len(df_indicators)))
        signals[df_indicators['SMA_20'] > df_indicators['SMA_50']] = 1
        signals[df_indicators['SMA_20'] < df_indicators['SMA_50']] = -1
        
        signal_transitions = (signals.diff() != 0).sum()
        print(f"✓ Generated trading signals ({signal_transitions} transitions)", flush=True)
        
        # ==================== STEP 3: BACKTESTING ====================
        print("\n" + "─"*80)
        print("🧪 STEP 3: BACKTESTING (Realistic Execution Model)")
        print("─"*80)
        
        # Configure backtester with realistic parameters
        config = BacktestConfig(
            initial_capital=100000,  # ₹1,00,000
            commission=0.001,  # 0.1% per trade
            slippage=0.0005,  # 0.05%
            position_size_percent=0.95,  # Use 95% of capital per trade
            use_atr_stop_loss=True,
            atr_multiplier=2.0,
        )
        
        print(f"\nBacktest Configuration:", flush=True)
        print(f"  Initial Capital: ₹{config.initial_capital:,.0f}", flush=True)
        print(f"  Commission: {config.commission*100:.2f}% per trade", flush=True)
        print(f"  Slippage: {config.slippage*100:.2f}%", flush=True)
        print(f"  Position Size: {config.position_size_percent*100:.0f}% of capital", flush=True)
        
        print(f"\nRunning backtest...", flush=True)
        
        backtester = ProfessionalBacktester(config)
        result = backtester.backtest(df_indicators, signals)
        
        # ==================== STEP 4: PERFORMANCE ANALYSIS ====================
        print("\n" + "─"*80)
        print("📈 STEP 4: PERFORMANCE ANALYSIS (20+ Metrics)")
        print("─"*80)
        
        analyzer = PerformanceAnalyzer(initial_capital=config.initial_capital)
        
        # Generate comprehensive report
        report = analyzer.generate_report(result)
        print(report)
        
        # Export results
        print("\nExporting results...", flush=True)
        
        reports_dir = Path('reports')
        reports_dir.mkdir(exist_ok=True)
        
        trades_df = result.get_trades_dataframe()
        trades_csv = reports_dir / f'trades_{symbol}_professional.csv'
        trades_df.to_csv(trades_csv, index=False)
        print(f"✓ Trades exported: {trades_csv}")
        
        equity_df = result.get_equity_dataframe()
        equity_csv = reports_dir / f'equity_curve_{symbol}_professional.csv'
        equity_df.to_csv(equity_csv, index=False)
        print(f"✓ Equity curve exported: {equity_csv}")
        
        metrics_json = reports_dir / f'metrics_{symbol}_professional.json'
        analyzer.export_to_json(result, str(metrics_json))
        print(f"✓ Metrics exported: {metrics_json}")
        
        # Generate chart
        try:
            from backend.charting import plot_price_with_signals
            chart_path = plot_price_with_signals(
                df_indicators,
                strategy_name=f"{symbol} - MA Crossover Professional",
                output_dir='reports'
            )
            print(f"✓ Chart generated: {chart_path}")
        except Exception as e:
            print(f"⚠️  Chart generation skipped: {e}")
        
        print("\n" + "="*80)
        print("✅ PROFESSIONAL BACKTESTING COMPLETE")
        print("="*80 + "\n")
        
        return result, analyzer
        
    except Exception as e:
        print(f"\n❌ Error in professional backtesting: {e}\n", flush=True)
        traceback.print_exc()
        return None, None


def run_multi_strategy_comparison():
    """
    Compare multiple trading strategies with professional backtesting
    """
    print("\n" + "="*80, flush=True)
    print("📊 MULTI-STRATEGY PROFESSIONAL COMPARISON", flush=True)
    print("="*80, flush=True)
    
    try:
        from backend.data_manager import DataManager
        from backend.technical_indicators import TechnicalIndicators
        from backend.professional_backtester import ProfessionalBacktester, BacktestConfig
        from backend.performance_metrics import PerformanceAnalyzer, StrategyComparator
        import pandas as pd
        
        # Fetch data
        print("\nFetching data for comparison...", flush=True)
        data_manager = DataManager(use_cache=True)
        df = data_manager.fetch_historical_data(
            symbol='TCS',
            start_date='2023-01-01',
            end_date='2024-01-01',
            timeframe='1d',
            is_nse=True
        )
        
        if df.empty:
            df = _generate_sample_data()
        
        # Calculate indicators
        indicators_config = {
            'SMA_20': {'type': 'sma', 'period': 20},
            'SMA_50': {'type': 'sma', 'period': 50},
            'RSI_14': {'type': 'rsi', 'period': 14},
            'MACD': {'type': 'macd'},
        }
        
        df = TechnicalIndicators.calculate_indicators(df, indicators_config)
        
        # Configure backtester
        config = BacktestConfig(initial_capital=100000)
        backtester = ProfessionalBacktester(config)
        analyzer = PerformanceAnalyzer()
        
        results = {}
        
        # Strategy 1: MA Crossover
        print("\n1. Testing MA Crossover Strategy...", flush=True)
        signals_ma = pd.Series(0, index=range(len(df)))
        signals_ma[df['SMA_20'] > df['SMA_50']] = 1
        signals_ma[df['SMA_20'] < df['SMA_50']] = -1
        result_ma = backtester.backtest(df, signals_ma)
        metrics_ma = analyzer.analyze(result_ma)
        results['MA Crossover'] = metrics_ma
        
        # Strategy 2: RSI
        print("2. Testing RSI Overbought/Oversold Strategy...", flush=True)
        signals_rsi = pd.Series(0, index=range(len(df)))
        signals_rsi[df['RSI_14'] > 70] = -1  # Sell
        signals_rsi[df['RSI_14'] < 30] = 1   # Buy
        result_rsi = backtester.backtest(df, signals_rsi)
        metrics_rsi = analyzer.analyze(result_rsi)
        results['RSI Overbought/Oversold'] = metrics_rsi
        
        # Strategy 3: MACD
        print("3. Testing MACD Strategy...", flush=True)
        signals_macd = pd.Series(0, index=range(len(df)))
        signals_macd[df['MACD_Line'] > df['Signal_Line']] = 1
        signals_macd[df['MACD_Line'] < df['Signal_Line']] = -1
        result_macd = backtester.backtest(df, signals_macd)
        metrics_macd = analyzer.analyze(result_macd)
        results['MACD'] = metrics_macd
        
        # Compare
        print("\n" + "─"*80)
        print("STRATEGY COMPARISON RESULTS")
        print("─"*80)
        
        comparison = StrategyComparator.compare(results)
        print("\nRanked by Total Return:")
        print(comparison.to_string(index=False))
        
        ranking = StrategyComparator.rank_strategies(results)
        print("\n\nOverall Rankings (Weighted Scoring):")
        print(ranking.to_string(index=False))
        
        # Export comparison
        reports_dir = Path('reports')
        reports_dir.mkdir(exist_ok=True)
        comparison.to_csv(reports_dir / 'strategy_comparison.csv', index=False)
        ranking.to_csv(reports_dir / 'strategy_ranking.csv', index=False)
        print(f"\n✓ Comparison exported: {reports_dir}/strategy_comparison.csv")
        
        print("\n" + "="*80)
        print("✅ STRATEGY COMPARISON COMPLETE")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error in strategy comparison: {e}\n", flush=True)
        traceback.print_exc()


def run_live_monitoring():
    """
    Monitor live market data and generate trading signals
    """
    print("\n" + "="*80, flush=True)
    print("📊 LIVE MARKET MONITORING", flush=True)
    print("="*80, flush=True)
    
    try:
        from backend.live_data_fetcher import LiveDataFetcher, RealTimeSignalGenerator
        
        fetcher = LiveDataFetcher(refresh_interval=60)
        
        symbols = ['RELIANCE', 'TCS', 'INFOSY']
        print(f"\nWatching {len(symbols)} symbols for live data...", flush=True)
        
        live_results = []
        for symbol in symbols:
            live_data = fetcher.watch_symbol(symbol, is_nse=True)
            if live_data:
                live_results.append({
                    'Symbol': live_data['symbol'],
                    'Price': f"₹{live_data['current_price']:.2f}",
                    'Change': f"{live_data['change_percent']:+.2f}%",
                })
        
        if live_results:
            import pandas as pd
            df_live = pd.DataFrame(live_results)
            print("\nCurrent Market Data:")
            print(df_live.to_string(index=False))
            
            # Set price alerts
            print("\nSetting price alerts...", flush=True)
            fetcher.set_price_alert('RELIANCE.NS', price_target=2700, alert_type='above')
            fetcher.set_price_alert('TCS.NS', price_target=3500, alert_type='above')
            
            # Generate signals
            signal_gen = RealTimeSignalGenerator(fetcher)
            signals = signal_gen.check_signals()
            if signals:
                print("\nGenerated Trading Signals:")
                for symbol, signal in signals.items():
                    print(f"  {symbol}: {signal}")
            
            # Export live data
            fetcher.export_live_data('reports/live_market_data.csv')
            print("\n✓ Live data exported: reports/live_market_data.csv")
        
        print("\n" + "="*80)
        print("✅ LIVE MONITORING COMPLETE")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error in live monitoring: {e}\n", flush=True)
        traceback.print_exc()


def run_headless_backtest():
    """Run backtest in headless mode without GUI (legacy)"""
    print("\n" + "="*70, flush=True)
    print("🎯  GOLD TRADING SIGNAL SYSTEM - HEADLESS BACKTESTER (LEGACY)", flush=True)
    print("="*70, flush=True)
    
    try:
        print("\n📦 Importing backend modules...", flush=True)
        from backend.data_fetch import DataFetcher
        from backend.strategies import StrategyFactory
        from backend.enhanced_backtester import EnhancedBacktester
        print("   ✓ Imports successful", flush=True)
        
        # Load data
        print("\n📊 Loading historical gold price data...")
        fetcher = DataFetcher()
        df = fetcher.fetch_historical_data('XAUUSD', use_fallback=True)
        print(f"   ✓ Loaded {len(df)} bars of XAUUSD data")
        
        # Discover and list available strategies
        try:
            from backend.base_strategy import StrategyFactory
            StrategyFactory.load_plugins(str(Path(__file__).parent / 'backend' / 'strategy_plugins'))
            strategies_list = StrategyFactory.list_strategies()
        except Exception:
            strategies_list = ['ICTStrategy', 'MovingAverageCrossStrategy', 'MomentumStrategy']

        print("\n🤖 Available Strategies:")
        for i, s in enumerate(strategies_list, 1):
            print(f"   {i}. {s}")
        
        # Run backtests
        print("\n⚙️  Running multi-strategy backtest...\n")
        
        bt = EnhancedBacktester(initial_capital=10000)
        
        # Import analyzers
        analyzer = None
        try:
            from backend.results_analyzer import ResultsAnalyzer
            analyzer = ResultsAnalyzer(output_dir='reports')
        except Exception:
            pass
        
        for strategy_name in strategies_list:
            print(f"\n{'─'*70}")
            print(f"Testing: {strategy_name}")
            print('─'*70)
            
            try:
                strategy = StrategyFactory.create(strategy_name)
                df_signals = strategy.generate_signals(df.copy())
                results = bt.run_backtest(df_signals, strategy_name)
                metrics = results['metrics']

                print(f"  Total Trades:        {metrics['total_trades']}")
                print(f"  Win Rate:            {metrics['win_rate']:.1f}%")
                print(f"  Total Return:        {metrics['total_return']:.2f}%")
                print(f"  Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
                print(f"  Max Drawdown:        {metrics['max_drawdown']:.2f}%")
                
                if analyzer:
                    analyzer.add_result(strategy_name, results)
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        # Export results
        if analyzer:
            csv_path = analyzer.export_csv()
            print(f"\n✓ Strategy comparison exported to: {csv_path}")

        print(f"\n{'─'*70}")
        print("✅ Headless backtest completed!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n", flush=True)
        traceback.print_exc()
        sys.exit(1)


def run_gui():
    """Run the PyQt6 GUI application"""
    try:
        os.environ.setdefault('QT_API', 'pyqt6')

        if platform.system() == 'Darwin':
            os.environ.setdefault('QT_MAC_WANTS_LAYER', '1')
            os.environ.setdefault('QT_OPENGL', 'software')
            os.environ.setdefault('QT_QPA_PLATFORM', os.environ.get('QT_QPA_PLATFORM', 'cocoa'))

        from PyQt6.QtWidgets import QApplication
        from app.trading_tool_gui import TradingToolGUI

        print("🚀 Starting Gold Trading Signal System GUI...\n")

        app = QApplication(sys.argv)
        window = TradingToolGUI()
        window.show()

        sys.exit(app.exec())
        
    except ImportError as e:
        if 'PyQt6' in str(e) or 'PySide6' in str(e):
            print("❌ GUI library not installed. Install with: pip install PyQt6 PyQt6-WebEngine")
            print("Falling back to professional backtesting mode...\n")
            run_professional_backtest()
            return
        else:
            print(f"❌ Import Error: {e}")
            raise

    except Exception as e:
        print(f"\n❌ GUI Error: {e}")
        print("Falling back to professional backtesting mode...\n")
        try:
            run_professional_backtest()
        except Exception:
            print("Backtest fallback failed. Exiting.")
            traceback.print_exc()
            sys.exit(1)


def _generate_sample_data(periods=252):
    """Generate sample OHLCV data for testing"""
    import numpy as np
    from datetime import datetime, timedelta
    import pandas as pd
    
    np.random.seed(42)
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(periods)]
    close_prices = 2500 + np.cumsum(np.random.randn(periods) * 10)
    
    data = {
        'DateTime': dates,
        'Open': close_prices + np.random.randn(periods) * 5,
        'High': close_prices + np.abs(np.random.randn(periods) * 10),
        'Low': close_prices - np.abs(np.random.randn(periods) * 10),
        'Close': close_prices,
        'Volume': np.random.uniform(1000000, 5000000, periods),
    }
    
    return pd.DataFrame(data)


def print_help():
    """Print usage information"""
    print("""
Gold Trading Signal System - Usage

MODES:
  Default (GUI):           python main.py
  Professional Mode:       python main.py --professional
  Multi-Strategy Compare:  python main.py --backtest-pro (then select option 2)
  Live Monitoring:         python main.py --live
  Headless (Legacy):       python main.py --headless
  
FEATURES:
  📊 4-step professional backtesting methodology
  🤖 Multi-strategy comparison and ranking
  📈 20+ performance metrics
  💹 Live market data monitoring (yfinance)
  📝 Technical indicators library (10+ indicators)
  💾 Export to CSV/JSON
  📉 Professional charting

EXAMPLES:
  # Run professional backtest
  python main.py --professional
  
  # Compare multiple strategies
  python main.py --professional  # then select option 2
  
  # Monitor live market data
  python main.py --live
  
  # Run with GUI
  python main.py
""")


if __name__ == '__main__':
    
    if '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0)
    
    print(f"Mode: Professional={professional_mode}, Live={live_mode}, Headless={headless_mode}\n", flush=True)
    
    if professional_mode:
        run_professional_backtest()
        run_multi_strategy_comparison()
    elif live_mode:
        run_live_monitoring()
    elif headless_mode:
        run_headless_backtest()
    else:
        run_gui()
