#!/usr/bin/env python3
"""
Quick functionality test - Tests core features in ~2 minutes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def quick_test():
    """Run quick tests on all 3 strategies"""
    print("🧪 Quick System Test\n")
    
    # Test 1: Data fetching
    print("1️⃣  Testing data fetching...")
    try:
        from backend.data_fetch_yfinance import YFinanceDataFetcher
        fetcher = YFinanceDataFetcher()
        df = fetcher.fetch_historical_data('GC=F', period='3mo', interval='1d')
        print(f"   ✅ Fetched {len(df)} bars of Gold data\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 2: EMA30 Strategy
    print("2️⃣  Testing EMA30 Strategy...")
    try:
        from backend.ema_strategy import EMA30Strategy
        strategy = EMA30Strategy()
        df_signals = strategy.generate_signals(df.copy())
        signals = (df_signals['Signal'] != 0).sum()
        print(f"   ✅ Generated {signals} signals\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 3: ICT Strategy
    print("3️⃣  Testing ICT Strategy...")
    try:
        from backend.ict_strategy import ICTStrategy
        strategy = ICTStrategy()
        df_signals = strategy.generate_signals(df.copy())
        signals = (df_signals['Signal'] != 0).sum()
        print(f"   ✅ Generated {signals} signals\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 4: VCP Strategy (NEW)
    print("4️⃣  Testing VCP Strategy (NEW)...")
    try:
        from backend.vcp_strategy import VCPStrategy
        from backend.data_fetch_yfinance import YFinanceDataFetcher
        
        # Use AAPL for VCP (more likely to have patterns)
        fetcher = YFinanceDataFetcher()
        df_stock = fetcher.fetch_historical_data('AAPL', period='1y', interval='1d')
        
        strategy = VCPStrategy()
        df_signals = strategy.generate_signals(df_stock)
        vcp_patterns = (df_signals['Signal'] == 1).sum()
        print(f"   ✅ Found {vcp_patterns} VCP patterns in AAPL\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 5: Backtesting
    print("5️⃣  Testing backtesting engine...")
    try:
        from backend.enhanced_backtester import EnhancedBacktester
        from backend.ema_strategy import EMA30Strategy
        
        strategy = EMA30Strategy()
        df_signals = strategy.generate_signals(df.copy())
        
        backtester = EnhancedBacktester(initial_capital=10000)
        results = backtester.run_backtest(df_signals)
        
        metrics = results['metrics']
        print(f"   ✅ Backtest complete:")
        print(f"      Return: {metrics['total_return']:.2f}%")
        print(f"      Win Rate: {metrics['win_rate']:.1f}%")
        print(f"      Trades: {metrics['total_trades']}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Test 6: Advanced Features
    print("6️⃣  Testing advanced features...")
    try:
        from backend.market_regime_detector import MarketRegimeDetector
        detector = MarketRegimeDetector()
        regime, _ = detector.detect_regime(df, verbose=False)
        print(f"   ✅ Market regime: {regime}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    print("="*50)
    print("✅ ALL QUICK TESTS PASSED!")
    print("="*50)
    print("\nYour system is working correctly! 🎉")
    print("\nNext: Run full test suite with:")
    print("  python test_complete_system.py")
    return True

if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)
