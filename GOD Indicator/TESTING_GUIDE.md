# 🧪 Complete Testing Guide

## Before Broker API Integration - Test Everything!

This guide helps you validate all system functionalities before connecting to Grow/Zerodha API.

---

## 🚀 Quick Start (2 minutes)

### **Option 1: Quick Test** (Recommended first)
```bash
python quick_test.py
```

This runs 6 essential tests:
1. ✅ Data fetching (yfinance)
2. ✅ EMA30 strategy
3. ✅ ICT strategy  
4. ✅ VCP strategy (NEW)
5. ✅ Backtesting engine
6. ✅ Advanced features

**Expected output:**
```
🧪 Quick System Test

1️⃣  Testing data fetching...
   ✅ Fetched 60 bars of Gold data

2️⃣  Testing EMA30 Strategy...
   ✅ Generated 12 signals

3️⃣  Testing ICT Strategy...
   ✅ Generated 8 signals

4️⃣  Testing VCP Strategy (NEW)...
   ✅ Found 3 VCP patterns in AAPL

5️⃣  Testing backtesting engine...
   ✅ Backtest complete:
      Return: 8.45%
      Win Rate: 62.5%
      Trades: 8

6️⃣  Testing advanced features...
   ✅ Market regime: trending_up

==================================================
✅ ALL QUICK TESTS PASSED!
==================================================
```

---

### **Option 2: Complete Test Suite** (10-15 minutes)
```bash
python test_complete_system.py
```

This runs 12 comprehensive tests covering every system component.

---

## 📋 Manual Testing Checklist

### **1. Test GUI (Interactive)**

```bash
python app/enhanced_gui.py
```

#### **What to test:**

**Dashboard Tab:**
- [ ] GUI loads without errors
- [ ] All 9 tabs visible
- [ ] Dashboard shows welcome message

**Backtest Tab:**
- [ ] Upload CSV or use yfinance
- [ ] Select symbol: GC=F (Gold)
- [ ] Period: 6 months
- [ ] Timeframe: 1 day
- [ ] Select strategy: EMA30
- [ ] Click "Run Backtest"
- [ ] Results display with metrics
- [ ] Chart shows equity curve

**Test All 3 Strategies:**
- [ ] EMA Strategy (Trend Following)
- [ ] ICT Strategy (Order Blocks)
- [ ] VCP Strategy (Minervini) ⭐ NEW

**Filters Tab:**
- [ ] Adjust swing lookback: 20
- [ ] Adjust ATR multiplier: 1.5
- [ ] Adjust confidence threshold: 5.0
- [ ] Settings save correctly

**Live Trading Tab:**
- [ ] Discord webhook input works
- [ ] Telegram token input works
- [ ] Risk settings adjustable
- [ ] Configuration saves

**Advanced Tabs:**
- [ ] Regime Detection tab loads
- [ ] Correlation Manager tab loads
- [ ] Multi-Timeframe tab loads
- [ ] RL Controls tab loads

---

### **2. Test Each Strategy Individually**

#### **Test EMA30 Strategy:**
```python
from backend.data_fetch_yfinance import YFinanceDataFetcher
from backend.ema_strategy import EMA30Strategy

# Fetch data
fetcher = YFinanceDataFetcher()
df = fetcher.fetch_historical_data('GC=F', period='1y', interval='1d')

# Run strategy
strategy = EMA30Strategy(fast_period=9, slow_period=30)
df_signals = strategy.generate_signals(df)

# Check signals
buy_signals = (df_signals['Signal'] == 1).sum()
sell_signals = (df_signals['Signal'] == -1).sum()

print(f"Buy signals: {buy_signals}")
print(f"Sell signals: {sell_signals}")

# Show latest signal
latest = df_signals[df_signals['Signal'] != 0].tail(1)
if not latest.empty:
    print(f"\nLatest signal:")
    print(f"  Type: {'BUY' if latest['Signal'].iloc[0] == 1 else 'SELL'}")
    print(f"  Date: {latest.index[0]}")
    print(f"  Price: ${latest['Close'].iloc[0]:.2f}")
    print(f"  Strength: {latest['Signal_Strength'].iloc[0]:.1f}/10")
```

**Expected:** 5-15 signals over 1 year

---

#### **Test ICT Strategy:**
```python
from backend.ict_strategy import ICTStrategy

# Fetch intraday data (ICT works best on lower timeframes)
df = fetcher.fetch_historical_data('GC=F', period='3mo', interval='1h')

# Run strategy
strategy = ICTStrategy(ob_lookback=20, fvg_threshold=0.5)
df_signals = strategy.generate_signals(df)

# Check signals
signals = (df_signals['Signal'] != 0).sum()
print(f"ICT signals: {signals}")

# Show latest
latest = df_signals[df_signals['Signal'] != 0].tail(1)
if not latest.empty:
    print(f"\nLatest ICT signal:")
    print(f"  Type: {'BUY' if latest['Signal'].iloc[0] == 1 else 'SELL'}")
    print(f"  Price: ${latest['Close'].iloc[0]:.2f}")
    print(f"  Strength: {latest['Signal_Strength'].iloc[0]:.1f}/10")
```

**Expected:** 10-30 signals over 3 months (hourly data)

---

#### **Test VCP Strategy:** ⭐ NEW
```python
from backend.vcp_strategy import VCPStrategy

# Use stocks for VCP (works better than commodities)
symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN']

for symbol in symbols:
    print(f"\n{'='*50}")
    print(f"Testing VCP on {symbol}")
    print('='*50)
    
    # Fetch 1 year daily data
    df = fetcher.fetch_historical_data(symbol, period='1y', interval='1d')
    
    # Run VCP strategy
    strategy = VCPStrategy(
        lookback_period=60,
        grade_a_final_contraction=0.15,
        grade_b_final_contraction=0.25
    )
    df_signals = strategy.generate_signals(df)
    
    # Find VCP patterns
    vcp_signals = df_signals[df_signals['Signal'] == 1]
    
    if len(vcp_signals) > 0:
        print(f"✅ Found {len(vcp_signals)} VCP pattern(s)!\n")
        
        for idx, row in vcp_signals.iterrows():
            grade = row['VCP_Grade']
            print(f"VCP Grade {grade} Pattern:")
            print(f"  Date: {idx}")
            print(f"  Price: ${row['Close']:.2f}")
            print(f"  Signal Strength: {row['Signal_Strength']:.1f}/10")
            print(f"  Contractions: {row['VCP_Contractions']}")
            print(f"  Prior Gain: {row['VCP_Prior_Gain']*100:.1f}%")
            print(f"  Stop Loss: ${row['Stop_Loss']:.2f}")
            print(f"  Take Profit: ${row['Take_Profit']:.2f}")
            print()
    else:
        print("⊝ No VCP patterns found (normal - patterns are rare)")
```

**Expected:** 1-5 VCP patterns across 5 stocks over 1 year

---

### **3. Test Backtesting**

```python
from backend.enhanced_backtester import EnhancedBacktester
from backend.ema_strategy import EMA30Strategy

# Fetch data
df = fetcher.fetch_historical_data('GC=F', period='2y', interval='1d')

# Generate signals
strategy = EMA30Strategy()
df_signals = strategy.generate_signals(df)

# Run backtest
backtester = EnhancedBacktester(
    initial_capital=10000,
    commission=0.001,
    slippage=0.001
)

results = backtester.run(df_signals)

# Display results
print("\n📊 Backtest Results:")
print(f"Initial Capital: ${results['initial_capital']:,.2f}")
print(f"Final Balance: ${results['final_balance']:,.2f}")
print(f"Total Return: {results['total_return']:.2f}%")
print(f"Total Trades: {results['total_trades']}")
print(f"Win Rate: {results['win_rate']:.2f}%")
print(f"Profit Factor: {results['profit_factor']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
```

**Expected metrics (EMA30 on Gold):**
- Win rate: 50-65%
- Profit factor: 1.2-2.0
- Max drawdown: 10-20%
- Sharpe ratio: 0.5-1.5

---

### **4. Test Advanced Features**

#### **Regime Detection:**
```python
from backend.market_regime_detector import MarketRegimeDetector

df = fetcher.fetch_historical_data('GC=F', period='6mo', interval='1d')

detector = MarketRegimeDetector()
regime, metrics = detector.detect_regime(df, verbose=True)

print(f"\nMarket Regime: {regime}")
print(f"Volatility: {metrics['volatility']*100:.2f}%")
print(f"Trend Strength: {metrics['trend_strength']:.2f}")

# Should we trade?
should_trade, reason = detector.should_trade(regime, 'trend_following')
print(f"\nShould trade: {should_trade}")
print(f"Reason: {reason}")
```

**Expected regimes:** trending_up, trending_down, ranging, volatile

---

#### **Multi-Timeframe Analysis:**
```python
from backend.multi_timeframe_analyzer import MultiTimeframeAnalyzer
from backend.ema_strategy import EMA30Strategy

strategy = EMA30Strategy()
analyzer = MultiTimeframeAnalyzer(
    strategy=strategy,
    timeframes=['15m', '1h', '4h']
)

result = analyzer.analyze_multi_timeframe('GC=F')

print(f"\nMulti-Timeframe Analysis:")
print(f"Final Signal: {result['final_signal']}")
print(f"Final Strength: {result['final_strength']:.1f}/10")
print(f"Timeframes Aligned: {result['timeframes_aligned']}")

print(f"\nBreakdown:")
for tf, data in result['timeframes'].items():
    print(f"  {tf}: {data['signal']} (strength: {data['strength']:.1f})")
```

**Expected:** BUY/SELL/HOLD with alignment status

---

#### **Correlation Manager:**
```python
from backend.correlation_manager import CorrelationManager

manager = CorrelationManager(lookback_days=90)

# Add related symbols
symbols = ['GC=F', 'SLV', 'GLD']
for symbol in symbols:
    manager.add_symbol(symbol)

manager.update_correlations()

# Check correlation matrix
corr_matrix = manager.get_correlation_matrix()
print("\nCorrelation Matrix:")
print(corr_matrix)

# Can we trade?
can_trade, reason = manager.can_trade_symbol('GC=F', max_correlated_exposure=0.30)
print(f"\nCan trade GC=F: {can_trade}")
print(f"Reason: {reason}")
```

**Expected:** High correlation between gold-related symbols (>0.7)

---

#### **RL System (Optional - requires PyTorch):**
```python
# Check if PyTorch available
try:
    import torch
    print(f"PyTorch {torch.__version__} installed ✅")
    
    from backend.advanced_rl_trading_system import TradingEnvironment, PPOAgent
    from backend.ema_strategy import EMA30Strategy
    
    # Quick training test
    df = fetcher.fetch_historical_data('GC=F', period='6mo', interval='1d')
    
    env = TradingEnvironment(df, strategy=EMA30Strategy())
    agent = PPOAgent(state_size=24, action_size=4)
    
    print("Training RL agent (5 episodes)...")
    rewards = agent.train(env, num_episodes=5, verbose=False)
    print(f"Average reward: {sum(rewards)/len(rewards):.2f}")
    
    # Save model
    agent.save('models/test_rl.pth')
    print("Model saved ✅")
    
except ImportError:
    print("PyTorch not installed - skip RL test")
    print("Install: pip install torch torchvision")
```

**Expected:** RL agent trains and saves model

---

### **5. Test Live Scheduler (Dry Run)**

```bash
# Create a test profile first
mkdir -p config/strategy_profiles
```

Create `config/strategy_profiles/test_ema30.yaml`:
```yaml
name: "Test_EMA30"
enabled: true

strategy:
  class: "EMA30Strategy"
  params:
    fast_period: 9
    slow_period: 30

data_source:
  type: "yfinance"
  symbol: "GC=F"
  period: "6mo"
  interval: "1h"

live:
  enabled: true
  schedule: "*/5 * * * *"  # Every 5 minutes (for testing)
  confidence_threshold: 6.0
  cooldown_minutes: 60
  risk_per_trade_percent: 1.0
  alert_channels: ["test"]
```

Then test:
```python
from backend.live_scheduler import LiveScheduler

# Initialize
scheduler = LiveScheduler()

# Load profiles
scheduler.load_profiles('config/strategy_profiles')
print(f"Loaded {len(scheduler.strategy_profiles)} profiles")

# Don't start (would run indefinitely)
# Just verify it initializes correctly
print("✅ Scheduler ready for live trading")
```

**Expected:** Profile loads without errors

---

### **6. Test Discord Webhook (Optional)**

If you have Discord webhook URL:

```python
from backend.tradingview_webhook import DiscordWebhook

webhook = DiscordWebhook(webhook_url="YOUR_WEBHOOK_URL")

# Send test signal
webhook.send_signal(
    symbol="TEST",
    direction="BUY",
    strategy="VCP",
    entry_price=100.00,
    signal_strength=9.0,
    stop_loss=95.00,
    take_profit=110.00,
    timeframe="1D"
)

print("✅ Test signal sent to Discord")
```

**Expected:** Message appears in Discord channel

---

## 📊 Test Results Checklist

After running all tests, verify:

### **Core Features**
- [ ] ✅ Data fetching works (yfinance)
- [ ] ✅ EMA30 strategy generates signals
- [ ] ✅ ICT strategy generates signals
- [ ] ✅ VCP strategy detects patterns (NEW)
- [ ] ✅ Backtesting produces results
- [ ] ✅ GUI launches and works

### **Advanced Features**
- [ ] ✅ Regime detection identifies market state
- [ ] ✅ Multi-timeframe analysis aligns signals
- [ ] ✅ Correlation manager tracks relationships
- [ ] ✅ RL system trains (if PyTorch installed)

### **Integration Features**
- [ ] ✅ Live scheduler loads profiles
- [ ] ✅ Discord webhook ready (if configured)
- [ ] ✅ Configuration management works

---

## 🐛 Common Issues & Fixes

### **Issue: "Module not found"**
```bash
pip install -r requirements.txt
```

### **Issue: "No module named 'torch'"**
RL features require PyTorch (optional):
```bash
pip install torch torchvision
```

### **Issue: "No VCP patterns found"**
Normal! VCP patterns are rare. Try:
- Test on multiple stocks (AAPL, MSFT, NVDA)
- Use 1-2 years of daily data
- Patterns appear in bull markets

### **Issue: "Backtest returns are negative"**
- Try different parameters in Filters tab
- Test different timeframes
- Some periods may be unfavorable

### **Issue: "GUI won't launch"**
```bash
pip install PySide6
```

---

## ✅ Ready for Broker API?

Once all tests pass, you're ready to integrate Grow/Zerodha API:

**Pre-integration checklist:**
- [ ] All 12 tests pass in `test_complete_system.py`
- [ ] GUI works correctly
- [ ] All 3 strategies tested
- [ ] Backtest results are reasonable
- [ ] Discord webhook tested (optional)
- [ ] Documentation reviewed

**Next steps:**
1. Get broker API credentials
2. Implement `backend/data_fetch_broker.py`
3. Update `backend/live_scheduler.py` to use broker data
4. Test with live data (paper trading)
5. Go live!

---

## 🚀 Running Tests

### **Quick (2 min):**
```bash
python quick_test.py
```

### **Complete (15 min):**
```bash
python test_complete_system.py
```

### **GUI Test:**
```bash
python app/enhanced_gui.py
```

### **Individual Strategy Test:**
```bash
python -c "
from backend.vcp_strategy import VCPStrategy
from backend.data_fetch_yfinance import YFinanceDataFetcher

fetcher = YFinanceDataFetcher()
df = fetcher.fetch_historical_data('AAPL', period='1y', interval='1d')

vcp = VCPStrategy()
signals = vcp.generate_signals(df)
patterns = (signals['Signal'] == 1).sum()

print(f'VCP patterns found: {patterns}')
"
```

---

**Your system is ready for testing! Start with `python quick_test.py` 🧪✨**
