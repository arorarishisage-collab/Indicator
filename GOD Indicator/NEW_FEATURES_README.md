# 🎯 GOD Indicator - New Features Quick Start

## 🚀 What's New (November 2025)

### 1. 📰 News Sentiment Analysis
Automatically fetches and analyzes financial news to help make better trading decisions.

**Features:**
- Fetches news from NewsData.io (pre-configured with your API key)
- Automatic fallback to NewsAPI.org and Google News
- Sentiment analysis (positive/negative/neutral)
- Shows latest headlines with sentiment scores
- Integrated into beginner mode GUI

**API Key:** Already configured - `pub_351be3c902b4478180538c1f6c2c33d3`

**Usage:**
```python
from backend.news_sentiment import NewsSentimentAnalyzer

# Your API key is already set as default
analyzer = NewsSentimentAnalyzer()
result = analyzer.get_sentiment_signal('RELIANCE.NS', days=7)

print(f"Sentiment: {result['sentiment']['label']}")
print(f"Score: {result['sentiment']['score']}")
```

📋 **Full Guide:** See `NEWSDATA_SETUP.md` for detailed documentation

---

### 2. 🔒 Zerodha Kite Connect (Paper Trading Only)
Real-time market data from Zerodha - **READ-ONLY, NO LIVE ORDERS**.

**Safety Features:**
- ✅ Fetch historical data
- ✅ Stream live quotes
- ✅ Get market depth
- ❌ **CANNOT place live orders** (hard-coded safety)
- ❌ **CANNOT modify/cancel orders**

**Usage:**
```python
from backend.zerodha_kite_safe import ZerodhaKiteDataFetcher

# Initialize (read-only mode)
kite = ZerodhaKiteDataFetcher(api_key='your_key', access_token='your_token')

# Fetch historical data
df = kite.fetch_historical_data(
    symbol='RELIANCE',
    interval='day',
    from_date=datetime(2024, 1, 1),
    to_date=datetime(2024, 12, 31)
)

# Get live quotes
quotes = kite.get_quote(['NSE:RELIANCE', 'NSE:TCS'])
```

**Paper Trading Simulator:**
```python
from backend.zerodha_kite_safe import PaperTradingSimulator

sim = PaperTradingSimulator(initial_capital=100000)

# Simulate buy
trade = sim.simulate_order('RELIANCE', 10, 'BUY', 2500.00, stop_loss=2450)

# Close position
sim.close_position(trade['trade_id'], 2580.00)

# Get summary
summary = sim.get_portfolio_summary()
print(f"P&L: ₹{summary['total_pnl']:,.2f}")
```

---

### 3. 🎯 Beginner Mode GUI
Simplified interface for non-technical traders.

**Features:**
- Simple dropdown selections (no technical jargon)
- One-click stock analysis
- Plain English recommendations
- News sentiment integration
- Paper trading simulator
- Visual risk indicators

**Launch:**
```bash
python3 app/beginner_mode_gui.py
```

**Screenshot:**
```
┌─────────────────────────────────────────┐
│  🔒 PAPER TRADING MODE - NO REAL ORDERS │
├─────────────────────────────────────────┤
│  Pick a Stock:                          │
│  [RELIANCE.NS - Reliance Industries ▼]  │
│                                         │
│  Pick a Strategy:                       │
│  [VCP - Best for trending stocks   ▼]   │
│                                         │
│  Risk Level: ●●○○○ Conservative         │
│                                         │
│  [🔍 ANALYZE THIS STOCK]                │
│                                         │
│  ✅ STRONG BUY SIGNAL                   │
│  Strength: 8.5/10                       │
│                                         │
│  Current Price: ₹2,500.00               │
│  Stop Loss: ₹2,450.00                   │
│  Target: ₹2,650.00                      │
│  Risk/Reward: 1:3                       │
│                                         │
│  📰 News: 😊 POSITIVE (75%)             │
│  • Major contract win announced         │
│  • Tech sector leading gains            │
│                                         │
│  [📝 SIMULATE PAPER TRADE]              │
└─────────────────────────────────────────┘
```

---

## 🛠️ Installation

### Quick Setup (Recommended)
```bash
# Make setup script executable
chmod +x setup_new_features.sh

# Run setup
./setup_new_features.sh
```

### Manual Installation
```bash
# Install news sentiment
pip3 install textblob feedparser
python3 -m textblob.download_corpora

# Install Zerodha Kite
pip3 install kiteconnect
```

---

## 📊 Usage Modes

### Mode 1: Beginner (Simple)
**For:** Non-technical traders, beginners  
**Features:** Simple dropdowns, plain English, one-click analysis  
**Launch:** `python3 app/beginner_mode_gui.py`

### Mode 2: Intermediate (Balanced)
**For:** Traders who understand basics  
**Features:** Pre-configured filters, visual indicators  
**Launch:** Coming soon (see SIMPLIFICATION_PLAN.md)

### Mode 3: Advanced (Full Control)
**For:** Professional traders  
**Features:** All technical controls, regime filters, MTF, RL  
**Launch:** `python3 app/enhanced_gui.py`

---

## 🔐 Safety & Paper Trading

### Three-Layer Safety System

#### Layer 1: Configuration Lock
```json
{
    "zerodha": {
        "mode": "PAPER_ONLY",
        "enable_live_orders": false
    }
}
```

#### Layer 2: Code-Level Prevention
```python
class ZerodhaKiteDataFetcher:
    PAPER_TRADING_ONLY = True  # Hard-coded
    BLOCK_LIVE_ORDERS = True    # Hard-coded
    
    def place_order(self):
        raise PermissionError("Live trading disabled")
```

#### Layer 3: GUI Warning
```
🔒 PAPER TRADING MODE - NO REAL ORDERS
```

---

## 📰 News API Setup (Optional)

### NewsData.io (Primary Source) ✅
**Already configured!** Your API key is pre-set in the code.

- **Key:** `pub_351be3c902b4478180538c1f6c2c33d3`
- **Dashboard:** https://newsdata.io/dashboard
- **Features:** 80,000+ sources, business news, global coverage
- **Updates:** Every 15 minutes

📋 **Full Documentation:** See `NEWSDATA_SETUP.md`

### NewsAPI.org (Optional Backup)
If you want additional coverage:
1. Visit https://newsapi.org
2. Sign up for free account (100 requests/day)
3. Get API key
4. Use in code:
```python
analyzer = NewsSentimentAnalyzer(
    newsdata_key='pub_351be3c902b4478180538c1f6c2c33d3',  # Default
    newsapi_key='your_additional_key_here'  # Optional
)
```

### Without Any API Key
Falls back to Google News RSS (limited functionality but works)

---

## 🔌 Zerodha API Setup

### Step 1: Get API Credentials
1. Login to Kite Connect: https://kite.trade
2. Go to: https://developers.kite.trade
3. Create app
4. Get API Key and API Secret

### Step 2: Authenticate
```python
from backend.zerodha_kite_safe import ZerodhaKiteDataFetcher

kite = ZerodhaKiteDataFetcher(api_key='your_key')

# Get login URL
login_url = kite.get_login_url()
print(f"Login here: {login_url}")

# After login, you'll get request_token in redirect URL
# Generate session
session = kite.generate_session(request_token='token_from_url')
access_token = session['access_token']

# Now you can fetch data
df = kite.fetch_historical_data(...)
```

### Step 3: Test with Paper Trading
```python
from backend.zerodha_kite_safe import PaperTradingSimulator

# Create simulator
sim = PaperTradingSimulator(initial_capital=100000)

# Simulate trades
trade = sim.simulate_order('RELIANCE', 10, 'BUY', 2500.00)
print(f"Trade ID: {trade['trade_id']}")

# Check portfolio
summary = sim.get_portfolio_summary()
print(f"Capital: ₹{summary['current_capital']:,.2f}")
```

---

## 🎓 Examples

### Example 1: Simple Stock Analysis (Beginner)
```python
# Just run the beginner GUI
python3 app/beginner_mode_gui.py

# Then:
# 1. Select stock: RELIANCE.NS
# 2. Select strategy: VCP
# 3. Set risk: Conservative
# 4. Click "ANALYZE THIS STOCK"
# 5. Review results and news
# 6. Click "SIMULATE PAPER TRADE"
```

### Example 2: News Sentiment Analysis
```python
from backend.news_sentiment import NewsSentimentAnalyzer

analyzer = NewsSentimentAnalyzer()

# Analyze multiple stocks
for symbol in ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']:
    result = analyzer.get_sentiment_signal(symbol, days=7)
    
    sentiment = result['sentiment']
    print(f"\n{symbol}:")
    print(f"  Sentiment: {sentiment['emoji']} {sentiment['label']}")
    print(f"  Score: {sentiment['score']:.3f}")
    print(f"  Articles: {sentiment['article_count']}")
    
    # Show top 3 headlines
    for i, article in enumerate(result['articles'][:3], 1):
        print(f"  {i}. {article['title']}")
```

### Example 3: Zerodha Data Fetching
```python
from backend.zerodha_kite_safe import ZerodhaKiteDataFetcher
from datetime import datetime, timedelta

# Initialize
kite = ZerodhaKiteDataFetcher(api_key='your_key', access_token='your_token')

# Fetch 1 year of daily data
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

df = kite.fetch_historical_data(
    symbol='RELIANCE',
    interval='day',
    from_date=start_date,
    to_date=end_date
)

print(f"Fetched {len(df)} candles")
print(df.tail())

# Get live quote
quote = kite.get_quote(['NSE:RELIANCE'])
print(f"LTP: ₹{quote['NSE:RELIANCE']['last_price']}")
```

---

## 📚 Documentation

- **SIMPLIFICATION_PLAN.md** - Complete simplification strategy
- **BROKER_API_INTEGRATION.md** - Detailed Zerodha setup guide
- **VCP_STRATEGY_GUIDE.md** - VCP strategy documentation
- **TESTING_GUIDE.md** - Testing procedures

---

## 🐛 Troubleshooting

### "textblob not found"
```bash
pip3 install textblob
python3 -m textblob.download_corpora
```

### "kiteconnect not found"
```bash
pip3 install kiteconnect
```

### "No news articles found"
- Get free API key from https://newsapi.org
- Or wait (Google News fallback has rate limits)

### "Cannot place order"
This is intentional! The system is PAPER TRADING ONLY for safety.

---

## 🎯 Next Steps

1. **Try Beginner Mode:**
   ```bash
   python3 app/beginner_mode_gui.py
   ```

2. **Test News Sentiment:**
   ```bash
   python3 backend/news_sentiment.py
   ```

3. **Setup Zerodha (when ready):**
   - Read BROKER_API_INTEGRATION.md
   - Get API credentials
   - Test with paper trading

4. **Go Live (manual trading):**
   - Use signals from tool
   - Place orders manually on Zerodha
   - Track performance

---

## ⚠️ Important Notes

1. **This is NOT automated trading software**
   - Generates signals only
   - You place orders manually
   - No auto-execution

2. **Paper trading is simulated**
   - No real money involved
   - For testing strategies only
   - Actual results may differ

3. **News sentiment is indicative**
   - Use as additional input
   - Not sole decision factor
   - Combine with technical analysis

4. **Zerodha data is read-only**
   - Cannot place live orders
   - Safety hard-coded
   - Paper trading only

---

## 📞 Support

Questions? Check:
- SIMPLIFICATION_PLAN.md (full details)
- BROKER_API_INTEGRATION.md (Zerodha setup)
- TESTING_GUIDE.md (testing procedures)

---

## 📜 License

Educational and research purposes only.  
Not financial advice. Trade at your own risk.
