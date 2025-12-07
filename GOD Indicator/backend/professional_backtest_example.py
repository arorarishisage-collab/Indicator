"""
Professional Backtesting Example
Demonstrates 4-step methodology:
1. 📊 Data Acquisition
2. 📝 Strategy Implementation  
3. 🧪 Backtesting
4. 📈 Performance Analysis
"""

import sys
import pandas as pd
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from data_manager import DataManager
from technical_indicators import TechnicalIndicators
from professional_backtester import ProfessionalBacktester, BacktestConfig
from performance_metrics import PerformanceAnalyzer, StrategyComparator
from strategies import MovingAverageCrossover, RSIOversoldStrategy


def example_professional_backtest():
    """
    Complete 4-step professional backtesting workflow
    """
    
    print("\n" + "=" * 80)
    print("PROFESSIONAL BACKTESTING WORKFLOW - 4-STEP METHODOLOGY")
    print("=" * 80)
    
    # ========== STEP 1: DATA ACQUISITION ==========
    print("\n📊 STEP 1: DATA ACQUISITION")
    print("-" * 80)
    
    data_manager = DataManager(use_cache=True)
    
    # Fetch historical data for an NSE stock
    print("Downloading historical data for RELIANCE.NS (1 year daily)...")
    df = data_manager.fetch_historical_data(
        symbol='RELIANCE',
        start_date='2023-01-01',
        end_date='2024-01-01',
        timeframe='1d',
        is_nse=True
    )
    
    if df.empty:
        print("Error: Could not fetch data. Using sample data...")
        # Generate sample data
        df = generate_sample_data()
    
    # Validate data
    is_valid, message = data_manager.validate_data(df)
    print(f"Data validation: {message}")
    
    if not is_valid:
        print("Invalid data! Exiting...")
        return
    
    print(f"✓ Loaded {len(df)} bars of data")
    print(f"  Date range: {df['DateTime'].min()} to {df['DateTime'].max()}")
    print(f"  Price range: ₹{df['Low'].min():.2f} - ₹{df['High'].max():.2f}")
    
    # ========== STEP 2: STRATEGY IMPLEMENTATION ==========
    print("\n📝 STEP 2: STRATEGY IMPLEMENTATION")
    print("-" * 80)
    
    # Add technical indicators
    print("Calculating technical indicators...")
    
    indicators_config = {
        'SMA_20': {'type': 'sma', 'period': 20},
        'SMA_50': {'type': 'sma', 'period': 50},
        'RSI_14': {'type': 'rsi', 'period': 14},
        'MACD': {'type': 'macd'},
        'BB_20': {'type': 'bollinger_bands', 'period': 20},
        'ATR_14': {'type': 'atr', 'period': 14},
    }
    
    df = TechnicalIndicators.calculate_indicators(df, indicators_config)
    print("✓ Technical indicators calculated")
    
    # Generate trading signals using Moving Average Crossover strategy
    print("Generating trading signals (MA Crossover: SMA 20 > SMA 50)...")
    
    signals = pd.Series(0, index=range(len(df)))
    
    # Signal: 1 when SMA20 > SMA50, -1 when SMA20 < SMA50
    signals[df['SMA_20'] > df['SMA_50']] = 1
    signals[df['SMA_20'] < df['SMA_50']] = -1
    
    # Generate buy/sell signals (transition based)
    buy_signals = []
    for i in range(1, len(signals)):
        if signals.iloc[i] == 1 and signals.iloc[i-1] != 1:
            buy_signals.append(i)
        elif signals.iloc[i] == -1 and signals.iloc[i-1] != -1:
            buy_signals.append(i)
    
    print(f"✓ Generated {len(buy_signals)} trading signals")
    
    # ========== STEP 3: BACKTESTING ==========
    print("\n🧪 STEP 3: BACKTESTING (STEP 3 OF 4)")
    print("-" * 80)
    
    # Configure backtester with realistic parameters
    config = BacktestConfig(
        initial_capital=100000,  # ₹1,00,000
        commission=0.001,  # 0.1% per trade
        slippage=0.0005,  # 0.05% slippage
        position_size_percent=0.95,  # Use 95% of capital
        use_atr_stop_loss=True,
        atr_multiplier=2.0,
    )
    
    print(f"Backtest Configuration:")
    print(f"  Initial Capital: ₹{config.initial_capital:,.0f}")
    print(f"  Commission: {config.commission*100:.2f}%")
    print(f"  Slippage: {config.slippage*100:.2f}%")
    print(f"  Position Size: {config.position_size_percent*100:.0f}% of capital")
    print()
    
    # Run backtest
    backtester = ProfessionalBacktester(config)
    result = backtester.backtest(df, signals)
    
    # ========== STEP 4: PERFORMANCE ANALYSIS ==========
    print("\n📈 STEP 4: PERFORMANCE ANALYSIS")
    print("-" * 80)
    
    analyzer = PerformanceAnalyzer(initial_capital=config.initial_capital)
    
    # Generate comprehensive report
    report = analyzer.generate_report(result)
    print(report)
    
    # Export results
    print("\nExporting results...")
    
    trades_df = result.get_trades_dataframe()
    trades_df.to_csv('reports/trades_ma_crossover.csv', index=False)
    print("✓ Trades exported: reports/trades_ma_crossover.csv")
    
    equity_df = result.get_equity_dataframe()
    equity_df.to_csv('reports/equity_curve_ma_crossover.csv', index=False)
    print("✓ Equity curve exported: reports/equity_curve_ma_crossover.csv")
    
    analyzer.export_to_json(result, 'reports/metrics_ma_crossover.json')
    print("✓ Metrics exported: reports/metrics_ma_crossover.json")
    
    return df, result, analyzer


def example_strategy_comparison():
    """
    Compare performance of multiple strategies
    """
    
    print("\n" + "=" * 80)
    print("STRATEGY COMPARISON - BACKTESTING MULTIPLE APPROACHES")
    print("=" * 80)
    
    data_manager = DataManager(use_cache=True)
    
    # Fetch data
    print("\nFetching data for comparison...")
    df = data_manager.fetch_historical_data(
        symbol='INFOSY',
        start_date='2023-01-01',
        end_date='2024-01-01',
        timeframe='1d',
        is_nse=True
    )
    
    if df.empty:
        df = generate_sample_data()
    
    # Calculate indicators once
    indicators_config = {
        'SMA_20': {'type': 'sma', 'period': 20},
        'SMA_50': {'type': 'sma', 'period': 50},
        'RSI_14': {'type': 'rsi', 'period': 14},
        'MACD': {'type': 'macd'},
    }
    
    df = TechnicalIndicators.calculate_indicators(df, indicators_config)
    
    # Backtest config
    config = BacktestConfig(initial_capital=100000)
    backtester = ProfessionalBacktester(config)
    analyzer = PerformanceAnalyzer()
    
    results = {}
    
    # Strategy 1: MA Crossover
    print("\n1. Testing MA Crossover Strategy...")
    signals_ma = pd.Series(0, index=range(len(df)))
    signals_ma[df['SMA_20'] > df['SMA_50']] = 1
    signals_ma[df['SMA_20'] < df['SMA_50']] = -1
    
    result_ma = backtester.backtest(df, signals_ma)
    metrics_ma = analyzer.analyze(result_ma)
    results['MA Crossover'] = metrics_ma
    
    # Strategy 2: RSI Overbought/Oversold
    print("\n2. Testing RSI Overbought/Oversold Strategy...")
    signals_rsi = pd.Series(0, index=range(len(df)))
    signals_rsi[df['RSI_14'] > 70] = -1  # Overbought = Sell
    signals_rsi[df['RSI_14'] < 30] = 1   # Oversold = Buy
    
    result_rsi = backtester.backtest(df, signals_rsi)
    metrics_rsi = analyzer.analyze(result_rsi)
    results['RSI Overbought/Oversold'] = metrics_rsi
    
    # Strategy 3: MACD
    print("\n3. Testing MACD Strategy...")
    signals_macd = pd.Series(0, index=range(len(df)))
    signals_macd[df['MACD_Line'] > df['Signal_Line']] = 1
    signals_macd[df['MACD_Line'] < df['Signal_Line']] = -1
    
    result_macd = backtester.backtest(df, signals_macd)
    metrics_macd = analyzer.analyze(result_macd)
    results['MACD'] = metrics_macd
    
    # Compare strategies
    print("\n" + "=" * 80)
    print("STRATEGY COMPARISON RESULTS")
    print("=" * 80)
    
    comparison = StrategyComparator.compare(results)
    print("\nRanked by Return:")
    print(comparison.to_string(index=False))
    
    ranking = StrategyComparator.rank_strategies(results)
    print("\n\nOverall Rankings (Weighted Scoring):")
    print(ranking.to_string(index=False))
    
    return results


def example_live_monitoring():
    """
    Demonstrate live market data monitoring
    """
    
    print("\n" + "=" * 80)
    print("LIVE MARKET DATA MONITORING")
    print("=" * 80)
    
    from live_data_fetcher import LiveDataFetcher, RealTimeSignalGenerator
    
    # Initialize live data fetcher
    fetcher = LiveDataFetcher(refresh_interval=60)
    
    # Watch specific symbols
    print("\nWatching market for live data...")
    symbols_to_watch = ['RELIANCE', 'TCS', 'INFOSY']
    
    for symbol in symbols_to_watch:
        live_data = fetcher.watch_symbol(symbol, is_nse=True)
        if live_data:
            print(f"✓ {symbol}: ₹{live_data['current_price']:.2f} "
                  f"({live_data['change_percent']:+.2f}%)")
    
    # Set price alerts
    print("\nSetting price alerts...")
    fetcher.set_price_alert('RELIANCE.NS', price_target=2700, alert_type='above')
    fetcher.set_price_alert('TCS.NS', price_target=3500, alert_type='above')
    
    # Get market summary
    print("\nMarket Summary:")
    summary = fetcher.get_market_summary()
    if not summary.empty:
        print(summary.to_string(index=False))
    
    # Generate signals
    signal_gen = RealTimeSignalGenerator(fetcher)
    signals = signal_gen.check_signals()
    if signals:
        print("\nGenerated Signals:")
        for symbol, signal in signals.items():
            print(f"  {symbol}: {signal}")
    
    # Export live data
    fetcher.export_live_data('reports/live_market_data.csv')
    print("\n✓ Live data exported: reports/live_market_data.csv")


def generate_sample_data(periods=252):
    """Generate sample OHLCV data for testing"""
    import numpy as np
    from datetime import datetime, timedelta
    
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


if __name__ == '__main__':
    
    try:
        # Run 4-step professional backtesting
        example_professional_backtest()
        
        # Compare multiple strategies
        example_strategy_comparison()
        
        # Monitor live market data (comment out if no internet/yfinance)
        # example_live_monitoring()
        
        print("\n" + "=" * 80)
        print("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nKey Outcomes:")
        print("  1. ✓ Data acquired from yfinance with caching")
        print("  2. ✓ Technical indicators calculated professionally")
        print("  3. ✓ Backtesting with realistic execution (commissions, slippage)")
        print("  4. ✓ Performance analyzed with 20+ metrics")
        print("  5. ✓ Multiple strategies compared and ranked")
        print("  6. ✓ Results exported to CSV and JSON")
        print("\nAll reports saved to: reports/")
        print("=" * 80 + "\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
