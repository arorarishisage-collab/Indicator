"""
Test yfinance directly to verify it works
"""

import yfinance as yf
from datetime import datetime, timedelta

print("\n" + "="*70)
print("🧪 TESTING YFINANCE DIRECTLY")
print("="*70)

# Test NSE stock
print("\n📊 Test 1: NSE Stock (RELIANCE.NS)")
print("-"*70)
try:
    ticker = yf.Ticker("RELIANCE.NS")
    df = ticker.history(period="1mo")
    if not df.empty:
        print(f"✅ Got {len(df)} candles")
        print(f"   Latest Close: ₹{df['Close'].iloc[-1]:.2f}")
    else:
        print("❌ No data")
except Exception as e:
    print(f"❌ Error: {e}")

# Test US stock
print("\n📊 Test 2: US Stock (AAPL)")
print("-"*70)
try:
    ticker = yf.Ticker("AAPL")
    df = ticker.history(period="1mo")
    if not df.empty:
        print(f"✅ Got {len(df)} candles")
        print(f"   Latest Close: ${df['Close'].iloc[-1]:.2f}")
    else:
        print("❌ No data")
except Exception as e:
    print(f"❌ Error: {e}")

# Test Gold (via Gold ETF)
print("\n📊 Test 3: Gold ETF (GLD)")
print("-"*70)
try:
    ticker = yf.Ticker("GLD")
    df = ticker.history(period="1mo")
    if not df.empty:
        print(f"✅ Got {len(df)} candles")
        print(f"   Latest Close: ${df['Close'].iloc[-1]:.2f}")
    else:
        print("❌ No data")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("✅ YFINANCE TEST COMPLETE")
print("="*70)
