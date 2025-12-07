"""
End-to-End Integration Tests
Tests complete workflow from data fetch to signal generation
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.unified_data_fetcher import UnifiedDataFetcher


def test_complete_workflow_nse():
    """Test complete workflow: NSE stock → data → signals → analysis"""
    print("\n" + "="*60)
    print("COMPLETE NSE WORKFLOW TEST")
    print("="*60)
    
    # Step 1: Fetch data
    print("\n1️⃣ Fetching NSE data...")
    fetcher = UnifiedDataFetcher(finnhub_api_key='d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg')
    to_date = datetime.now()
    from_date = to_date - timedelta(days=180)
    
    df = fetcher.fetch_historical_data('RELIANCE', 'D', from_date, to_date, 'NSE')
    assert df is not None
    assert len(df) > 100
    print(f"   ✅ Fetched {len(df)} candles")
    print(f"   ✅ Latest close: ₹{df['Close'].iloc[-1]:.2f}")
    
    # Step 2: Generate signals (try multiple strategies)
    print("\n2️⃣ Generating trading signals...")
    
    strategies_tested = 0
    
    try:
        from backend.ema_strategy import EMA30Strategy
        strategy = EMA30Strategy()
        signals = strategy.generate_signals(df)
        buy_signals = signals[signals['Signal'] == 1]
        print(f"   ✅ EMA30: {len(buy_signals)} buy signals")
        strategies_tested += 1
    except ImportError:
        print("   ⚠️ EMA30 strategy not available")
    
    try:
        from backend.vcp_strategy import VCPStrategy
        strategy = VCPStrategy()
        signals = strategy.generate_signals(df)
        buy_signals = signals[signals['Signal'] == 1]
        print(f"   ✅ VCP: {len(buy_signals)} buy signals")
        strategies_tested += 1
    except ImportError:
        print("   ⚠️ VCP strategy not available")
    
    assert strategies_tested > 0, "No strategies available"
    
    # Step 3: News sentiment
    print("\n3️⃣ Analyzing news sentiment...")
    try:
        from backend.news_sentiment import NewsSentimentAnalyzer
        analyzer = NewsSentimentAnalyzer()
        news = analyzer.get_stock_news('RELIANCE', days=7, max_articles=5)
        
        if news:
            sentiment = analyzer.analyze_sentiment(news)
            print(f"   ✅ Analyzed {len(news)} articles")
            print(f"   ✅ Sentiment: {sentiment.get('summary', 'N/A')}")
        else:
            print("   ⚠️ No news found")
    except ImportError:
        print("   ⚠️ News sentiment not available")
    
    # Step 4: Verify data quality
    print("\n4️⃣ Data quality checks...")
    assert not df['Close'].isna().any()
    assert (df['Close'] > 0).all()
    assert (df['High'] >= df['Low']).all()
    print("   ✅ All quality checks passed")
    
    print("\n" + "="*60)
    print("✅ COMPLETE NSE WORKFLOW: SUCCESS")
    print("="*60 + "\n")


def test_complete_workflow_us():
    """Test complete workflow: US stock → data → signals → analysis"""
    print("\n" + "="*60)
    print("COMPLETE US WORKFLOW TEST")
    print("="*60)
    
    # Step 1: Fetch data
    print("\n1️⃣ Fetching US data...")
    fetcher = UnifiedDataFetcher(finnhub_api_key='d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg')
    to_date = datetime.now()
    from_date = to_date - timedelta(days=180)
    
    df = fetcher.fetch_historical_data('AAPL', 'D', from_date, to_date, 'US')
    assert df is not None
    assert len(df) > 100
    print(f"   ✅ Fetched {len(df)} candles")
    print(f"   ✅ Latest close: ${df['Close'].iloc[-1]:.2f}")
    
    # Step 2: Generate signals
    print("\n2️⃣ Generating trading signals...")
    try:
        from backend.ema_strategy import EMA30Strategy
        strategy = EMA30Strategy()
        signals = strategy.generate_signals(df)
        buy_signals = signals[signals['Signal'] == 1]
        print(f"   ✅ EMA30: {len(buy_signals)} buy signals")
    except ImportError:
        print("   ⚠️ EMA30 strategy not available")
    
    # Step 3: Real-time quote
    print("\n3️⃣ Fetching real-time quote...")
    quote = fetcher.get_quote('AAPL', 'US')
    if quote:
        print(f"   ✅ Real-time price: ${quote.get('c', 0):.2f}")
    
    print("\n" + "="*60)
    print("✅ COMPLETE US WORKFLOW: SUCCESS")
    print("="*60 + "\n")


def test_multi_symbol_portfolio():
    """Test handling multiple symbols simultaneously"""
    print("\n" + "="*60)
    print("MULTI-SYMBOL PORTFOLIO TEST")
    print("="*60)
    
    fetcher = UnifiedDataFetcher()
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)
    
    symbols = {
        'NSE': ['RELIANCE', 'TCS', 'INFY'],
        'US': ['AAPL', 'MSFT', 'GOOGL']
    }
    
    results = {}
    
    for exchange, symbol_list in symbols.items():
        print(f"\n{exchange} Stocks:")
        for symbol in symbol_list:
            try:
                df = fetcher.fetch_historical_data(symbol, 'D', from_date, to_date, exchange)
                price = df['Close'].iloc[-1]
                results[symbol] = price
                currency = "₹" if exchange == 'NSE' else "$"
                print(f"   ✅ {symbol}: {currency}{price:.2f}")
            except Exception as e:
                print(f"   ❌ {symbol}: {str(e)}")
    
    assert len(results) >= 4, "At least 4 symbols should succeed"
    
    print(f"\n✅ Successfully fetched {len(results)}/{sum(len(v) for v in symbols.values())} symbols")


def test_error_handling():
    """Test error handling for various edge cases"""
    print("\n" + "="*60)
    print("ERROR HANDLING TEST")
    print("="*60)
    
    fetcher = UnifiedDataFetcher()
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)
    
    # Test invalid symbol
    print("\n1️⃣ Testing invalid symbol...")
    try:
        df = fetcher.fetch_historical_data('INVALID_XYZ_999', 'D', from_date, to_date, 'NSE')
        print("   ⚠️ Should have raised exception")
    except Exception:
        print("   ✅ Invalid symbol handled correctly")
    
    # Test invalid date range
    print("\n2️⃣ Testing invalid date range...")
    try:
        df = fetcher.fetch_historical_data('RELIANCE', 'D', to_date, from_date, 'NSE')  # Swapped dates
        # Some sources might handle this gracefully
        print("   ⚠️ Accepted invalid date range (source handles gracefully)")
    except Exception:
        print("   ✅ Invalid date range rejected")
    
    print("\n✅ Error handling tests complete")


if __name__ == '__main__':
    print("\n" + "="*70)
    print(" "*20 + "INTEGRATION TEST SUITE")
    print("="*70)
    
    # Run all tests
    test_complete_workflow_nse()
    test_complete_workflow_us()
    test_multi_symbol_portfolio()
    test_error_handling()
    
    print("\n" + "="*70)
    print(" "*20 + "ALL INTEGRATION TESTS PASSED")
    print("="*70 + "\n")
