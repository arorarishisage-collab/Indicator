#!/usr/bin/env python3
"""
📊 Bank Nifty Custom Data Loader
Loads data from GitHub CSV or Yahoo Finance with validation
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BankNiftyDataLoader:
    """Load Bank Nifty data from CSV or Yahoo Finance."""
    
    # Direct CSV URLs from GitHub
    CSV_URLS = {
        '1m': 'https://raw.githubusercontent.com/sandeepkapri/BankNifty-Data/main/bank-nifty-1m-data.csv',
        '5m': 'https://raw.githubusercontent.com/sandeepkapri/BankNifty-Data/main/bank-nifty-5m-data.csv',
        '15m': 'https://raw.githubusercontent.com/sandeepkapri/BankNifty-Data/main/bank-nifty-15m-data.csv',
        '1h': 'https://raw.githubusercontent.com/sandeepkapri/BankNifty-Data/main/bank-nifty-1h-data.csv',
        '2h': 'https://raw.githubusercontent.com/sandeepkapri/BankNifty-Data/main/bank-nifty-2h-data.csv',
        '3h': 'https://raw.githubusercontent.com/sandeepkapri/BankNifty-Data/main/bank-nifty-3h-data.csv',
        '1d': 'https://raw.githubusercontent.com/sandeepkapri/BankNifty-Data/main/bank-nifty-1d-data.csv'
    }
    
    def __init__(self, interval: str = '1h', use_cache: bool = True):
        """
        Initialize Bank Nifty data loader.
        
        Args:
            interval: Data interval (1m, 5m, 15m, 1h, 2h, 3h, 1d)
            use_cache: Whether to cache downloaded data
        """
        self.interval = interval
        self.use_cache = use_cache
        self.cache_dir = Path('data') / 'banknifty'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_from_github(self) -> pd.DataFrame:
        """Load Bank Nifty data from GitHub CSV."""
        
        if self.interval not in self.CSV_URLS:
            raise ValueError(f"Invalid interval: {self.interval}. Choose from {list(self.CSV_URLS.keys())}")
        
        cache_file = self.cache_dir / f'banknifty_{self.interval}.csv'
        
        # Check cache first
        if self.use_cache and cache_file.exists():
            logger.info(f"Loading cached Bank Nifty data: {cache_file}")
            try:
                df = pd.read_csv(cache_file)
                df['DateTime'] = pd.to_datetime(df['DateTime'])
                df.set_index('DateTime', inplace=True)
                logger.info(f"✓ Loaded {len(df)} candles from cache")
                return df
            except Exception as e:
                logger.warning(f"Cache read failed: {e}, downloading fresh data...")
        
        # Download from GitHub
        url = self.CSV_URLS[self.interval]
        logger.info(f"Downloading Bank Nifty {self.interval} data from GitHub...")
        
        try:
            df = pd.read_csv(url)
            
            # Parse datetime (format: DD-MM-YYYY HH:MM:SS)
            if 'Date' in df.columns and 'Time' in df.columns:
                df['DateTime'] = pd.to_datetime(
                    df['Date'] + ' ' + df['Time'],
                    format='%d-%m-%Y %H:%M:%S'
                )
            elif 'Date' in df.columns:
                df['DateTime'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
            else:
                raise ValueError("CSV missing Date/Time columns")
            
            # Standardize column names (OHLCV)
            df = df.rename(columns={
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
            
            # Add Volume if missing (Bank Nifty data doesn't have volume)
            if 'Volume' not in df.columns:
                df['Volume'] = 0
            
            # Set DateTime as index
            df.set_index('DateTime', inplace=True)
            
            # Keep only OHLCV columns
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            # Remove any duplicates
            df = df[~df.index.duplicated(keep='first')]
            
            # Sort by datetime
            df.sort_index(inplace=True)
            
            logger.info(f"✓ Downloaded {len(df)} candles ({df.index[0]} to {df.index[-1]})")
            
            # Cache for future use
            if self.use_cache:
                df.to_csv(cache_file)
                logger.info(f"✓ Cached to {cache_file}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to download Bank Nifty data: {e}")
            raise
    
    def load_from_yahoo(self) -> pd.DataFrame:
        """Fallback: Load Bank Nifty from Yahoo Finance."""
        from backend.data_fetch_yfinance import YFinanceDataFetcher
        
        logger.info("Loading Bank Nifty from Yahoo Finance (^NSEBANK)...")
        
        fetcher = YFinanceDataFetcher(
            symbol='^NSEBANK',
            interval=self.interval,
            period='max',
            use_cache=self.use_cache
        )
        
        df = fetcher.get_data()
        
        if df is not None and not df.empty:
            logger.info(f"✓ Loaded {len(df)} candles from Yahoo Finance")
            return df
        
        logger.error("Yahoo Finance fetch failed")
        return None
    
    def load(self, fallback_to_yahoo: bool = True) -> pd.DataFrame:
        """
        Load Bank Nifty data with fallback options.
        
        Args:
            fallback_to_yahoo: If GitHub fails, try Yahoo Finance
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Try GitHub first (more reliable for Bank Nifty)
            df = self.load_from_github()
            
            if df is not None and not df.empty:
                self._validate_data(df)
                return df
                
        except Exception as e:
            logger.warning(f"GitHub load failed: {e}")
        
        # Fallback to Yahoo Finance
        if fallback_to_yahoo:
            try:
                df = self.load_from_yahoo()
                
                if df is not None and not df.empty:
                    self._validate_data(df)
                    return df
                    
            except Exception as e:
                logger.error(f"Yahoo Finance fallback failed: {e}")
        
        raise ValueError("All data sources failed")
    
    def _validate_data(self, df: pd.DataFrame):
        """Validate loaded data."""
        required_cols = ['Open', 'High', 'Low', 'Close']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        if df.empty:
            raise ValueError("DataFrame is empty")
        
        # Check for reasonable price values
        if (df['Close'] <= 0).any():
            raise ValueError("Invalid prices detected (<=0)")
        
        logger.info(f"✓ Data validation passed: {len(df)} candles")


def compare_data_sources(interval: str = '1h'):
    """Compare Bank Nifty data from GitHub vs Yahoo Finance."""
    
    print(f"\n{'='*80}")
    print(f"📊 Comparing Bank Nifty Data Sources ({interval})")
    print('='*80 + '\n')
    
    loader = BankNiftyDataLoader(interval=interval)
    
    # Load from GitHub
    print("1️⃣ Loading from GitHub CSV...")
    try:
        github_df = loader.load_from_github()
        print(f"✓ GitHub data: {len(github_df)} candles")
        print(f"  Date range: {github_df.index[0]} to {github_df.index[-1]}")
        print(f"  Sample prices: {github_df['Close'].iloc[-5:].values}")
    except Exception as e:
        print(f"❌ GitHub failed: {e}")
        github_df = None
    
    # Load from Yahoo
    print("\n2️⃣ Loading from Yahoo Finance...")
    try:
        yahoo_df = loader.load_from_yahoo()
        print(f"✓ Yahoo data: {len(yahoo_df)} candles")
        print(f"  Date range: {yahoo_df.index[0]} to {yahoo_df.index[-1]}")
        print(f"  Sample prices: {yahoo_df['Close'].iloc[-5:].values}")
    except Exception as e:
        print(f"❌ Yahoo failed: {e}")
        yahoo_df = None
    
    # Compare if both loaded
    if github_df is not None and yahoo_df is not None:
        print("\n3️⃣ Comparison:")
        
        # Find overlapping dates
        common_dates = github_df.index.intersection(yahoo_df.index)
        
        if len(common_dates) > 0:
            print(f"  Common dates: {len(common_dates)}")
            
            # Compare prices on common dates
            github_subset = github_df.loc[common_dates, 'Close']
            yahoo_subset = yahoo_df.loc[common_dates, 'Close']
            
            diff = (github_subset - yahoo_subset).abs()
            max_diff = diff.max()
            avg_diff = diff.mean()
            
            print(f"  Max price difference: ₹{max_diff:.2f}")
            print(f"  Avg price difference: ₹{avg_diff:.2f}")
            
            if avg_diff < 1.0:
                print("  ✅ Data sources are consistent!")
            else:
                print("  ⚠️ Significant differences detected")
        else:
            print("  ⚠️ No overlapping dates found")
    
    print('\n' + '='*80)


if __name__ == '__main__':
    # Compare data sources
    compare_data_sources(interval='1h')
    
    # Test loading
    print("\n\n" + "="*80)
    print("🧪 Testing Data Loader")
    print("="*80 + "\n")
    
    loader = BankNiftyDataLoader(interval='1h')
    df = loader.load()
    
    print(f"\n✅ Successfully loaded {len(df)} candles")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"\nLast 5 candles:")
    print(df.tail())
