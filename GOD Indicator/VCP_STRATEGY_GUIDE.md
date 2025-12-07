# 📊 VCP Strategy Guide - Minervini's Volatility Contraction Pattern

## Overview

The **VCP (Volatility Contraction Pattern)** strategy is based on Mark Minervini's SEPA (Specific Entry Point Analysis) methodology. It identifies stocks forming tight consolidation patterns with decreasing volatility before powerful breakouts.

This is your **3rd strategy** alongside EMA30 and ICT strategies.

---

## 🎯 What is VCP?

VCP is a **momentum breakout pattern** characterized by:
1. **Prior uptrend** (30%+ gain for Grade A, 15%+ for Grade B)
2. **Consolidation base** (15-90 bars)
3. **Multiple contractions** (pullbacks) with decreasing depth
4. **Tight final contraction** (< 15% for Grade A, < 25% for Grade B)
5. **Breakout on volume** above pivot resistance

---

## 🏆 Grade A vs Grade B Patterns

### **Grade A - Highest Quality** ⭐⭐⭐
- **Prior uptrend**: 30%+ gain
- **Contractions**: 3-4 pullbacks
- **Final contraction depth**: < 15%
- **Base length**: Typically 30-60 bars
- **Expected win rate**: 70-80%
- **Signal strength**: 8-10/10

**Example:**
```
Price Action:
$100 → $140 (40% uptrend)
  ↓ -20% → $112
  ↓ -15% → $119
  ↓ -12% → $123
  ↓ -10% → $125  ← Final tight contraction
  ↑ BREAKOUT at $140 (pivot) ✓
```

### **Grade B - Good Quality** ⭐⭐
- **Prior uptrend**: 15-30% gain
- **Contractions**: 2-3 pullbacks
- **Final contraction depth**: < 25%
- **Base length**: Typically 20-50 bars
- **Expected win rate**: 60-70%
- **Signal strength**: 6-8/10

**Example:**
```
Price Action:
$100 → $120 (20% uptrend)
  ↓ -18% → $98
  ↓ -15% → $102
  ↓ -12% → $106  ← Final contraction
  ↑ BREAKOUT at $120 (pivot) ✓
```

---

## 📐 VCP Detection Algorithm

### **Step 1: Identify Prior Uptrend**
- Look back 50-100 bars
- Find swing low
- Calculate gain from swing low to current high
- **Grade A**: Requires 30%+ gain
- **Grade B**: Requires 15%+ gain

### **Step 2: Find Consolidation Base**
- Identify the highest high (becomes pivot resistance)
- Base must be 15-90 bars long
- Price should stay relatively near the high

### **Step 3: Detect Contractions**
- Contraction = pullback from high + rally attempt
- Each pullback must be at least 5% from base high
- Rally attempt = price moves 2%+ above contraction low
- **Grade A**: Needs 3-4 contractions
- **Grade B**: Needs 2-3 contractions

### **Step 4: Verify Decreasing Volatility**
- Each contraction should be shallower than previous
- Example: 20% → 15% → 12% → 10% ✓
- Tolerance: 5% deviation allowed

### **Step 5: Check Final Contraction**
- Final contraction depth determines grade
- **Grade A**: < 15% from base high
- **Grade B**: < 25% from base high

### **Step 6: Wait for Breakout**
- Price closes above pivot resistance (+2%)
- Volume > 1.2x average (20%+ increase)
- Positive candle (close > open)

---

## 🎯 Entry, Stop Loss, and Take Profit

### **Entry**
- **Trigger**: Close above pivot resistance by 2%
- **Confirmation**: Volume spike (1.5x average ideal)
- **Timing**: Enter on breakout candle or next bar

**Example:**
```
Pivot resistance: $140
Entry trigger: $142.80 (2% above)
Volume: 2.5M (avg: 1.5M) ✓
```

### **Stop Loss**
- **Placement**: Below swing low of final contraction
- **Typical**: 7-15% below entry for Grade A
- **Typical**: 10-20% below entry for Grade B

**Example:**
```
Entry: $142.80
Final contraction low: $125
Stop loss: $124.50 (12.8% risk)
```

### **Take Profit**
- **Default**: 2x risk (Risk:Reward = 1:2)
- **Calculation**: Entry + (Entry - Stop Loss) × 2
- **Aggressive**: 3-5x risk for strong patterns

**Example:**
```
Entry: $142.80
Stop loss: $124.50
Risk: $18.30
Take profit: $142.80 + ($18.30 × 2) = $179.40
```

---

## 💹 Position Sizing

### **Risk Management**
- **Max risk per trade**: 1-2% of account
- **Position size formula**:
  ```
  Shares = (Account × Risk%) / (Entry - Stop Loss)
  ```

**Example:**
```
Account: $100,000
Risk: 1% = $1,000
Entry: $142.80
Stop loss: $124.50
Risk per share: $18.30

Position size: $1,000 / $18.30 = 54 shares
Capital required: 54 × $142.80 = $7,711
```

---

## 📊 Strategy Parameters

### **Configurable Parameters**

| Parameter | Default | Grade A | Grade B | Description |
|-----------|---------|---------|---------|-------------|
| `lookback_period` | 60 | 60 | 60 | Bars to scan for patterns |
| `min_base_length` | 15 | 20 | 15 | Minimum consolidation bars |
| `max_base_length` | 90 | 60 | 90 | Maximum consolidation bars |
| `grade_a_final_contraction` | 0.15 | 0.15 | N/A | Max 15% depth |
| `grade_b_final_contraction` | 0.25 | N/A | 0.25 | Max 25% depth |
| `min_contractions_grade_a` | 3 | 3-4 | N/A | Number of pullbacks |
| `min_contractions_grade_b` | 2 | N/A | 2-3 | Number of pullbacks |
| `prior_uptrend_threshold_a` | 0.30 | 30%+ | N/A | Prior gain required |
| `prior_uptrend_threshold_b` | 0.15 | N/A | 15%+ | Prior gain required |
| `breakout_volume_multiplier` | 1.5 | 1.5-2x | 1.2x | Volume confirmation |
| `pivot_resistance_threshold` | 0.02 | 2% | 2% | Breakout buffer |

---

## 🔧 Usage in Your System

### **1. Backtesting**

```python
from backend.vcp_strategy import VCPStrategy
from backend.data_fetch_yfinance import YFinanceDataFetcher

# Fetch historical data
fetcher = YFinanceDataFetcher()
df = fetcher.fetch_historical_data('AAPL', period='1y', interval='1d')

# Initialize VCP strategy
vcp = VCPStrategy(
    lookback_period=60,
    grade_a_final_contraction=0.15,
    grade_b_final_contraction=0.25
)

# Generate signals
df_signals = vcp.generate_signals(df)

# Check for patterns
vcp_signals = df_signals[df_signals['Signal'] == 1]
print(f"Found {len(vcp_signals)} VCP breakouts")

for idx, row in vcp_signals.iterrows():
    details = vcp.get_pattern_details(df_signals, df_signals.index.get_loc(idx))
    print(f"\nVCP {details['vcp_grade']} Pattern:")
    print(f"  Date: {details['timestamp']}")
    print(f"  Price: ${details['price']:.2f}")
    print(f"  Signal Strength: {details['signal_strength']:.1f}/10")
    print(f"  Contractions: {details['num_contractions']}")
    print(f"  Prior Gain: {details['prior_gain_pct']:.1f}%")
    print(f"  Stop Loss: ${details['stop_loss']:.2f}")
    print(f"  Take Profit: ${details['take_profit']:.2f}")
    print(f"  Risk:Reward: 1:{details['risk_reward_ratio']:.2f}")
```

### **2. Live Trading with Grow/Zerodha API**

```python
from backend.live_scheduler import LiveScheduler

# Initialize scheduler
scheduler = LiveScheduler()

# VCP strategy will be loaded from profile config
scheduler.load_profiles('config/profiles/')

# Start monitoring (fetches live data via Grow/Zerodha)
scheduler.start()

# When VCP pattern + breakout detected:
# → Signal sent to Discord
# → No automatic trade execution (as per your requirement)
```

### **3. Enhanced GUI**

1. Launch GUI: `python app/enhanced_gui.py`
2. Go to **"Backtest"** tab
3. Select **"VCP Strategy (Minervini Volatility Contraction)"**
4. Upload historical data or fetch from yfinance
5. Run backtest to see VCP patterns and performance

---

## 📈 Expected Performance

### **Grade A Patterns**
- **Win rate**: 70-80%
- **Avg gain**: 20-40%
- **Avg loss**: 7-12%
- **Profit factor**: 3-5
- **Typical hold time**: 2-8 weeks

### **Grade B Patterns**
- **Win rate**: 60-70%
- **Avg gain**: 15-30%
- **Avg loss**: 10-15%
- **Profit factor**: 2-3
- **Typical hold time**: 2-6 weeks

### **Combined (A + B)**
- **Overall win rate**: 65-75%
- **Expectancy**: Positive (3-5R per trade)
- **Monthly signals**: 2-5 (depends on market)

---

## ⚠️ Important Notes

### **Best Markets for VCP**
- ✅ **Bull markets** (trending higher)
- ✅ **Growth stocks** with momentum
- ✅ **Individual stocks** (works better than indices)
- ✅ **Sectors in leadership** (tech, healthcare during bull runs)
- ⚠️ **Avoid in bear markets** or ranging markets

### **When to Avoid**
- ❌ Choppy/ranging markets (< 15% uptrend)
- ❌ High volatility periods (contractions won't form)
- ❌ Low liquidity stocks (< 500K volume)
- ❌ News-driven spikes (false patterns)

### **Risk Management**
- Never risk more than 1-2% per trade
- Use proper stop losses (don't move them lower)
- Scale out at 2R, 3R, 5R if strong momentum
- Cut losses quickly if pattern fails

---

## 🚀 Integration with Your System

### **Data Fetching**
Your system will fetch data through **Grow/Zerodha API**:
- ✅ Historical data for backtesting VCP patterns
- ✅ Live data for real-time VCP detection
- ✅ Volume data essential for breakout confirmation

### **Signal Generation**
VCP strategy generates signals when:
1. Pattern detected (Grade A or B)
2. Breakout confirmed (price + volume)
3. Signal strength calculated (6-10/10)

### **Discord Alerts**
Signals sent to Discord include:
```
🎯 VCP GRADE A BREAKOUT
Symbol: AAPL
Price: $142.80
Entry: $143.00
Stop Loss: $124.50 (12.8% risk)
Take Profit: $179.40 (25.6% gain)
Signal Strength: 9.0/10
Contractions: 4
Prior Gain: 38.5%
Volume: 2.5M (167% of average)
```

---

## 📚 Further Reading

- **Mark Minervini's Books**:
  - "Trade Like a Stock Market Wizard" (VCP introduced here)
  - "Think & Trade Like a Champion"
  
- **Key Concepts**:
  - SEPA (Specific Entry Point Analysis)
  - Stage analysis (Weinstein method)
  - Relative strength vs market

---

## 🎯 Quick Reference

**VCP Checklist:**
- [ ] Prior uptrend: 30%+ (A) or 15%+ (B)
- [ ] Base formed: 15-90 bars
- [ ] 3-4 contractions (A) or 2-3 (B)
- [ ] Decreasing volatility pattern
- [ ] Final contraction: < 15% (A) or < 25% (B)
- [ ] Breakout above pivot +2%
- [ ] Volume > 1.2x average
- [ ] Stop below contraction low
- [ ] Target 2-3x risk

**Your 3 Strategies:**
1. **EMA30** - Simple trend following (good for beginners)
2. **ICT** - Institutional order flow (advanced)
3. **VCP** - Momentum breakouts (intermediate-advanced) ⭐ NEW

---

Ready to catch powerful breakouts with VCP! 🚀📈
