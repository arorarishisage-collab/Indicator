#!/usr/bin/env python3
"""
Quick test of stock screener fixes
Tests that strategies generate signals properly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.unified_data_fetcher import UnifiedDataFetcher
from backend.simple_ema_strategy import SimpleEMAStrategy
from datetime import datetime, timedelta

print("\n" + "="*60)
print("TESTING STOCK SCREENER FIXES")
print("="*60 + "\n")

# Test 1: Data fetching
print("1️⃣ Testing data fetching...")
fetcher = UnifiedDataFetcher(finnhub_api_key='d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg')

to_date = datetime.now()
from_date = to_date - timedelta(days=180)

# Test NSE
print("   Testing NSE: RELIANCE...")
df_nse = fetcher.fetch_historical_data('RELIANCE', 'D', from_date, to_date, 'NSE')
print(f"   ✅ NSE: {len(df_nse)} bars, Latest: ₹{df_nse['Close'].iloc[-1]:.2f}")

# Test US
print("   Testing US: AAPL...")
df_us = fetcher.fetch_historical_data('AAPL', 'D', from_date, to_date, 'US')
print(f"   ✅ US: {len(df_us)} bars, Latest: ${df_us['Close'].iloc[-1]:.2f}")

# Test Forex
print("   Testing Forex: GLD (Gold)...")
df_gold = fetcher.fetch_historical_data('GLD', 'D', from_date, to_date, 'US')
print(f"   ✅ Gold: {len(df_gold)} bars, Latest: ${df_gold['Close'].iloc[-1]:.2f}\n")

# Test 2: Strategy signal generation
print("2️⃣ Testing strategy signal generation...")
strategy = SimpleEMAStrategy(fast_period=9, slow_period=21)

print("   Testing on RELIANCE...")
signals_nse = strategy.generate_signals(df_nse)
buy_signals_nse = signals_nse[signals_nse['Signal'] == 1]
print(f"   ✅ NSE: {len(buy_signals_nse)} buy signals found")
if len(buy_signals_nse) > 0:
    latest = buy_signals_nse.iloc[-1]
    print(f"      Latest signal: {latest.name.date()}, Strength: {latest['Signal_Strength']:.1f}/10")

print("   Testing on AAPL...")
signals_us = strategy.generate_signals(df_us)
buy_signals_us = signals_us[signals_us['Signal'] == 1]
print(f"   ✅ US: {len(buy_signals_us)} buy signals found")
if len(buy_signals_us) > 0:
    latest = buy_signals_us.iloc[-1]
    print(f"      Latest signal: {latest.name.date()}, Strength: {latest['Signal_Strength']:.1f}/10")

print("   Testing on GLD...")
signals_gold = strategy.generate_signals(df_gold)
buy_signals_gold = signals_gold[signals_gold['Signal'] == 1]
print(f"   ✅ Gold: {len(buy_signals_gold)} buy signals found")
if len(buy_signals_gold) > 0:
    latest = buy_signals_gold.iloc[-1]
    print(f"      Latest signal: {latest.name.date()}, Strength: {latest['Signal_Strength']:.1f}/10\n")

# Test 3: Quick screener test
print("3️⃣ Testing screener (5 stocks)...")
from backend.stock_screener import StockScreener

screener = StockScreener(fetcher)

# Test with very low threshold
print("   Screening NSE with min_strength=3.0...")
results = screener.screen_by_strategy(
    strategy=strategy,
    market='NSE',
    min_signal_strength=3.0,
    max_stocks=5,
    days=180
)

print(f"\n   ✅ SCREENER RESULTS: {len(results)} stocks found")
for i, result in enumerate(results, 1):
    print(f"   {i}. {result['symbol']}: ₹{result['current_price']:.2f} (Strength: {result['signal_strength']:.1f}/10)")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
print("\nIf you see buy signals above, the screener SHOULD work!")
print("If screener shows 0 results, there's still an issue.\n")
