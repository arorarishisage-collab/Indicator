"""
Verify Finnhub API coverage by checking supported exchanges
"""

import requests

API_KEY = 'd4jv009r01qgcb0voap0d4jv009r01qgcb0voapg'

print("\n" + "="*70)
print("🔍 FINNHUB API - CHECKING SUPPORTED EXCHANGES")
print("="*70)

# Get list of supported exchanges
url = "https://finnhub.io/api/v1/stock/exchange"
params = {'token': API_KEY}

try:
    response = requests.get(url, params=params)
    if response.status_code == 200:
        exchanges = response.json()
        print(f"\n✅ Total Exchanges: {len(exchanges)}")
        
        # Check for Indian exchanges
        indian_exchanges = [ex for ex in exchanges if 'india' in ex.lower() or 'nse' in ex.lower() or 'bse' in ex.lower()]
        
        print(f"\n📍 Looking for NSE/BSE in supported exchanges...")
        if indian_exchanges:
            print(f"✅ Found Indian exchanges: {indian_exchanges}")
        else:
            print("❌ No Indian exchanges found")
        
        print(f"\n📋 All Supported Exchanges:")
        for ex in sorted(exchanges):
            print(f"   • {ex}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

# Try searching for Indian stocks
print("\n" + "="*70)
print("🔍 SEARCHING FOR INDIAN STOCKS")
print("="*70)

search_url = "https://finnhub.io/api/v1/search"
search_terms = ['RELIANCE', 'TCS', 'INFOSYS']

for term in search_terms:
    params = {'q': term, 'token': API_KEY}
    try:
        response = requests.get(search_url, params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get('result', [])
            print(f"\n🔍 Search: {term}")
            if results:
                for r in results[:5]:  # Show first 5 results
                    print(f"   • {r.get('symbol')} - {r.get('description')} ({r.get('type')})")
            else:
                print(f"   ❌ No results found")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n" + "="*70)
print("✅ ANALYSIS COMPLETE")
print("="*70)
print("\nIf NSE/BSE not in supported exchanges, they require:")
print("   • Premium tier ($59+/month)")
print("   • Free tier: US stocks, Forex (limited), Crypto")
print("="*70)
