"""
Complete Integration Example: ICT + EMA 30 Strategies with Live Trading
Demonstrates how to run both strategies simultaneously with parameter optimization
"""

import logging
from datetime import datetime
from pathlib import Path

# Import all components
from data_fetch_yfinance import YFinanceDataFetcher
from ict_strategy import ICTStrategy
from ema_strategy import EMA30Strategy
from parameter_optimizer import ParameterOptimizer
from live_dummy_trader import LiveDummyTrader
from tradingview_webhook import TradingViewWebhook, WebhookConfig
from live_scheduler import LiveTradingScheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_standalone_strategies():
    """
    Example 1: Run both strategies independently on historical data
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Standalone Strategy Testing (Historical Data)")
    print("="*80 + "\n")
    
    # Fetch historical data
    fetcher = YFinanceDataFetcher()
    df = fetcher.fetch_historical_data('XAUUSD', period='5y', interval='1d')
    print(f"✓ Loaded {len(df)} bars of XAUUSD data")
    
    # Test ICT Strategy
    print("\n1️⃣  Testing ICT Strategy...")
    ict_strategy = ICTStrategy(lookback_period=200, fvg_threshold=0.0005, ob_threshold=2)
    df_ict = ict_strategy.generate_signals(df.copy())
    
    ict_buys = (df_ict['Signal'] == 1).sum()
    ict_sells = (df_ict['Signal'] == -1).sum()
    print(f"   ICT Signals: {ict_buys} buys, {ict_sells} sells")
    
    # Show sample ICT signals
    ict_signals = df_ict[df_ict['Signal'] != 0].tail(3)
    print(f"\n   Last 3 ICT signals:")
    for idx, row in ict_signals.iterrows():
        direction = "🟢 BUY" if row['Signal'] == 1 else "🔴 SELL"
        print(f"   {idx.strftime('%Y-%m-%d')}: {direction} @ {row['Close']:.2f} (strength: {row['Signal_Strength']:.1f}/10)")
    
    # Test EMA 30 Strategy
    print("\n2️⃣  Testing EMA 30 Strategy...")
    ema_strategy = EMA30Strategy(fast_period=9, slow_period=30, rsi_period=14)
    df_ema = ema_strategy.generate_signals(df.copy())
    
    ema_buys = (df_ema['Signal'] == 1).sum()
    ema_sells = (df_ema['Signal'] == -1).sum()
    print(f"   EMA 30 Signals: {ema_buys} buys, {ema_sells} sells")
    
    # Show sample EMA 30 signals
    ema_signals = df_ema[df_ema['Signal'] != 0].tail(3)
    print(f"\n   Last 3 EMA 30 signals:")
    for idx, row in ema_signals.iterrows():
        direction = "🟢 BUY" if row['Signal'] == 1 else "🔴 SELL"
        print(f"   {idx.strftime('%Y-%m-%d')}: {direction} @ {row['Close']:.2f} (strength: {row['Signal_Strength']:.1f}/10)")
    
    # Compare strategies
    print("\n📊 Strategy Comparison:")
    print(f"   ICT:    {ict_buys + ict_sells} total signals")
    print(f"   EMA 30: {ema_buys + ema_sells} total signals")


def example_parameter_optimization():
    """
    Example 2: Optimize both strategies using grid search (hit-and-trial)
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Parameter Optimization (Hit-and-Trial Grid Search)")
    print("="*80 + "\n")
    
    # Fetch data
    fetcher = YFinanceDataFetcher()
    df = fetcher.fetch_historical_data('XAUUSD', period='2y', interval='1d')
    print(f"✓ Loaded {len(df)} bars for optimization")
    
    # Optimize ICT Strategy
    print("\n1️⃣  Optimizing ICT Strategy Parameters...")
    ict_optimizer = ParameterOptimizer(
        strategy_class=ICTStrategy,
        optimization_metric='profit_factor'
    )
    ict_results = ict_optimizer.optimize(df, verbose=True)
    
    print(f"\n✓ Top 3 ICT Parameter Sets:")
    for i, result in enumerate(ict_results[:3], 1):
        params = result['params']
        metrics = result['metrics']
        print(f"\n   #{i}: Win Rate: {metrics['win_rate']:.1f}%, Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"       Params: {params}")
    
    # Optimize EMA 30 Strategy
    print("\n2️⃣  Optimizing EMA 30 Strategy Parameters...")
    ema_optimizer = ParameterOptimizer(
        strategy_class=EMA30Strategy,
        optimization_metric='sharpe_ratio'
    )
    ema_results = ema_optimizer.optimize(df, verbose=True)
    
    print(f"\n✓ Top 3 EMA 30 Parameter Sets:")
    for i, result in enumerate(ema_results[:3], 1):
        params = result['params']
        metrics = result['metrics']
        print(f"\n   #{i}: Win Rate: {metrics['win_rate']:.1f}%, Sharpe: {metrics['sharpe_ratio']:.2f}")
        print(f"       Params: {params}")


def example_dummy_trading():
    """
    Example 3: Simulate trading with both strategies using dummy trader
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Dummy Trading Simulation (Paper Trading)")
    print("="*80 + "\n")
    
    # Setup dummy trader
    dummy_trader = LiveDummyTrader(initial_capital=10000)
    print(f"✓ Initialized dummy trader with $10,000 capital")
    
    # Fetch data for simulation
    fetcher = YFinanceDataFetcher()
    df = fetcher.fetch_historical_data('XAUUSD', period='1y', interval='1h')
    print(f"✓ Loaded {len(df)} hourly bars for simulation")
    
    # Get best parameters from optimization
    ict_optimizer = ParameterOptimizer(ICTStrategy, 'profit_factor')
    ict_results = ict_optimizer.optimize(df[:500])  # Quick optimization on subset
    best_ict_params = ict_results[0]['params'] if ict_results else {}
    
    ema_optimizer = ParameterOptimizer(EMA30Strategy, 'sharpe_ratio')
    ema_results = ema_optimizer.optimize(df[:500])
    best_ema_params = ema_results[0]['params'] if ema_results else {}
    
    print(f"\n✓ Using best parameters from optimization")
    
    # Simulate trades
    print(f"\n📊 Simulating trades on {len(df)} bars...\n")
    
    # Process data and execute trades based on both strategies
    for i in range(500, len(df)):
        window = df.iloc[max(0, i-500):i]
        
        # ICT signals
        ict = ICTStrategy(**best_ict_params)
        df_ict = ict.generate_signals(window.copy())
        signal_ict = df_ict.iloc[-1]['Signal'] if len(df_ict) > 0 else 0
        strength_ict = df_ict.iloc[-1].get('Signal_Strength', 0) if len(df_ict) > 0 else 0
        
        # EMA signals
        ema = EMA30Strategy(**best_ema_params)
        df_ema = ema.generate_signals(window.copy())
        signal_ema = df_ema.iloc[-1]['Signal'] if len(df_ema) > 0 else 0
        strength_ema = df_ema.iloc[-1].get('Signal_Strength', 0) if len(df_ema) > 0 else 0
        
        # Multi-strategy fusion: Only trade if both agree
        if signal_ict == signal_ema and signal_ict != 0:
            direction = 'BUY' if signal_ict == 1 else 'SELL'
            strength = (strength_ict + strength_ema) / 2
            
            # Execute trade
            if len(dummy_trader.open_trades) < 3:  # Limit concurrent trades
                dummy_trader.execute_trade(
                    symbol='XAUUSD',
                    direction=signal_ict,
                    entry_price=df.iloc[i]['Close'],
                    stop_loss=df.iloc[i]['Close'] * (0.98 if signal_ict == 1 else 1.02),
                    take_profit=df.iloc[i]['Close'] * (1.02 if signal_ict == 1 else 0.98),
                    signal_strength=strength,
                    strategy=f'ICT+EMA30'
                )
        
        # Close trades based on take profit / stop loss
        for trade_id in list(dummy_trader.open_trades.keys()):
            trade = dummy_trader.open_trades[trade_id]
            current_price = df.iloc[i]['Close']
            
            # Check stop loss / take profit
            if trade['direction'] == 1 and current_price <= trade['stop_loss']:
                dummy_trader.close_trade(trade_id, current_price)
            elif trade['direction'] == 1 and current_price >= trade['take_profit']:
                dummy_trader.close_trade(trade_id, current_price)
            elif trade['direction'] == -1 and current_price >= trade['stop_loss']:
                dummy_trader.close_trade(trade_id, current_price)
            elif trade['direction'] == -1 and current_price <= trade['take_profit']:
                dummy_trader.close_trade(trade_id, current_price)
    
    # Print results
    print("\n📈 Trading Results:")
    summary = dummy_trader.get_performance_summary()
    print(summary)


def example_live_scheduler():
    """
    Example 4: Run live trading scheduler with both strategies
    This would run 24/7 in background
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Live Trading Scheduler (24/7 Operation)")
    print("="*80 + "\n")
    
    # Setup webhook configuration
    webhook_config = WebhookConfig()
    webhook_config.add_webhook('main', 'https://hooks.slack.com/services/YOUR_WEBHOOK_URL')
    webhook_config.add_webhook('discord', 'https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN')
    
    print("✓ Webhook configuration setup (Slack, Discord)")
    
    # Setup dummy trader
    dummy_trader = LiveDummyTrader(initial_capital=10000)
    print(f"✓ Dummy trader initialized with $10,000")
    
    # Setup strategies to run
    strategy_classes = {
        'ICTStrategy': ICTStrategy,
        'EMA30Strategy': EMA30Strategy,
    }
    print(f"✓ Configured strategies: {', '.join(strategy_classes.keys())}")
    
    # Create scheduler
    scheduler = LiveTradingScheduler(
        symbols=['XAUUSD', 'BTC'],
        check_interval_minutes=60,  # Check every hour
        data_fetcher_class=YFinanceDataFetcher,
        strategy_classes=strategy_classes,
        webhook_config=webhook_config,
        dummy_trader=dummy_trader
    )
    
    print(f"\n✓ Scheduler configured:")
    print(f"  - Symbols: {', '.join(scheduler.symbols)}")
    print(f"  - Check interval: {scheduler.check_interval_minutes} minutes")
    print(f"  - Daily optimization: 2:00 AM")
    print(f"  - Daily reporting: 9:00 AM")
    
    print(f"\n⚠️  NOTE: To start live trading, call:")
    print(f"    scheduler.start()")
    print(f"\n   This will:")
    print(f"   - Check {scheduler.symbols} every {scheduler.check_interval_minutes} minutes")
    print(f"   - Run both ICT and EMA 30 strategies")
    print(f"   - Send signals to webhooks")
    print(f"   - Execute and track dummy trades")
    print(f"   - Optimize parameters daily at 2 AM")
    print(f"   - Generate performance report daily at 9 AM")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 COMPLETE INTEGRATION EXAMPLES: ICT + EMA 30 STRATEGIES")
    print("="*80)
    
    try:
        # Example 1: Standalone testing
        example_standalone_strategies()
        
        # Example 2: Parameter optimization
        example_parameter_optimization()
        
        # Example 3: Dummy trading simulation
        example_dummy_trading()
        
        # Example 4: Live scheduler setup
        example_live_scheduler()
        
        print("\n" + "="*80)
        print("✅ All examples completed successfully!")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error in examples: {e}")
        import traceback
        traceback.print_exc()
