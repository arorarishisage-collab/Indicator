"""
Test Finnhub API key directly
"""

import requests

API_KEY = 'd4jv009r01qgcb0voap0d4jv009r01qgcb0voapg'

print("\n" + "="*70)
print("🔍 TESTING FINNHUB API KEY")
print("="*70)
print(f"\nAPI Key: {API_KEY[:20]}...")

# Test 1: Check API key validity with quote endpoint (simpler than candles)
print("\n📊 Test 1: Simple Quote (AAPL)")
print("-"*70)
url = "https://finnhub.io/api/v1/quote"
params = {'symbol': 'AAPL', 'token': API_KEY}

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS: {data}")
    elif response.status_code == 403:
        print(f"❌ 403 FORBIDDEN: {response.text}")
        print("\nPossible reasons:")
        print("  1. API key is invalid/expired")
        print("  2. API key needs activation on Finnhub website")
        print("  3. Rate limit exceeded (60 calls/min on free tier)")
        print("  4. Account suspended")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 2: Check with different symbol
print("\n📊 Test 2: Different Symbol (MSFT)")
print("-"*70)
params = {'symbol': 'MSFT', 'token': API_KEY}

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ SUCCESS: {response.json()}")
    else:
        print(f"❌ Error: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 3: Try without exchange prefix
print("\n📊 Test 3: Check Account Status")
print("-"*70)
print("\nTo fix 403 error:")
print("1. Go to: https://finnhub.io/dashboard")
print("2. Verify your API key is active")
print("3. Check if you need to verify email")
print("4. Generate a new API key if needed")
print("5. Wait 1 minute if rate limited")

print("\n" + "="*70)
