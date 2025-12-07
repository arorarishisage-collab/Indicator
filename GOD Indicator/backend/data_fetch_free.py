"""
Alternative Data Fetching Module using Free APIs
Provides fallback data sources when yfinance is unavailable or rate-limited.
Supports: Alpha Vantage, Polygon.io, and synthetic data generation.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
import time
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FreeDataFetcher:
    """Fetch OHLCV data from free alternative sources."""
    
    # Free API endpoints
    ALPHA_VANTAGE_BASE = 'https://www.alphavantage.co/query'
    POLYGON_BASE = 'https://api.polygon.io/v1/open-close'
    
    def __init__(self, data_dir: str = './data'):
        """
        Initialize FreeDataFetcher.
        
        Args:
            data_dir: Directory to store downloaded data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Alpha Vantage requires API key (free tier available)
        self.alpha_vantage_key = self._get_alpha_vantage_key()
        # Polygon.io requires API key (free tier available)
        self.polygon_key = self._get_polygon_key()
    
    @staticmethod
    def _get_alpha_vantage_key() -> str:
        """Get Alpha Vantage API key from environment or create demo key."""
        import os
        key = os.environ.get('ALPHA_VANTAGE_KEY')
        if not key:
            # Demo key for testing (limited requests)
            key = 'demo'
            logger.info("Using Alpha Vantage demo key (limited to 5 requests/min)")
        return key
    
    @staticmethod
    def _get_polygon_key() -> str:
        """Get Polygon API key from environment."""
        import os
        key = os.environ.get('POLYGON_API_KEY')
        if not key:
            logger.warning("Polygon.io API key not set. Set POLYGON_API_KEY environment variable.")
        return key
    
    def fetch_from_alpha_vantage(
        self,
        symbol: str = 'GOOG',
        interval: str = '60min',
        max_retries: int = 3
    ) -> pd.DataFrame:
        """
        Fetch historical data from Alpha Vantage (free tier: up to 5 requests/min).
        
        Args:
            symbol: Stock ticker symbol
            interval: '60min' for hourly, '30min', '15min', '5min', '1min'
            max_retries: Number of retries on rate limit
        
        Returns:
            DataFrame with OHLCV data or empty DataFrame if failed
        """
        try:
            logger.info(f"Fetching {symbol} from Alpha Vantage (interval: {interval})...")
            
            params = {
                'function': 'FX_INTRADAY',  # Use FX for 24/5 trading
                'from_symbol': 'XAU',
                'to_symbol': 'USD',
                'interval': interval,
                'apikey': self.alpha_vantage_key,
                'outputsize': 'full'
            }
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(self.ALPHA_VANTAGE_BASE, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check for rate limit
                    if 'Note' in data:
                        logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 12  # Exponential backoff: 12, 24, 36 seconds
                            logger.info(f"Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error("Max retries exceeded")
                            return pd.DataFrame()
                    
                    # Extract time series data
                    key = f'Time Series FX ({interval})'
                    if key not in data:
                        logger.error(f"No data key '{key}' in response. Available keys: {list(data.keys())}")
                        return pd.DataFrame()
                    
                    time_series = data[key]
                    
                    # Convert to DataFrame
                    ohlcv_data = []
                    for timestamp, values in time_series.items():
                        ohlcv_data.append({
                            'Datetime': pd.to_datetime(timestamp),
                            'Open': float(values['1. open']),
                            'High': float(values['2. high']),
                            'Low': float(values['3. low']),
                            'Close': float(values['4. close']),
                            'Volume': 0  # FX data doesn't have volume
                        })
                    
                    df = pd.DataFrame(ohlcv_data)
                    df = df.sort_values('Datetime').reset_index(drop=True)
                    df.set_index('Datetime', inplace=True)
                    
                    logger.info(f"✓ Fetched {len(df)} candles from Alpha Vantage")
                    return df
                
                except requests.exceptions.Timeout:
                    logger.warning(f"Alpha Vantage request timeout (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
        
        except Exception as e:
            logger.error(f"Alpha Vantage fetch error: {e}")
        
        return pd.DataFrame()
    
    def fetch_from_polygon(
        self,
        symbol: str = 'GOOG',
        start_date: str = '2023-01-01',
        end_date: str = None
    ) -> pd.DataFrame:
        """
        Fetch historical data from Polygon.io (free tier: up to 5 API calls/min).
        
        Args:
            symbol: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            DataFrame with OHLCV data or empty DataFrame if failed
        """
        if not self.polygon_key:
            logger.error("Polygon API key not configured")
            return pd.DataFrame()
        
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Fetching {symbol} from Polygon.io ({start_date} to {end_date})...")
            
            # For daily data (simplification)
            current_date = pd.to_datetime(start_date)
            end_date_obj = pd.to_datetime(end_date)
            
            all_data = []
            
            while current_date <= end_date_obj:
                date_str = current_date.strftime('%Y-%m-%d')
                
                params = {
                    'adjusted': 'true',
                    'apiKey': self.polygon_key
                }
                
                url = f"{self.POLYGON_BASE}/{symbol}/{date_str}"
                
                try:
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get('status') == 'OK':
                        all_data.append({
                            'Datetime': pd.to_datetime(date_str),
                            'Open': data['o'],
                            'High': data['h'],
                            'Low': data['l'],
                            'Close': data['c'],
                            'Volume': data.get('v', 0)
                        })
                
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        logger.warning("Polygon rate limit hit, waiting...")
                        time.sleep(12)
                        continue
                    elif e.response.status_code == 404:
                        logger.debug(f"No data for {date_str}")
                    else:
                        logger.error(f"Polygon API error: {e}")
                        break
                
                current_date += timedelta(days=1)
            
            if all_data:
                df = pd.DataFrame(all_data)
                df = df.sort_values('Datetime').reset_index(drop=True)
                df.set_index('Datetime', inplace=True)
                logger.info(f"✓ Fetched {len(df)} candles from Polygon.io")
                return df
        
        except Exception as e:
            logger.error(f"Polygon.io fetch error: {e}")
        
        return pd.DataFrame()
    
    def generate_synthetic_data(
        self,
        symbol: str = 'GC=F',
        start_date: str = '2023-01-01',
        end_date: str = None,
        base_price: float = 2000.0,
        volatility: float = 0.02,
        num_candles: int = 1000
    ) -> pd.DataFrame:
        """
        Generate synthetic OHLCV data using Geometric Brownian Motion.
        Useful for testing when APIs are unavailable.
        
        Args:
            symbol: Ticker symbol (for reference only)
            start_date: Start date
            end_date: End date
            base_price: Starting price level
            volatility: Daily volatility (default: 2%)
            num_candles: Number of candles to generate
        
        Returns:
            DataFrame with realistic OHLCV data
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Generating {num_candles} synthetic candles for {symbol}...")
        
        # Generate dates (hourly candles, assuming 24/5 trading)
        start = pd.to_datetime(start_date)
        dates = pd.date_range(start=start, periods=num_candles, freq='H')
        
        # GBM parameters
        mu = 0.0001  # Small positive drift
        sigma = volatility / np.sqrt(252 * 24)  # Hourly volatility
        
        # Generate price movements
        prices = [base_price]
        for _ in range(num_candles - 1):
            dW = np.random.standard_normal()
            price_change = mu * prices[-1] + sigma * prices[-1] * dW
            prices.append(prices[-1] + price_change)
        
        prices = np.array(prices)
        
        # Generate OHLC from prices (simplified)
        ohlcv_data = []
        for i, (date, close_price) in enumerate(zip(dates, prices)):
            # Add intra-candle volatility
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
        
        logger.info(f"✓ Generated {len(df)} synthetic candles (Price range: ${df['Close'].min():.2f} - ${df['Close'].max():.2f})")
        return df
    
    def add_technical_indicators(self, df: pd.DataFrame, fast_ema: int = 30, slow_ema: int = 200) -> pd.DataFrame:
        """
        Add basic technical indicators to the DataFrame.
        
        Args:
            df: OHLCV DataFrame
            fast_ema: Period for fast EMA
            slow_ema: Period for slow EMA
        
        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()
        
        # EMA indicators
        df['EMA_30'] = df['Close'].ewm(span=fast_ema, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=slow_ema, adjust=False).mean()
        
        # ATR
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df


def load_demo_data_free(
    use_synthetic: bool = False,
    num_candles: int = 1000
) -> pd.DataFrame:
    """
    Load demo data using free API or synthetic generation.
    
    Args:
        use_synthetic: If True, generate synthetic data; otherwise try Alpha Vantage
        num_candles: Number of candles to load/generate
    
    Returns:
        DataFrame with OHLCV data
    """
    fetcher = FreeDataFetcher()
    
    if use_synthetic:
        logger.info("Using synthetic data generation...")
        df = fetcher.generate_synthetic_data(num_candles=num_candles)
    else:
        # Try Alpha Vantage first
        logger.info("Attempting to fetch from Alpha Vantage...")
        df = fetcher.fetch_from_alpha_vantage(interval='60min')
        
        # Fallback to synthetic if Alpha Vantage fails
        if df.empty:
            logger.warning("Alpha Vantage failed, generating synthetic data...")
            df = fetcher.generate_synthetic_data(num_candles=num_candles)
    
    if df.empty:
        logger.error("Failed to load any data")
        return pd.DataFrame()
    
    # Add indicators
    df = fetcher.add_technical_indicators(df)
    
    # Keep last N candles
    df = df.tail(num_candles)
    
    logger.info(f"✓ Loaded {len(df)} candles")
    return df


if __name__ == "__main__":
    # Example: Generate synthetic data
    fetcher = FreeDataFetcher()
    
    print("\n1. Generating synthetic data...")
    df_synthetic = fetcher.generate_synthetic_data(num_candles=500)
    df_synthetic = fetcher.add_technical_indicators(df_synthetic)
    print(df_synthetic.head())
    print(f"Shape: {df_synthetic.shape}")
    
    print("\n2. Attempting Alpha Vantage fetch...")
    df_av = fetcher.fetch_from_alpha_vantage()
    if not df_av.empty:
        print(df_av.head())
    else:
        print("Alpha Vantage fetch failed")
