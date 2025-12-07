#!/usr/bin/env python3
"""Quick test to verify yfinance initialization"""

import sys
import logging
from pathlib import Path

# Setup logging BEFORE imports
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*60)
print("TESTING YFINANCE INITIALIZATION")
print("="*60 + "\n")

print("Importing UnifiedDataFetcher...")
from backend.unified_data_fetcher import UnifiedDataFetcher

print("\nInitializing fetcher...")
fetcher = UnifiedDataFetcher(finnhub_api_key='d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg')

print(f"\nChecking yfinance availability:")
print(f"  yfinance object: {fetcher.yfinance}")
print(f"  Type: {type(fetcher.yfinance) if fetcher.yfinance else 'None'}")

if fetcher.yfinance:
    print("\n✅ SUCCESS: yfinance is initialized!")
    print("\nTrying to fetch AAPL data...")
    
    from datetime import datetime, timedelta
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)
    
    df = fetcher.fetch_historical_data('AAPL', 'D', from_date, to_date, 'US')
    if df is not None and not df.empty:
        print(f"✅ Got {len(df)} bars")
        print(f"   Latest close: ${df['Close'].iloc[-1]:.2f}")
    else:
        print(f"❌ Failed to fetch data")
else:
    print("\n❌ FAILED: yfinance is NOT initialized!")

print("\n" + "="*60)
