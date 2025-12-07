"""
Data Manager - Handles live and historical market data acquisition
Supports NSE stocks, multiple timeframes, and real-time updates via yfinance
"""

import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime, timedelta
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataManager:
    """
    Professional data acquisition layer for backtesting and live trading.
    
    Features:
    - Live market data fetching (yfinance)
    - Historical data download
    - Multiple timeframes (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)
    - Data caching for performance
    - NSE stock support (append .NS for NSE symbols)
    - Data validation and cleaning
    """
    
    def __init__(self, cache_dir: str = 'data/cache', use_cache: bool = True):
        """
        Initialize DataManager
        
        Args:
            cache_dir: Directory to cache downloaded data
            use_cache: Whether to use cached data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.use_cache = use_cache
        
        # Common NSE stocks (can be expanded)
        self.nse_stocks = {
            'RELIANCE': 'RELIANCE.NS',
            'TCS': 'TCS.NS',
            'INFY': 'INFOSY.NS',
            'HDFC': 'HDFC.NS',
            'ICICIBANK': 'ICICIBANK.NS',
            'LT': 'LT.NS',
            'MARUTI': 'MARUTI.NS',
            'BAJAJFINSV': 'BAJAJFINSV.NS',
            'WIPRO': 'WIPRO.NS',
            'DRREDDY': 'DRREDDY.NS',
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _infer_datetime_column(self, columns: List[str]) -> Optional[str]:
        """Best-effort detection of the datetime column within a CSV."""
        candidates = {'datetime', 'date', 'timestamp', 'time'}
        for col in columns:
            if col.lower() in candidates:
                return col
        return None

    def _standardize_ohlcv_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename common OHLCV variations to canonical names."""
        column_map = {}
        for col in df.columns:
            key = col.strip().lower()
            if key in ('open', 'o'):
                column_map[col] = 'Open'
            elif key in ('high', 'h'):
                column_map[col] = 'High'
            elif key in ('low', 'l'):
                column_map[col] = 'Low'
            elif key in ('close', 'c', 'price', 'adj close', 'adj_close'):
                column_map[col] = 'Close'
            elif key in ('volume', 'vol', 'qty', 'shares'):
                column_map[col] = 'Volume'
        if column_map:
            df = df.rename(columns=column_map)
        if 'Volume' not in df.columns:
            df['Volume'] = 0
        return df

    def _period_to_timedelta(self, period: str) -> timedelta:
        """Convert strings like '1y', '6mo', '30d' into timedeltas."""
        if not period:
            return timedelta(days=365)
        period = period.strip().lower()
        unit = ''.join(filter(str.isalpha, period)) or 'd'
        value_str = period.replace(unit, '')
        value = int(value_str) if value_str else 1
        if unit in ('y', 'yr', 'yrs', 'year', 'years'):
            return timedelta(days=365 * value)
        if unit in ('mo', 'mon', 'month', 'months'):
            return timedelta(days=30 * value)
        if unit in ('w', 'wk', 'week', 'weeks'):
            return timedelta(weeks=value)
        if unit in ('h', 'hr', 'hour', 'hours'):
            return timedelta(hours=value)
        return timedelta(days=value)
    
    def get_cache_path(self, symbol: str, timeframe: str, start_date: str) -> Path:
        """Generate cache file path"""
        filename = f"{symbol}_{timeframe}_{start_date}.parquet"
        return self.cache_dir / filename
    
    def load_cached_data(self, symbol: str, timeframe: str, start_date: str) -> Optional[pd.DataFrame]:
        """Load data from cache if available"""
        if not self.use_cache:
            return None
        
        cache_path = self.get_cache_path(symbol, timeframe, start_date)
        if cache_path.exists():
            try:
                df = pd.read_parquet(cache_path)
                logger.info(f"✓ Loaded {len(df)} bars from cache: {cache_path}")
                return df
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
                return None
        
        return None
    
    def save_to_cache(self, df: pd.DataFrame, symbol: str, timeframe: str, start_date: str) -> None:
        """Save data to cache"""
        if not self.use_cache or df.empty:
            return
        
        try:
            cache_path = self.get_cache_path(symbol, timeframe, start_date)
            df.to_parquet(cache_path)
            logger.info(f"✓ Cached {len(df)} bars to: {cache_path}")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    def fetch_historical_data(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        timeframe: str = '1d',
        is_nse: bool = False
    ) -> pd.DataFrame:
        """
        Fetch historical data from yfinance
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE' or 'RELIANCE.NS')
            start_date: Start date (YYYY-MM-DD). Default: 1 year ago
            end_date: End date (YYYY-MM-DD). Default: today
            timeframe: Candle timeframe ('1m', '5m', '15m', '1h', '1d', '1wk', '1mo')
            is_nse: If True and symbol not in NSE format, append .NS
        
        Returns:
            DataFrame with OHLCV data
        """
        # Set defaults
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # Format symbol for NSE
        if is_nse and not symbol.endswith('.NS'):
            symbol = f"{symbol}.NS"
        
        # Check cache
        cached_df = self.load_cached_data(symbol, timeframe, start_date)
        if cached_df is not None:
            return cached_df
        
        try:
            logger.info(f"Downloading {symbol} data ({start_date} to {end_date}, {timeframe})...")

            df = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                interval=timeframe,
                progress=False
            )

            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.rename(columns=lambda c: c.strip())

            required = ['Open', 'High', 'Low', 'Close']
            missing = [col for col in required if col not in df.columns]
            if missing:
                available = ', '.join(df.columns.astype(str).tolist())
                raise ValueError(
                    f"Downloaded data for {symbol} missing columns {missing} (available: {available})"
                )

            if 'Adj Close' in df.columns:
                df = df.drop(columns=['Adj Close'])

            if 'Volume' not in df.columns:
                df['Volume'] = 0

            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

            df.index.name = 'DateTime'
            df = df.reset_index()
            df['DateTime'] = pd.to_datetime(df['DateTime'])

            logger.info(f"✓ Downloaded {len(df)} bars for {symbol}")

            self.save_to_cache(df, symbol, timeframe, start_date)

            return df

        except Exception as e:
            logger.error(f"Error downloading data for {symbol}: {e}")
            return pd.DataFrame()

    def load_csv(
        self,
        filepath: str,
        datetime_column: Optional[str] = None,
        timezone: Optional[str] = None,
        resample_to: Optional[str] = None
    ) -> pd.DataFrame:
        """Load OHLCV data from CSV uploads (NSE or custom)."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {filepath}")

        df = pd.read_csv(path)
        if df.empty:
            raise ValueError(f"CSV {filepath} is empty")

        datetime_column = datetime_column or self._infer_datetime_column(df.columns.tolist())
        if not datetime_column:
            raise ValueError("Unable to identify datetime column. Provide datetime_column explicitly.")

        df[datetime_column] = pd.to_datetime(df[datetime_column], errors='coerce')
        df = df.dropna(subset=[datetime_column])
        df = df.sort_values(datetime_column)
        df = df.reset_index(drop=True)

        if timezone:
            df[datetime_column] = (
                pd.to_datetime(df[datetime_column], utc=True)
                .dt.tz_convert(timezone)
                .dt.tz_localize(None)
            )

        df = self._standardize_ohlcv_columns(df)
        df = df.rename(columns={datetime_column: 'DateTime'})

        missing = [col for col in ['Open', 'High', 'Low', 'Close'] if col not in df.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']]

        if resample_to:
            df = self.resample_data(df, resample_to)

        logger.info(f"✓ Loaded {len(df)} rows from CSV: {filepath}")
        return df
    
    def fetch_live_data(self, symbol: str, is_nse: bool = False) -> Dict:
        """
        Fetch live market data for a symbol
        
        Args:
            symbol: Stock symbol
            is_nse: If True, append .NS
        
        Returns:
            Dictionary with live price data
        """
        if is_nse and not symbol.endswith('.NS'):
            symbol = f"{symbol}.NS"
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Extract live data
            live_data = {
                'symbol': symbol,
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'previous_close': info.get('previousClose', 0),
                'open': info.get('open', 0),
                'high': info.get('dayHigh', 0),
                'low': info.get('dayLow', 0),
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'timestamp': datetime.now().isoformat(),
            }
            
            logger.info(f"✓ Live data fetched for {symbol}: ₹{live_data['current_price']}")
            return live_data
        
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {e}")
            return {}
    
    def fetch_multiple_symbols(
        self,
        symbols: List[str],
        start_date: str = None,
        end_date: str = None,
        timeframe: str = '1d',
        is_nse: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple symbols
        
        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            timeframe: Candle timeframe
            is_nse: If True, treat as NSE symbols
        
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        data = {}
        for symbol in symbols:
            df = self.fetch_historical_data(symbol, start_date, end_date, timeframe, is_nse)
            if not df.empty:
                data[symbol] = df
        
        return data
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Validate OHLCV data
        
        Args:
            df: DataFrame to validate
        
        Returns:
            Tuple of (is_valid, message)
        """
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Check columns
        if not all(col in df.columns for col in required_cols):
            return False, f"Missing required columns. Need: {required_cols}"
        
        # Check for empty data
        if df.empty:
            return False, "DataFrame is empty"
        
        # Check data types
        for col in required_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                return False, f"Column {col} is not numeric"
        
        # Check for NaN values
        if df[required_cols].isna().any().any():
            return False, "Data contains NaN values"
        
        # Check OHLC logic
        if not (df['High'] >= df['Low']).all():
            return False, "High < Low in some bars"
        
        if not ((df['High'] >= df['Open']) & (df['High'] >= df['Close'])).all():
            return False, "High < Open/Close in some bars"
        
        if not ((df['Low'] <= df['Open']) & (df['Low'] <= df['Close'])).all():
            return False, "Low > Open/Close in some bars"
        
        return True, "✓ Data validation passed"
    
    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample OHLCV data to different timeframe
        
        Args:
            df: DataFrame with datetime index
            timeframe: Target timeframe (e.g., '5min', '1H', '1D')
        
        Returns:
            Resampled DataFrame
        """
        try:
            if 'DateTime' in df.columns:
                df = df.set_index('DateTime')
            
            resampled = pd.DataFrame({
                'Open': df['Open'].resample(timeframe).first(),
                'High': df['High'].resample(timeframe).max(),
                'Low': df['Low'].resample(timeframe).min(),
                'Close': df['Close'].resample(timeframe).last(),
                'Volume': df['Volume'].resample(timeframe).sum(),
            })
            
            resampled = resampled.dropna()
            resampled = resampled.reset_index()
            
            logger.info(f"✓ Resampled data to {timeframe}: {len(resampled)} bars")
            return resampled
        
        except Exception as e:
            logger.error(f"Resampling failed: {e}")
            return df
    
    def get_nse_stock(self, symbol: str) -> Optional[str]:
        """Get NSE symbol from common name"""
        return self.nse_stocks.get(symbol.upper())
    
    def list_available_nse_stocks(self) -> List[str]:
        """List all available NSE stocks"""
        return list(self.nse_stocks.keys())
    
    def export_data(self, df: pd.DataFrame, filepath: str) -> bool:
        """Export data to CSV"""
        try:
            df.to_csv(filepath, index=False)
            logger.info(f"✓ Data exported to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def load_source(self, source_config: Dict[str, Any], *, _depth: int = 0) -> pd.DataFrame:
        """Unified entry point for CSV or API-based historical data with optional fallback."""
        if not source_config:
            raise ValueError("source_config is required")

        if _depth > 3:
            raise RuntimeError("Exceeded maximum fallback depth while loading data source")

        fallback_config = source_config.get('fallback')
        source_type = source_config.get('type', 'csv').lower()

        try:
            if source_type == 'csv':
                df = self.load_csv(
                    filepath=source_config['path'],
                    datetime_column=source_config.get('datetime_column'),
                    timezone=source_config.get('timezone'),
                    resample_to=source_config.get('resample_to')
                )
            elif source_type in {'yfinance', 'yf', 'api'}:
                symbol = source_config['symbol']
                timeframe = source_config.get('interval', '1h')
                start_date = source_config.get('start_date')
                end_date = source_config.get('end_date')

                if not start_date and source_config.get('period'):
                    delta = self._period_to_timedelta(source_config['period'])
                    end_dt = pd.Timestamp(end_date or datetime.now())
                    start_date = (end_dt - delta).strftime('%Y-%m-%d')
                    end_date = end_date or end_dt.strftime('%Y-%m-%d')

                df = self.fetch_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=timeframe,
                    is_nse=source_config.get('is_nse', False)
                )

                resample_to = source_config.get('resample_to')
                if resample_to:
                    df = self.resample_data(df, resample_to)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            if df.empty and fallback_config:
                logger.warning(
                    f"Primary data source returned no rows (type={source_type}). Falling back to alternate source."
                )
                return self.load_source(fallback_config, _depth=_depth + 1)

            return df
        except Exception as exc:
            if fallback_config:
                logger.warning(
                    f"Primary data source failed ({exc}). Attempting fallback source..."
                )
                return self.load_source(fallback_config, _depth=_depth + 1)
            raise


# Convenience function
def get_data(symbol: str, start_date: str = None, end_date: str = None, 
             timeframe: str = '1d', is_nse: bool = True) -> pd.DataFrame:
    """Quick function to fetch data"""
    manager = DataManager()
    return manager.fetch_historical_data(symbol, start_date, end_date, timeframe, is_nse)
