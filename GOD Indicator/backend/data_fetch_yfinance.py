"""Simple yfinance data fetcher for unified_data_fetcher"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


class YFinanceDataFetcher:
    """Simple yfinance wrapper"""
    
    def __init__(self):
        pass
    
    def fetch_historical_data(self, symbol, period='1y', interval='1d', start_date=None, end_date=None):
        """
        Fetch historical data using yfinance
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'RELIANCE.NS')
            period: Period string ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            interval: Interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
            start_date: Start date (datetime or string)
            end_date: End date (datetime or string)
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            if start_date and end_date:
                df = ticker.history(start=start_date, end=end_date, interval=interval)
            else:
                df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                return pd.DataFrame()
            
            # Standardize column names
            df = df.rename(columns={
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
            
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
        except Exception as e:
            print(f"yfinance error for {symbol}: {e}")
            return pd.DataFrame()


__all__ = ['YFinanceDataFetcher']

