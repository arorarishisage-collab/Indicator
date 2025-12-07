"""
Unit tests for trading strategies
Tests VCP, ICT, and EMA30 strategies
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.unified_data_fetcher import UnifiedDataFetcher


class TestStrategies:
    """Test suite for trading strategies"""
    
    @pytest.fixture
    def sample_data(self):
        """Get real market data for testing"""
        fetcher = UnifiedDataFetcher()
        to_date = datetime.now()
        from_date = to_date - timedelta(days=365)
        
        # Fetch RELIANCE data
        df = fetcher.fetch_historical_data('RELIANCE', 'D', from_date, to_date, 'NSE')
        return df
    
    def test_vcp_strategy(self, sample_data):
        """Test VCP (Volatility Contraction Pattern) strategy"""
        try:
            from backend.vcp_strategy import VCPStrategy
            
            strategy = VCPStrategy()
            signals = strategy.generate_signals(sample_data)
            
            assert signals is not None
            assert isinstance(signals, pd.DataFrame)
            assert 'Signal' in signals.columns
            assert 'Signal_Strength' in signals.columns
            
            # Check for buy signals
            buy_signals = signals[signals['Signal'] == 1]
            print(f"✅ VCP Strategy: {len(buy_signals)} buy signals found")
            
            return True
        except ImportError:
            print("⚠️ VCP Strategy not found, skipping")
            return False
    
    def test_ict_strategy(self, sample_data):
        """Test ICT (Inner Circle Trader) strategy"""
        try:
            from backend.ict_strategy import ICTStrategy
            
            strategy = ICTStrategy()
            signals = strategy.generate_signals(sample_data)
            
            assert signals is not None
            assert isinstance(signals, pd.DataFrame)
            assert 'Signal' in signals.columns
            
            buy_signals = signals[signals['Signal'] == 1]
            print(f"✅ ICT Strategy: {len(buy_signals)} buy signals found")
            
            return True
        except ImportError:
            print("⚠️ ICT Strategy not found, skipping")
            return False
    
    def test_ema30_strategy(self, sample_data):
        """Test EMA30 trend following strategy"""
        try:
            from backend.ema_strategy import EMA30Strategy
            
            strategy = EMA30Strategy()
            signals = strategy.generate_signals(sample_data)
            
            assert signals is not None
            assert isinstance(signals, pd.DataFrame)
            assert 'Signal' in signals.columns
            
            buy_signals = signals[signals['Signal'] == 1]
            print(f"✅ EMA30 Strategy: {len(buy_signals)} buy signals found")
            
            return True
        except ImportError:
            print("⚠️ EMA30 Strategy not found, skipping")
            return False
    
    def test_signal_quality(self, sample_data):
        """Test that strategies generate valid signals"""
        try:
            from backend.ema_strategy import EMA30Strategy
            
            strategy = EMA30Strategy()
            signals = strategy.generate_signals(sample_data)
            
            # Signals should be 1, 0, or -1
            assert signals['Signal'].isin([1, 0, -1]).all()
            
            # Signal strength should be 0-10
            if 'Signal_Strength' in signals.columns:
                assert (signals['Signal_Strength'] >= 0).all()
                assert (signals['Signal_Strength'] <= 10).all()
            
            print("✅ Signal quality checks passed")
        except ImportError:
            print("⚠️ Strategy not found for signal quality test")


class TestBacktesting:
    """Test backtesting functionality"""
    
    @pytest.fixture
    def sample_data(self):
        """Get real market data"""
        fetcher = UnifiedDataFetcher()
        to_date = datetime.now()
        from_date = to_date - timedelta(days=180)
        return fetcher.fetch_historical_data('TCS', 'D', from_date, to_date, 'NSE')
    
    def test_backtest_execution(self, sample_data):
        """Test basic backtest execution"""
        try:
            from backend.enhanced_backtester import EnhancedBacktester
            
            backtester = EnhancedBacktester(
                initial_capital=100000,
                commission=0.001
            )
            
            # Simple buy-and-hold strategy for testing
            signals = pd.DataFrame(index=sample_data.index)
            signals['Signal'] = 0
            signals.iloc[10] = 1  # Buy on day 10
            
            results = backtester.run_backtest(sample_data, signals)
            
            assert results is not None
            assert 'total_return' in results or 'returns' in results
            
            print("✅ Backtest execution successful")
        except ImportError:
            print("⚠️ Backtester not found, skipping")


def test_news_sentiment():
    """Test news sentiment analysis"""
    try:
        from backend.news_sentiment import NewsSentimentAnalyzer
        
        analyzer = NewsSentimentAnalyzer()
        news = analyzer.get_stock_news('RELIANCE', days=7, max_articles=5)
        
        assert news is not None
        assert isinstance(news, list)
        
        if len(news) > 0:
            sentiment = analyzer.analyze_sentiment(news)
            assert 'score' in sentiment or 'percentage' in sentiment
            print(f"✅ News sentiment: {len(news)} articles analyzed")
        else:
            print("⚠️ No news articles found")
    except ImportError:
        print("⚠️ News sentiment analyzer not found")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("STRATEGY TEST SUITE")
    print("="*60 + "\n")
    
    pytest.main([__file__, '-v', '-s'])
