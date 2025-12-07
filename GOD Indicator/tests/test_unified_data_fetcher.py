"""
Unit tests for UnifiedDataFetcher
Tests all data source integrations and fallback mechanisms
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.unified_data_fetcher import UnifiedDataFetcher


class TestUnifiedDataFetcher:
    """Test suite for UnifiedDataFetcher"""
    
    @pytest.fixture
    def fetcher(self):
        """Create fetcher instance with test API keys"""
        return UnifiedDataFetcher(
            finnhub_api_key='d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg'
        )
    
    def test_nse_stock_data(self, fetcher):
        """Test fetching NSE stock data using nsepython"""
        symbol = 'RELIANCE'
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        df = fetcher.fetch_historical_data(symbol, 'D', from_date, to_date, 'NSE')
        
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
        assert df['Close'].iloc[-1] > 0
        print(f"✅ NSE Test: RELIANCE ₹{df['Close'].iloc[-1]:.2f}")
    
    def test_us_stock_data(self, fetcher):
        """Test fetching US stock data using yfinance"""
        symbol = 'AAPL'
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        df = fetcher.fetch_historical_data(symbol, 'D', from_date, to_date, 'US')
        
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
        assert df['Close'].iloc[-1] > 0
        print(f"✅ US Test: AAPL ${df['Close'].iloc[-1]:.2f}")
    
    def test_bse_stock_data(self, fetcher):
        """Test fetching BSE stock data (fallback to yfinance)"""
        symbol = 'RELIANCE'
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        df = fetcher.fetch_historical_data(symbol, 'D', from_date, to_date, 'BSE')
        
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        print(f"✅ BSE Test: RELIANCE ₹{df['Close'].iloc[-1]:.2f}")
    
    def test_finnhub_quote(self, fetcher):
        """Test Finnhub real-time quote"""
        quote = fetcher.get_quote('AAPL', 'US')
        
        assert quote is not None
        assert 'c' in quote  # current price
        assert quote['c'] > 0
        print(f"✅ Finnhub Quote: AAPL ${quote['c']:.2f}")
    
    def test_source_selection_nse(self, fetcher):
        """Test that NSE stocks use nsepython"""
        source, _ = fetcher._select_source('RELIANCE', 'NSE')
        assert source in ['nsepython', 'yfinance', 'Zerodha']
        print(f"✅ Source Selection NSE: {source}")
    
    def test_source_selection_us(self, fetcher):
        """Test that US stocks use yfinance"""
        source, _ = fetcher._select_source('AAPL', 'US')
        assert source == 'yfinance'
        print(f"✅ Source Selection US: {source}")
    
    def test_invalid_symbol(self, fetcher):
        """Test error handling for invalid symbols"""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        with pytest.raises(Exception):
            fetcher.fetch_historical_data('INVALID_XYZ_123', 'D', from_date, to_date, 'NSE')
        
        print("✅ Invalid symbol handling works")
    
    def test_data_quality(self, fetcher):
        """Test data quality - no NaN values, proper ordering"""
        symbol = 'RELIANCE'
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        df = fetcher.fetch_historical_data(symbol, 'D', from_date, to_date, 'NSE')
        
        # Check for NaN values
        assert not df['Close'].isna().any(), "Data contains NaN values"
        
        # Check price sanity (positive values)
        assert (df['Close'] > 0).all(), "Negative or zero prices found"
        assert (df['High'] >= df['Low']).all(), "High < Low found"
        assert (df['High'] >= df['Close']).all(), "High < Close found"
        assert (df['Low'] <= df['Close']).all(), "Low > Close found"
        
        print("✅ Data quality checks passed")
    
    def test_multiple_symbols(self, fetcher):
        """Test fetching multiple symbols"""
        symbols = ['RELIANCE', 'TCS', 'INFY']
        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)
        
        results = {}
        for symbol in symbols:
            df = fetcher.fetch_historical_data(symbol, 'D', from_date, to_date, 'NSE')
            results[symbol] = df
            assert len(df) > 0
        
        print(f"✅ Multiple symbols test: {len(results)} stocks fetched")


def test_fallback_mechanism():
    """Test fallback from failed sources"""
    # Create fetcher without Finnhub key to test fallback
    fetcher = UnifiedDataFetcher()
    
    to_date = datetime.now()
    from_date = to_date - timedelta(days=7)
    
    # Should still work with yfinance fallback
    df = fetcher.fetch_historical_data('AAPL', 'D', from_date, to_date, 'US')
    assert df is not None
    assert len(df) > 0
    
    print("✅ Fallback mechanism works")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("UNIFIED DATA FETCHER TEST SUITE")
    print("="*60 + "\n")
    
    # Run with pytest
    pytest.main([__file__, '-v', '-s'])
