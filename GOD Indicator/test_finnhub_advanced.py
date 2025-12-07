"""
Test alternative Finnhub endpoints and formats for NSE data
"""

import requests
from datetime import datetime, timedelta

API_KEY = 'd4jv009r01qgcb0voap0d4jv009r01qgcb0voapg'

print("\n" + "="*70)
print("🔬 TESTING ALTERNATIVE FINNHUB ENDPOINTS FOR NSE")
print("="*70)

# Test 1: Stock symbols endpoint
print("\n📊 Test 1: Get NSE stock symbols list")
print("-"*70)
url = "https://finnhub.io/api/v1/stock/symbol"
params = {'exchange': 'NS', 'token': API_KEY}  # NS = NSE India

try:
    response = requests.get(url, params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {len(data)} symbols")
        if data:
            print(f"Sample symbols: {[d.get('symbol') for d in data[:5]]}")
    else:
        print(f"❌ Error: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 2: Try different exchange codes
print("\n📊 Test 2: Testing different exchange codes")
print("-"*70)
exchange_codes = ['NS', 'NSE', 'BO', 'BSE', 'IN', 'INDIA']

for ex_code in exchange_codes:
    params = {'exchange': ex_code, 'token': API_KEY}
    try:
        response = requests.get("https://finnhub.io/api/v1/stock/symbol", params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"   ✅ {ex_code}: {len(data)} symbols found")
            else:
                print(f"   ⚠️  {ex_code}: Empty response")
        else:
            print(f"   ❌ {ex_code}: {response.status_code}")
    except Exception as e:
        print(f"   ❌ {ex_code}: {e}")

# Test 3: Company profile (sometimes works when candles don't)
print("\n📊 Test 3: Company Profile endpoint")
print("-"*70)
symbols = ['RELIANCE.NS', 'NSE:RELIANCE', 'RELIANCE', 'INFY.NS']

for symbol in symbols:
    url = "https://finnhub.io/api/v1/stock/profile2"
    params = {'symbol': symbol, 'token': API_KEY}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"   ✅ {symbol}: {data.get('name', 'Found')}")
            else:
                print(f"   ⚠️  {symbol}: Empty")
        else:
            print(f"   ❌ {symbol}: {response.status_code}")
    except Exception as e:
        print(f"   ❌ {symbol}: {e}")

# Test 4: Check account tier/limits
print("\n📊 Test 4: Check API usage/limits")
print("-"*70)
url = "https://finnhub.io/api/v1/quota"
params = {'token': API_KEY}

try:
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API Quota Info:")
        for key, value in data.items():
            print(f"   • {key}: {value}")
    else:
        print(f"⚠️  Quota endpoint: {response.status_code}")
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "="*70)
print("📋 SUMMARY")
print("="*70)
print("""
If all NSE tests fail with 403:
  → Your Finnhub account needs upgrade for Indian market data
  → Free tier limitations confirmed
  
Solutions:
  1. Upgrade Finnhub to Premium ($59/month) - unlocks NSE/BSE
  2. Use yfinance for NSE/BSE (free but 15-min delayed)
  3. Get Zerodha Kite API (₹2,000/month, real-time NSE/BSE)
  
Our unified_data_fetcher.py already handles this:
  → Falls back to yfinance for NSE/BSE automatically
  → Uses Finnhub for US/Forex/Commodities (working)
""")
print("="*70)
