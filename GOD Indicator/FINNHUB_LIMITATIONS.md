# ⚠️ IMPORTANT: Finnhub Free Tier Limitations

## Issue Discovered

The **403 Forbidden** error indicates that Finnhub's **free tier does NOT support**:
- ❌ NSE/BSE Indian stocks (forbidden)
- ❌ Many international exchanges

## What Finnhub Free Tier DOES Support

✅ **US Stocks** (NASDAQ, NYSE, AMEX)
- AAPL, MSFT, GOOGL, TSLA, etc.

✅ **Forex** (Major pairs)
- OANDA:EUR_USD, OANDA:GBP_USD, etc.

✅ **Crypto** (Bitcoin, Ethereum, etc.)
- BINANCE:BTCUSDT, BINANCE:ETHUSDT

✅ **Some Commodities** (Limited)
- OANDA:XAU_USD (Gold)
- OANDA:XAG_USD (Silver)

## Solutions for NSE/BSE Indian Stocks

### Option 1: Use Zerodha Kite API (RECOMMENDED)
**Status:** Already implemented in `backend/zerodha_kite_safe.py`

**Pros:**
- ✅ Real NSE/BSE data
- ✅ Real-time quotes
- ✅ Historical data
- ✅ WebSocket streaming
- ✅ Paper trading included

**Cons:**
- ⚠️ Requires Zerodha account
- ⚠️ ₹2,000/month for API access

**Setup:**
1. Get Zerodha API credentials (kite.trade)
2. Already integrated in backend
3. Just need to connect to GUI

### Option 2: Use yfinance for NSE/BSE (FREE)
**Status:** Currently using this

**Pros:**
- ✅ Free
- ✅ Works for NSE/BSE
- ✅ No API key needed

**Cons:**
- ❌ 15-20 min delayed data
- ❌ Unreliable for live trading
- ❌ No WebSocket streaming

### Option 3: Upgrade Finnhub (PAID)
**Cost:** $59/month for Starter plan

**Pros:**
- ✅ NSE/BSE access
- ✅ More exchanges
- ✅ Higher rate limits

**Cons:**
- ❌ Monthly cost
- ❌ Still limited compared to Zerodha

## Recommended Hybrid Approach

### For Production NSE/BSE Trading:
```python
# Use Zerodha Kite API
from backend.zerodha_kite_safe import ZerodhaKiteDataFetcher

fetcher = ZerodhaKiteDataFetcher(api_key, access_token)
df = fetcher.fetch_historical_data('RELIANCE', 'day', from_date, to_date)
quote = fetcher.get_quote(['NSE:RELIANCE'])
```

### For US Stocks:
```python
# Use Finnhub
from backend.finnhub_data_fetcher import FinnhubDataFetcher

fetcher = FinnhubDataFetcher()
df = fetcher.fetch_historical_data('AAPL', 'D', exchange='US')
quote = fetcher.get_quote('AAPL', 'US')
```

### For Backtesting/Testing:
```python
# Use yfinance (free, but delayed)
from backend.data_fetch_yfinance import YFinanceDataFetcher

fetcher = YFinanceDataFetcher()
df = fetcher.fetch_historical_data('RELIANCE.NS', period='1y')
```

## Updated Data Source Strategy

| Asset Type | Production | Backtesting | Cost |
|------------|-----------|-------------|------|
| **NSE/BSE Stocks** | Zerodha Kite | yfinance | ₹2,000/mo |
| **US Stocks** | Finnhub | Finnhub/yfinance | Free |
| **Gold/Silver** | Finnhub | Finnhub | Free |
| **Forex** | Finnhub | Finnhub | Free |
| **Crypto** | Finnhub | Finnhub | Free |

## Action Items

### Immediate (This Week):
1. ✅ Keep Finnhub for US stocks, Gold, Forex
2. ✅ Use yfinance for NSE/BSE (testing/backtesting)
3. 🔄 Integrate Zerodha Kite with GUI (for production)

### Short-term (Next Month):
1. Get Zerodha account
2. Get Kite API credentials
3. Switch to Zerodha for live NSE/BSE trading

### Long-term (Later):
1. Consider Finnhub paid tier if needed for other exchanges
2. Or stick with Zerodha + Finnhub combo

## Updated Code Approach

I'll create a **unified data fetcher** that intelligently chooses the best source:

```python
class UnifiedDataFetcher:
    """Smart data fetcher that chooses the best source"""
    
    def __init__(self):
        self.finnhub = FinnhubDataFetcher()  # For US, Forex, Crypto
        self.yfinance = YFinanceDataFetcher()  # For NSE/BSE testing
        self.zerodha = None  # For NSE/BSE production (when available)
    
    def fetch_historical_data(self, symbol, exchange='NSE'):
        if exchange in ['NSE', 'BSE']:
            # Use Zerodha if available, else yfinance
            if self.zerodha:
                return self.zerodha.fetch_historical_data(symbol, ...)
            else:
                return self.yfinance.fetch_historical_data(f"{symbol}.NS", ...)
        else:
            # Use Finnhub for US/Forex/Crypto
            return self.finnhub.fetch_historical_data(symbol, ...)
```

## Summary

**Finnhub Limitation:** Free tier doesn't support NSE/BSE  
**Solution:** Use Zerodha for NSE/BSE, Finnhub for everything else  
**Status:** Zerodha already implemented, just needs GUI integration  

**Next Steps:**
1. Update GUI to use hybrid approach (yfinance for NSE, Finnhub for US)
2. Add Zerodha integration when you get API credentials
3. Document the multi-source strategy

This is actually better - you get the best of all worlds! 🎯
