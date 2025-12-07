#!/usr/bin/env python3
"""
Gold Trading Signal System - Main Application
Complete end-to-end trading tool with multi-strategy backtesting, 
charting, and signal generation for manual trading execution.
"""


import sys
import os
import traceback
import platform
from pathlib import Path

# Add project root to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Check for command line flags
headless_mode = '--headless' in sys.argv or '--backend' in sys.argv or '--test' in sys.argv
cli_mode = '--cli' in sys.argv

# Clean up sys.argv
sys.argv = [arg for arg in sys.argv if arg not in ['--headless', '--backend', '--test', '--cli']]

print("🚀 Gold Trading Signal System Starting...", flush=True)

def run_headless_backtest():
    """Run backtest in headless mode without GUI"""
    print("\n" + "="*70, flush=True)
    print("🎯  GOLD TRADING SIGNAL SYSTEM - HEADLESS BACKTESTER", flush=True)
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
        df = fetcher.fetch_historical_data('XAUUSD')
        print(f"   ✓ Loaded {len(df)} bars of XAUUSD data")
        
        # Discover and list available strategies (including plugins)
        try:
            from backend.base_strategy import StrategyFactory
            # Load plugins from folder 'backend/strategy_plugins' (optional)
            StrategyFactory.load_plugins(str(Path(__file__).parent / 'backend' / 'strategy_plugins'))
            strategies_list = StrategyFactory.list_strategies()
        except Exception:
            # Fallback to built-in list if discovery fails
            strategies_list = [
                'ICTStrategy',
                'MovingAverageCrossStrategy', 
                'MomentumStrategy',
            ]

        print("\n🤖 Available Strategies:")
        for i, s in enumerate(strategies_list, 1):
            print(f"   {i}. {s}")
        
        # Run backtests
        print("\n⚙️  Running multi-strategy backtest...\n")
        
        bt = EnhancedBacktester(initial_capital=10000)
        
        # Import analyzers with error handling (optional features)
        analyzer = None
        try:
            from backend.results_analyzer import ResultsAnalyzer, SignalInsights
            analyzer = ResultsAnalyzer(output_dir='reports')
        except Exception as ier:
            print(f"  ⚠️ Results analyzer not available: {ier}")
        
        try:
            from backend.performance_display import PerformanceDisplay
            perf_display = PerformanceDisplay()
        except Exception as pde:
            print(f"  ⚠️ Performance display not available: {pde}")
            perf_display = None
        
        for strategy_name in strategies_list:
            print(f"\n{'─'*70}")
            print(f"Testing: {strategy_name}")
            print('─'*70)
            
            try:
                strategy = StrategyFactory.create(strategy_name)
                df_signals = strategy.generate_signals(df.copy())
                results = bt.run_backtest(df_signals, strategy_name)
                metrics = results['metrics']

                # Save a chart for this backtest (headless-friendly)
                try:
                    from backend.charting import plot_price_with_signals
                    chart_path = plot_price_with_signals(df_signals, strategy_name=strategy_name)
                    print(f"  Chart saved: {chart_path}")
                except Exception as ce:
                    print(f"  ⚠️ Chart generation failed: {ce}")
                
                print(f"  Total Trades:        {metrics['total_trades']}")
                print(f"  Win Rate:            {metrics['win_rate']:.1f}%")
                print(f"  Total Return:        {metrics['total_return']:.2f}%")
                print(f"  Sharpe Ratio:        {metrics['sharpe_ratio']:.2f}")
                print(f"  Max Drawdown:        {metrics['max_drawdown']:.2f}%")
                
                if metrics['total_trades'] > 0:
                    print(f"  Avg Win:             {metrics.get('avg_win', 0):.2f}%")
                    print(f"  Avg Loss:            {metrics.get('avg_loss', 0):.2f}%")
                    print(f"  Profit Factor:       {metrics.get('profit_factor', 0):.2f}")

                # Store result for comparison
                if analyzer:
                    analyzer.add_result(strategy_name, results)

                # Analyze signal quality
                insights = None
                try:
                    from backend.results_analyzer import SignalInsights
                    insights = SignalInsights.analyze_signal_quality(df_signals)
                except Exception:
                    pass
                    
                if insights:
                    print(f"  Signal Quality:")
                    print(f"    - Total Signals:     {insights.get('total_signals', 0)}")
                    print(f"    - Buy/Sell:          {insights.get('buy_signals', 0)}/{insights.get('sell_signals', 0)}")
                    print(f"    - Signal Density:    {insights.get('signal_density_%', 0):.2f}%")

                # Display detailed performance metrics (optional)
                if perf_display:
                    try:
                        print(f"\n{perf_display.format_metrics(metrics)}")
                        if results.get('trades'):
                            print(f"\n{perf_display.format_trade_summary(results.get('trades', []))}")
                            print(f"\n{perf_display.get_trade_insights(results.get('trades', []))}")
                    except Exception as pd_err:
                        pass  # Display is optional
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print(f"\n{'─'*70}")
        print("📊 GENERATING REPORTS AND EXPORTS...")
        print('─'*70 + "\n")

        # Print strategy comparison summary
        if analyzer:
            try:
                analyzer.print_summary()
            except Exception as e:
                print(f"❌ Summary generation failed: {e}")

            # Export results to CSV
            try:
                csv_path = analyzer.export_csv()
                print(f"\n✓ Strategy comparison exported to: {csv_path}")
            except Exception as e:
                print(f"⚠️ CSV export failed: {e}")

            # Export detailed results to JSON
            try:
                json_path = analyzer.export_json()
                print(f"✓ Detailed results exported to: {json_path}")
            except Exception as e:
                print(f"⚠️ JSON export failed: {e}")

            # Export individual trade logs for each strategy
            for strategy_name in strategies_list:
                try:
                    if strategy_name in analyzer.results:
                        trade_csv = analyzer.export_trades_csv(strategy_name)
                        print(f"✓ {strategy_name} trade log exported to: {trade_csv}")
                except Exception as e:
                    print(f"⚠️ Trade log export for {strategy_name} failed: {e}")

        print(f"\n{'─'*70}")
        print("✅ Headless backtest completed!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        traceback.print_exc()
        sys.exit(1)

def run_gui():
    """Run the enhanced GUI application with multi-pair and CSV support"""
    try:
        # Try enhanced GUI first
        try:
            from app.enhanced_gui import main as enhanced_main
            print("🚀 Starting Enhanced Gold Trading System GUI...\n")
            print("✨ Features: Multi-Pair Support | CSV Upload | Live Dashboard\n")
            enhanced_main()
            return
        except ImportError as enhanced_err:
            print(f"⚠️ Enhanced GUI not available: {enhanced_err}")
            print("Falling back to standard GUI...\n")
        
        # Fallback to PyQt6 GUI
        os.environ.setdefault('QT_API', 'pyqt6')

        # On macOS, prefer software rendering and enable layer flag to avoid SIGBUS in some setups
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
        # If GUI libraries are missing, fall back to headless mode instead of exiting
        if 'PyQt6' in str(e) or 'PySide6' in str(e):
            print("❌ GUI library not installed or not available:", e)
            print("Install with: pip install PyQt6 PyQt6-WebEngine (or PySide6)")
            print("Falling back to headless mode...\n")
            run_headless_backtest()
            return
        else:
            print(f"❌ Import Error: {e}")
            raise

    except Exception as e:
        # Catch high-level GUI errors and fall back to headless mode so the user can still run backtests
        print(f"\n❌ GUI Error: {e}")
        print(f"\nTraceback:\n{traceback.format_exc()}")
        print("\nFalling back to headless mode (use --headless to run headless directly).\n")
        try:
            run_headless_backtest()
        except Exception:
            print("Headless fallback failed as well. Exiting.")
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    try:
        print(f"Headless mode: {headless_mode}", flush=True)
        if headless_mode:
            run_headless_backtest()
        else:
            run_gui()
    except Exception as e:
        print(f"\n❌ Fatal error in main.py: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        print("\nFalling back to headless mode...", flush=True)
        try:
            run_headless_backtest()
        except Exception as e2:
            print(f"❌ Headless fallback also failed: {e2}", flush=True)
            print(traceback.format_exc(), flush=True)
