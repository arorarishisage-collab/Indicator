"""
Data Fetching Module for XAU/USD Trading Signal System
Handles historical and live OHLCV data retrieval from multiple sources.
Includes fallback to free APIs and synthetic data generation.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from pathlib import Path
import logging

from backend.technical_indicators import TechnicalIndicators

from backend.technical_indicators import TechnicalIndicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetch and manage OHLCV data for XAU/USD (Gold) forex trading."""
    
    GOLD_TICKER = 'GC=F'
    SYMBOL_MAPPING = {
        'XAUUSD': 'GC=F',
        'GOLD': 'GC=F',
        'BTC': 'BTC-USD',
        'BTCUSD': 'BTC-USD',
        'ETH': 'ETH-USD',
        'EURUSD': 'EURUSD=X',
        'GBPUSD': 'GBPUSD=X',
        'USDJPY': 'USDJPY=X',
    }
    
    def __init__(self, data_dir: str = './data', use_fallback: bool = True):
        """
        Initialize DataFetcher.
        
        Args:
            data_dir: Directory to store downloaded data
            use_fallback: Use free API/synthetic data if yfinance fails
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.use_fallback = use_fallback
    
    def _try_free_fetch(
        self,
        symbol: str = GOLD_TICKER,
        start_date: str = '2020-01-01',
        end_date: str = None,
        interval: str = '1h'
    ) -> pd.DataFrame:
        """
        Fallback to free data fetch if yfinance fails.
        
        Args:
            symbol: Ticker symbol
            start_date: Start date
            end_date: End date
            interval: Candlestick interval
        
        Returns:
            DataFrame with OHLCV data (synthetic if APIs unavailable)
        """
        try:
            from backend.data_fetch_free import FreeDataFetcher
            
            logger.info("Attempting fallback to free data sources...")
            fetcher = FreeDataFetcher()
            
            # Try Alpha Vantage first
            logger.info("Trying Alpha Vantage...")
            df = fetcher.fetch_from_alpha_vantage(interval='60min')
            
            if df.empty:
                logger.warning("Alpha Vantage unavailable, generating synthetic data...")
                df = fetcher.generate_synthetic_data(
                    base_price=2000.0,
                    num_candles=1000
                )
            
            return df
        
        except ImportError:
            logger.debug("data_fetch_free module not available")
        except Exception as e:
            logger.warning(f"Free data fetch error: {e}")
        
        # Generate synthetic data as last resort
        logger.info("Generating synthetic data for testing...")
        return self._generate_synthetic_data_internal()

    @classmethod
    def get_yfinance_ticker(cls, symbol: str) -> str:
        """Map generic symbols to Yahoo Finance tickers."""
        if not symbol:
            return cls.GOLD_TICKER
        return cls.SYMBOL_MAPPING.get(symbol.upper(), symbol)
    
    @staticmethod
    def _generate_synthetic_data_internal(
        base_price: float = 2000.0,
        volatility: float = 0.02,
        num_candles: int = 500
    ) -> pd.DataFrame:
        """
        Generate synthetic OHLCV data using Geometric Brownian Motion.
        
        Args:
            base_price: Starting price
            volatility: Daily volatility
            num_candles: Number of candles to generate
        
        Returns:
            DataFrame with synthetic OHLCV data
        """
        logger.info(f"Generating {num_candles} synthetic candles...")
        
        # Generate dates (hourly candles, 24/5 trading)
        start = datetime.now() - timedelta(days=30)
        dates = pd.date_range(start=start, periods=num_candles, freq='H')
        
        # GBM parameters
        mu = 0.0001
        sigma = volatility / np.sqrt(252 * 24)
        
        # Generate prices
        prices = [base_price]
        for _ in range(num_candles - 1):
            dW = np.random.standard_normal()
            price_change = mu * prices[-1] + sigma * prices[-1] * dW
            prices.append(prices[-1] + price_change)
        
        prices = np.array(prices)
        
        # Generate OHLC
        ohlcv_data = []
        for date, close_price in zip(dates, prices):
            open_price = close_price + np.random.normal(0, close_price * sigma * 0.5)
            high_price = max(open_price, close_price) + np.random.uniform(0, close_price * sigma)
            low_price = min(open_price, close_price) - np.random.uniform(0, close_price * sigma)
            volume = np.random.uniform(1000, 10000)
            
            ohlcv_data.append({
                'Datetime': date,
                'Open': open_price,
                'High': high_price,
                'Low': low_price,
                'Close': close_price,
                'Volume': volume
            })
        
        df = pd.DataFrame(ohlcv_data)
        df.set_index('Datetime', inplace=True)
        logger.info(f"✓ Generated {len(df)} synthetic candles (${df['Close'].min():.2f} - ${df['Close'].max():.2f})")
        return df
    
    def fetch_historical_data(
        self,
        symbol: str = GOLD_TICKER,
        start_date: str = None,
        end_date: str = None,
        interval: str = '1h',
        period: str = '10y',
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from Yahoo Finance with fallback to free APIs.
        
        Args:
            symbol: Ticker symbol (default: GC=F for gold)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
            interval: Candlestick interval ('1h', '4h', '1d', etc.)
            use_cache: Use cached CSV if available
        
        Returns:
            DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume, Adj Close)
        """
        ticker_symbol = self.get_yfinance_ticker(symbol)
        use_period = not (start_date and end_date)

        if end_date is None and not use_period:
            end_date = datetime.now().strftime('%Y-%m-%d')

        if use_period:
            cache_key = f"{symbol}_{interval}_{period}"
        else:
            cache_key = f"{symbol}_{interval}_{start_date}_{end_date}"
        cache_file = self.data_dir / f'{cache_key}.csv'
        
        # Load from cache if available
        if use_cache and cache_file.exists():
            logger.info(f"Loading cached data from {cache_file}")
            try:
                df = pd.read_csv(cache_file, index_col='Datetime', parse_dates=True)
                return df
            except Exception as e:
                logger.warning(f"Cache load error: {e}, re-fetching data...")
        
        # Fetch from Yahoo Finance
        logger.info(
            f"Fetching {symbol} ({ticker_symbol}) data with interval={interval}"
            + (f", period={period}" if use_period else f", range={start_date}→{end_date}")
        )
        try:
            if use_period:
                df = yf.download(
                    ticker_symbol,
                    period=period,
                    interval=interval,
                    progress=False
                )
            else:
                df = yf.download(
                    ticker_symbol,
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    progress=False
                )
            
            # Ensure proper column naming and index
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.index.name = 'Datetime'
            df = df.reset_index()
            
            # Handle column name variations
            if 'Adj Close' in df.columns:
                df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']]
            else:
                df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            df.set_index('Datetime', inplace=True)
            
            # Remove NaN rows
            df.dropna(subset=['Close'], inplace=True)
            
            # Cache the data
            df.to_csv(cache_file)
            logger.info(f"Data cached to {cache_file}. Shape: {df.shape}")
            
            return df
        
        except Exception as e:
            logger.warning(f"Yahoo Finance fetch failed: {e}")
            
            # Use fallback if enabled
            if self.use_fallback:
                logger.info("Using fallback data source...")
                return self._try_free_fetch(symbol, start_date or '', end_date, interval)
            else:
                logger.error(f"Error fetching data: {e}")
                raise

    def fetch_live_candle(self, symbol: str, interval: str = '1h') -> dict:
        """Fetch the latest completed candle for live workflows."""
        try:
            ticker_symbol = self.get_yfinance_ticker(symbol)
            df = yf.download(
                ticker_symbol,
                period='7d',
                interval=interval,
                progress=False
            )
            if df is None or df.empty:
                return None

            latest = df.iloc[-1]
            return {
                'symbol': symbol,
                'timestamp': df.index[-1],
                'open': latest['Open'],
                'high': latest['High'],
                'low': latest['Low'],
                'close': latest['Close'],
                'volume': latest['Volume'],
            }
        except Exception as exc:
            logger.error(f"Error fetching live candle for {symbol}: {exc}")
            return None

    def fetch_multiple_symbols(self, symbols, period='10y', interval='1d') -> dict:
        """Fetch historical data for multiple symbols."""
        results = {}
        for sym in symbols:
            try:
                results[sym] = self.fetch_historical_data(
                    symbol=sym,
                    period=period,
                    interval=interval,
                    use_cache=False
                )
            except Exception as exc:
                logger.warning(f"Failed to fetch {sym}: {exc}")
        return results
    
    def fetch_multiple_timeframes(
        self,
        symbol: str = GOLD_TICKER,
        timeframes: list = ['1h', '4h'],
        start_date: str = '2020-01-01',
        end_date: str = None
    ) -> dict:
        """
        Fetch data for multiple timeframes.
        
        Args:
            symbol: Ticker symbol
            timeframes: List of intervals (e.g., ['1h', '4h', '1d'])
            start_date: Start date
            end_date: End date
        
        Returns:
            Dictionary with timeframe keys and DataFrame values
        """
        data_dict = {}
        for tf in timeframes:
            try:
                data_dict[tf] = self.fetch_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=tf
                )
                logger.info(f"✓ Loaded {tf} data: {data_dict[tf].shape[0]} candles")
            except Exception as e:
                logger.error(f"✗ Failed to fetch {tf}: {e}")
        
        return data_dict
    
    def add_technical_indicators(self, df: pd.DataFrame, fast_ema: int = 30, slow_ema: int = 200) -> pd.DataFrame:
        """
        Add basic technical indicators to the DataFrame.
        
        Args:
            df: OHLCV DataFrame
            fast_ema: Period for fast EMA (default: 30)
            slow_ema: Period for slow EMA (default: 200)
        
        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()
        
        df = TechnicalIndicators.ema(df, period=fast_ema, name='EMA_30')
        df = TechnicalIndicators.ema(df, period=slow_ema, name='EMA_200')
        df = TechnicalIndicators.atr(df, period=14, name='ATR')
        df = TechnicalIndicators.rsi(df, period=14, name='RSI')
        
        return df

    add_indicators = add_technical_indicators
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate data quality.
        
        Args:
            df: DataFrame to validate
        
        Returns:
            True if data is valid, False otherwise
        """
        issues = []
        
        # Check for required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            issues.append(f"Missing columns. Required: {required_cols}")
        
        # Check for NaNs in price columns
        if df[['Open', 'High', 'Low', 'Close']].isnull().any().any():
            issues.append("NaN values found in OHLC columns")
        
        # Check for inverted OHLC
        if (df['High'] < df['Low']).any():
            issues.append("High < Low detected (inverted OHLC)")
        
        if (df['Close'] < df['Low']).any() or (df['Close'] > df['High']).any():
            issues.append("Close outside High-Low range")
        
        if issues:
            logger.warning(f"Data validation issues:\n" + "\n".join(issues))
            return False
        
        logger.info(f"✓ Data validation passed. Records: {len(df)}")
        return True


def load_demo_data(symbol: str = 'GC=F', years: int = 5, use_fallback: bool = True) -> pd.DataFrame:
    """
    Quick function to load 5 years of demo data for testing.
    Falls back to synthetic data if APIs unavailable.
    
    Args:
        symbol: Ticker symbol
        years: Number of years of historical data
        use_fallback: Use fallback data if primary source fails
    
    Returns:
        DataFrame with OHLCV data
    """
    fetcher = DataFetcher(use_fallback=use_fallback)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365*years)).strftime('%Y-%m-%d')
    
    try:
        df = fetcher.fetch_historical_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval='1h'
        )
    except Exception as e:
        logger.error(f"Failed to load demo data: {e}")
        if use_fallback:
            logger.info("Using synthetic data fallback...")
            df = DataFetcher._generate_synthetic_data_internal(num_candles=500)
        else:
            raise
    
    df = fetcher.add_technical_indicators(df)
    fetcher.validate_data(df)
    
    return df


if __name__ == "__main__":
    # Example usage
    fetcher = DataFetcher()
    
    # Fetch historical data
    df_1h = fetcher.fetch_historical_data(
        symbol='GC=F',
        start_date='2023-01-01',
        end_date='2024-12-31',
        interval='1h'
    )
    
    # Add indicators
    df_1h = fetcher.add_technical_indicators(df_1h)
    
    # Validate
    fetcher.validate_data(df_1h)
    
    print(f"\nLoaded {len(df_1h)} candles")
    print(df_1h.head())
