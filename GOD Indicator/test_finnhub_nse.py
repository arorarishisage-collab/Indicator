"""
Direct test of Finnhub API for NSE/BSE stocks
"""

import requests
from datetime import datetime, timedelta

API_KEY = 'd4jv009r01qgcb0voap0d4jv009r01qgcb0voapg'

print("\n" + "="*70)
print("🧪 FINNHUB NSE/BSE DIRECT TEST")
print("="*70)

# Test different symbol formats for RELIANCE
test_symbols = [
    'RELIANCE.NS',      # Yahoo Finance format
    'NSE:RELIANCE',     # Finnhub format
    'RELIANCE',         # Plain symbol
    'RELIANCE.BSE',     # BSE format
]

to_date = int(datetime.now().timestamp())
from_date = int((datetime.now() - timedelta(days=30)).timestamp())

for symbol in test_symbols:
    print(f"\n📊 Testing: {symbol}")
    print("-"*70)
    
    url = f"https://finnhub.io/api/v1/stock/candle"
    params = {
        'symbol': symbol,
        'resolution': 'D',
        'from': from_date,
        'to': to_date,
        'token': API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('s') == 'ok':
                print(f"   ✅ SUCCESS: {len(data.get('c', []))} candles received")
                print(f"   Latest Close: {data['c'][-1] if data.get('c') else 'N/A'}")
            elif data.get('s') == 'no_data':
                print(f"   ⚠️  NO DATA: {data}")
            else:
                print(f"   ❌ FAILED: {data}")
        else:
            print(f"   ❌ HTTP ERROR: {response.text}")
            
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")

# Test quote endpoint
print("\n" + "="*70)
print("📊 Testing Quote Endpoint")
print("="*70)

for symbol in ['NSE:RELIANCE', 'RELIANCE.NS', 'AAPL']:
    print(f"\n🔍 Quote for: {symbol}")
    url = f"https://finnhub.io/api/v1/quote"
    params = {'symbol': symbol, 'token': API_KEY}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('c'):
                print(f"   ✅ Price: {data['c']}")
            else:
                print(f"   ⚠️  No data: {data}")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
