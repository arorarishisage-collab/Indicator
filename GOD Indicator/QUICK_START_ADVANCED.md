# Quick Start Guide - Advanced Trading System

## What's New

You now have a complete advanced trading system with:

✅ **Free Data** - yFinance API for XAUUSD and Bitcoin  
✅ **ICT Strategy** - Full implementation of order blocks, liquidity voids, supply/demand zones  
✅ **Dummy Trading** - Paper trading simulator with P&L tracking  
✅ **Parameter Optimization** - Automatic hit-and-trial to find best parameters  
✅ **TradingView Webhooks** - Send signals to TradingView via webhooks  
✅ **24/7 Scheduler** - Background daemon for continuous operation  

## 5-Minute Quick Start

### 1. Install Dependencies

```bash
pip install yfinance pandas numpy requests schedule
```

### 2. Test Data Fetching

```python
from backend.data_fetch_yfinance import YFinanceDataFetcher

fetcher = YFinanceDataFetcher()
df = fetcher.fetch_historical_data('XAUUSD', period='1y', interval='1d')
print(f"✓ Fetched {len(df)} bars of XAUUSD")
```

### 3. Test ICT Strategy

```python
from backend.ict_strategy import ICTStrategy

strategy = ICTStrategy()
df_signals = strategy.generate_signals(df)
print(f"✓ Generated {(df_signals['Signal'] != 0).sum()} signals")
print(df_signals[['Close', 'Signal', 'Signal_Strength']].tail(10))
```

### 4. Test Dummy Trader

```python
from backend.live_dummy_trader import LiveDummyTrader
from datetime import datetime

trader = LiveDummyTrader(symbol='XAUUSD')

# Simulate a winning trade
trade = trader.execute_trade(
    entry_price=2000,
    entry_time=datetime.now(),
    direction=1,
    strategy='ICTStrategy',
    signal_strength=7.5
)
trader.close_trade(trade.trade_id, exit_price=2010, exit_time=datetime.now())

# Show results
print(trader.get_performance_summary())
```

### 5. Run Parameter Optimization

```python
from backend.parameter_optimizer import ParameterOptimizer

optimizer = ParameterOptimizer(ICTStrategy, optimization_metric='win_rate')
results = optimizer.optimize(df, verbose=True)
optimizer.print_results(top_n=5)
```

### 6. Start 24/7 Scheduler

```python
from backend.live_scheduler import LiveTradingScheduler
from backend.data_fetch_yfinance import YFinanceDataFetcher
from backend.ict_strategy import ICTStrategy

scheduler = LiveTradingScheduler(
    symbols=['XAUUSD', 'BTC'],
    check_interval_minutes=60,
    data_fetcher_class=YFinanceDataFetcher,
    strategy_classes={'ICTStrategy': ICTStrategy}
)

scheduler.start()
print("✓ Scheduler running 24/7 in background!")
```

## File Organization

```
backend/
├── data_fetch_yfinance.py      # ✨ NEW: Free data fetcher
├── ict_strategy.py             # ✨ NEW: Full ICT implementation
├── live_dummy_trader.py        # ✨ NEW: Paper trading simulator
├── parameter_optimizer.py      # ✨ NEW: Hit-and-trial optimization
├── tradingview_webhook.py      # ✨ NEW: TradingView integration
├── live_scheduler.py           # ✨ NEW: 24/7 background daemon
└── (existing files...)

config/
├── webhooks.json               # ✨ NEW: Webhook configuration
└── scheduler_config.json       # ✨ NEW: Scheduler settings

reports/
├── dummy_trades.json           # ✨ NEW: Trade history
├── optimization_results.json   # ✨ NEW: Optimization results
└── trading_log.db              # ✨ NEW: Trade database

data/
└── signal_history_YYYYMMDD.json # ✨ NEW: Daily signal history
```

## Module Capabilities

### YFinance Data Fetcher
```
✓ Fetch any timeframe (1m, 5m, 1h, 1d, 1w, 1mo)
✓ Fetch any duration (1d, 1mo, 1y, 5y, 10y)
✓ Add technical indicators (SMA, EMA, RSI, MACD, ATR, BB)
✓ Fetch live candles for real-time trading
✓ Support XAUUSD, Bitcoin, Ethereum, Forex pairs
```

### ICT Strategy
```
✓ Order Blocks (Bullish/Bearish)
✓ Fair Value Gaps (Bullish/Bearish)
✓ Liquidity Voids
✓ Supply/Demand Zones
✓ Break of Structure (Bullish/Bearish)
✓ Multi-element signal confirmation
✓ Signal strength 0-10
```

### Dummy Trader
```
✓ Execute paper trades
✓ Track P&L per trade
✓ Calculate win rate, profit factor
✓ Calculate Sharpe ratio, max drawdown
✓ Store in SQLite database
✓ Export to JSON
✓ Performance summary report
```

### Parameter Optimizer
```
✓ Grid search all parameter combinations
✓ Rank by win rate, profit factor, Sharpe ratio, return
✓ Support any strategy
✓ Export results to JSON
✓ Show top N results
```

### TradingView Webhooks
```
✓ Standard alert format for Pine Script
✓ Send to Slack, Discord, email, custom webhooks
✓ Signal debouncing (5-minute minimum)
✓ Bulk signal sending
✓ Configuration management
```

### Live Scheduler
```
✓ 24/7 background operation
✓ Configurable check intervals (hourly, 4-hourly, daily)
✓ Multi-symbol monitoring
✓ Automatic signal generation
✓ Dummy trade execution
✓ Daily parameter optimization
✓ Daily performance reporting
✓ Mac-compatible daemon mode
```

## Configuration Examples

### Setup Webhook for Slack

1. Create Slack Webhook:
   - Go to https://api.slack.com/apps
   - Create New App → From scratch
   - Enable Incoming Webhooks
   - Copy Webhook URL

2. Add to config:
```python
from backend.tradingview_webhook import WebhookConfig

config = WebhookConfig()
config.add_webhook(
    name='slack_alerts',
    url='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
)
```

### Setup Webhook for Discord

1. Create Discord Webhook:
   - Server Settings → Integrations → Webhooks
   - Create New Webhook
   - Copy Webhook URL

2. Add to config:
```python
config.add_webhook(
    name='discord_alerts',
    url='https://discordapp.com/api/webhooks/YOUR/WEBHOOK'
)
```

## Real-World Usage Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SETUP (Once)                                             │
├─────────────────────────────────────────────────────────────┤
│ • Install dependencies                                       │
│ • Configure webhooks (Slack, Discord, etc.)                │
│ • Run parameter optimization on 5-10 years data             │
│ • Note best parameters                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. RUN 24/7 (Background)                                   │
├─────────────────────────────────────────────────────────────┤
│ • Start scheduler with optimized parameters                 │
│ • Every hour: Check for new signals                         │
│ • Every signal: Execute dummy trade                         │
│ • Send to TradingView via webhooks                         │
│ • Track performance in real-time                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. MONITOR (Daily)                                          │
├─────────────────────────────────────────────────────────────┤
│ • View live trading performance                             │
│ • Check P&L, win rate, signal quality                      │
│ • Review daily performance report                           │
│ • Adjust parameters if needed                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. OPTIMIZE (Daily)                                         │
├─────────────────────────────────────────────────────────────┤
│ • System automatically optimizes parameters at 2 AM         │
│ • Test new combinations against recent data                 │
│ • Update strategy with best performers                      │
│ • Adapt to changing market conditions                       │
└─────────────────────────────────────────────────────────────┘
```

## Performance Metrics Explained

### Win Rate
- Percentage of profitable trades
- Target: 50%+ (break-even is good, 60%+ is excellent)

### Profit Factor
- Total wins ÷ Total losses
- Target: >1.5x (means earning $1.50 for every $1 lost)

### Sharpe Ratio
- Risk-adjusted returns (reward per unit of risk)
- Target: >2.0 (higher is better)

### Max Drawdown
- Largest peak-to-trough decline
- Target: <20% (your capital never drops more than 20%)

### Return %
- Total profit as percentage of initial capital
- Example: 50% = $5,000 profit on $10,000 capital

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "No module named yfinance" | `pip install yfinance` |
| "No data returned" | Check internet, try different period |
| Signals too frequent | Increase `check_interval_minutes` |
| Optimization takes forever | Reduce parameter grid size |
| Webhook not sending | Check webhook URL, verify enabled in config |
| Scheduler not running | Check logs, verify strategies return signals |

## Next: EMA 30 Strategy

Your next task is explaining the EMA 30 strategy! Provide:

1. **Entry Conditions** - When to buy/sell?
2. **Exit Conditions** - When to close?
3. **Timeframe** - What candle size? (1H, 4H, 1D?)
4. **Risk Rules** - Stop loss, take profit?
5. **Parameters** - Which EMAs? Thresholds?

Example:
```
LONG ENTRY:
- EMA 9 crosses above EMA 30
- Price above EMA 50 (uptrend)
- Volume > average

LONG EXIT:
- EMA 9 crosses below EMA 30
- Stop loss -2%
- Take profit +3%
```

Once provided, I'll implement it with full optimization and integration! 🚀

## Support Resources

- **Documentation**: See `ADVANCED_SYSTEM_DOCUMENTATION.md`
- **Integration Guide**: See `INTEGRATION_GUIDE.md`
- **Code Examples**: In each module's `__main__` section
- **Logs**: Check `/tmp/tradingsystem.log` for scheduler logs
- **Database**: `sqlite3 reports/trading_log.db` to query trades
