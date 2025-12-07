"""
Unified Data Fetcher - Smart Multi-Source Data Provider
Automatically selects the best data source based on asset type
"""

import os
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

# Configure logging FIRST
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Import all data sources
try:
    from backend.finnhub_data_fetcher import FinnhubDataFetcher
    FINNHUB_AVAILABLE = True
except Exception as e:
    FINNHUB_AVAILABLE = False
    logging.warning(f"Finnhub not available: {e}")

try:
    from nsepy import get_history
    from nsepy.derivatives import get_expiry_date
    NSEPY_AVAILABLE = True
    
    # Fix SSL issue on macOS
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception as e:
    NSEPY_AVAILABLE = False

try:
    from nsepython import nsefetch
    NSEPYTHON_AVAILABLE = True
except Exception as e:
    NSEPYTHON_AVAILABLE = False
    logging.warning(f"nsepython not available: {e}")

try:
    from backend.data_fetch_yfinance import YFinanceDataFetcher
    YFINANCE_AVAILABLE = True
    logging.info("✅ Loaded YFinanceDataFetcher from backend.data_fetch_yfinance")
except Exception as e1:
    # Try without backend prefix
    try:
        from data_fetch_yfinance import YFinanceDataFetcher
        YFINANCE_AVAILABLE = True
        logging.info("✅ Loaded YFinanceDataFetcher from data_fetch_yfinance")
    except Exception as e2:
        # Create inline fallback
        try:
            import yfinance as yf
            logging.info("🔧 Creating inline yfinance wrapper...")
            
            class YFinanceDataFetcher:
                """Inline yfinance wrapper"""
                def fetch_historical_data(self, symbol, period='1y', interval='1d'):
                    logging.debug(f"Inline wrapper fetching: {symbol}, period={period}")
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(period=period, interval=interval)
                    if df.empty:
                        logging.warning(f"Empty data for {symbol}")
                        return None
                    df = df.rename(columns={
                        'Open': 'Open', 'High': 'High', 'Low': 'Low',
                        'Close': 'Close', 'Volume': 'Volume'
                    })
                    logging.info(f"✅ Fetched {len(df)} bars for {symbol}")
                    return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            YFINANCE_AVAILABLE = True
            logging.info("✅ Inline yfinance wrapper created successfully!")
        except Exception as e3:
            YFINANCE_AVAILABLE = False
            logging.error(f"❌ yfinance completely unavailable. Errors: {e1}, {e2}, {e3}")

try:
    from backend.zerodha_kite_safe import ZerodhaKiteDataFetcher
    ZERODHA_AVAILABLE = True
except Exception as e:
    try:
        from zerodha_kite_safe import ZerodhaKiteDataFetcher
        ZERODHA_AVAILABLE = True
    except:
        ZERODHA_AVAILABLE = False


class UnifiedDataFetcher:
    """
    Smart data fetcher that automatically selects the best source
    
    Source Priority:
    - NSE/BSE: Zerodha (production) > nsepython > yfinance (fallback)
    - US Stocks: Finnhub > yfinance
    - Forex/Commodities: Finnhub > yfinance
    - Crypto: Finnhub > yfinance
    """
    
    def __init__(self, zerodha_api_key: str = None, zerodha_access_token: str = None,
                 finnhub_api_key: str = None):
        """
        Initialize unified data fetcher
        
        Args:
            zerodha_api_key: Optional Zerodha API key
            zerodha_access_token: Optional Zerodha access token
            finnhub_api_key: Optional Finnhub API key
        """
        # Initialize available sources
        self.finnhub = None
        if FINNHUB_AVAILABLE:
            resolved_key = finnhub_api_key or os.getenv('FINNHUB_API_KEY')
            try:
                self.finnhub = FinnhubDataFetcher(api_key=resolved_key) if resolved_key else FinnhubDataFetcher()
            except Exception as finnhub_error:
                logger.warning(f"⚠️  Finnhub init failed: {finnhub_error}")
                self.finnhub = None
        self.nsepython_available = NSEPYTHON_AVAILABLE
        self.yfinance = YFinanceDataFetcher() if YFINANCE_AVAILABLE else None
        
        # Initialize Zerodha if credentials provided
        if ZERODHA_AVAILABLE and zerodha_api_key and zerodha_access_token:
            try:
                self.zerodha = ZerodhaKiteDataFetcher(zerodha_api_key, zerodha_access_token)
                logger.info("✅ Zerodha Kite initialized")
            except Exception as e:
                logger.warning(f"⚠️  Zerodha init failed: {e}")
                self.zerodha = None
        else:
            self.zerodha = None
        
        # Log available sources
        sources = []
        if self.finnhub:
            sources.append("Finnhub")
        if self.nsepython_available:
            sources.append("nsepython")
        if self.yfinance:
            sources.append("yfinance")
        if self.zerodha:
            sources.append("Zerodha")
        
        logger.info(f"📊 Unified Data Fetcher initialized with: {', '.join(sources)}")
        
        # Debug logging
        if not self.yfinance:
            logger.error(f"❌ CRITICAL: yfinance not available! YFINANCE_AVAILABLE={YFINANCE_AVAILABLE}")
        else:
            logger.info(f"✅ yfinance initialized: {type(self.yfinance)}")
    
    def fetch_historical_data(
        self,
        symbol: str,
        resolution: str = 'D',
        from_date: datetime = None,
        to_date: datetime = None,
        exchange: str = 'NSE'
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data (automatically selects best source)
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'AAPL')
            resolution: D (daily), W (weekly), M (monthly), or 1/5/15/30/60 (minutes)
            from_date: Start date (default: 1 year ago)
            to_date: End date (default: today)
            exchange: NSE, BSE, US, or '' for forex/commodities
        
        Returns:
            DataFrame with OHLCV data
        """
        # Set defaults
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=365)
        
        # Determine best source
        source, fetcher = self._select_source(symbol, exchange)
        
        logger.info(f"📊 Fetching {symbol} from {source}...")
        
        try:
            if source == 'Zerodha':
                # Convert resolution to Zerodha format
                interval_map = {'D': 'day', 'W': 'week', 'M': 'month', 
                               '1': 'minute', '5': '5minute', '15': '15minute',
                               '30': '30minute', '60': '60minute'}
                interval = interval_map.get(resolution, 'day')
                
                df = fetcher.fetch_historical_data(symbol, interval, from_date, to_date)
                
            elif source == 'nsepython':
                # nsepython for NSE stocks (modern API)
                from nsepython import nsefetch
                
                try:
                    # Limit to 365 days per call
                    days = (to_date - from_date).days
                    if days > 365:
                        from_date = to_date - timedelta(days=365)
                    
                    # Fetch data from NSE API
                    url = f'https://www.nseindia.com/api/historical/cm/equity?symbol={symbol}&series=["EQ"]&from={from_date.strftime("%d-%m-%Y")}&to={to_date.strftime("%d-%m-%Y")}'
                    data = nsefetch(url)
                    
                    if data and 'data' in data and data['data']:
                        records = data['data']
                        df = pd.DataFrame(records)
                        
                        # Rename columns
                        df = df.rename(columns={
                            'CH_TIMESTAMP': 'DateTime',
                            'CH_OPENING_PRICE': 'Open',
                            'CH_TRADE_HIGH_PRICE': 'High',
                            'CH_TRADE_LOW_PRICE': 'Low',
                            'CH_CLOSING_PRICE': 'Close',
                            'CH_TOT_TRADED_QTY': 'Volume'
                        })
                        
                        df['DateTime'] = pd.to_datetime(df['DateTime'])
                        df = df.set_index('DateTime')
                        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index()
                    else:
                        df = pd.DataFrame()
                        
                except Exception as e:
                    logger.error(f"nsepython error: {e}")
                    df = pd.DataFrame()
                
            elif source == 'nsepy':
                # nsepy for NSE/BSE stocks (fallback)
                from nsepy import get_history
                
                df = get_history(
                    symbol=symbol,
                    start=from_date.date() if hasattr(from_date, 'date') else from_date,
                    end=to_date.date() if hasattr(to_date, 'date') else to_date,
                    index=(exchange == 'INDEX')
                )
                
                if not df.empty:
                    df = df.rename(columns={
                        'Open': 'Open',
                        'High': 'High',
                        'Low': 'Low',
                        'Close': 'Close',
                        'Volume': 'Volume'
                    })
                    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                
            elif source == 'Finnhub':
                df = fetcher.fetch_historical_data(symbol, resolution, from_date, to_date, exchange)
                
            elif source == 'yfinance':
                # Convert dates to yfinance format
                period = self._calculate_yfinance_period(from_date, to_date)
                interval_map = {'D': '1d', 'W': '1wk', 'M': '1mo',
                               '1': '1m', '5': '5m', '15': '15m',
                               '30': '30m', '60': '60m'}
                interval = interval_map.get(resolution, '1d')
                
                # Symbol conversion
                yf_symbol = symbol
                if exchange == 'NSE' and not symbol.endswith('.NS'):
                    yf_symbol = f"{symbol}.NS"
                elif exchange == 'BSE' and not symbol.endswith('.BO'):
                    yf_symbol = f"{symbol}.BO"
                elif 'OANDA:XAU' in symbol.upper() or 'XAU_USD' in symbol.upper():
                    # Convert Gold forex to GLD ETF
                    yf_symbol = 'GLD'
                    logger.info(f"💡 Using GLD (Gold ETF) instead of {symbol}")
                elif 'OANDA:' in symbol:
                    # Convert forex to currency pair ETF
                    yf_symbol = symbol.replace('OANDA:', '').replace('_', '=') + '=X'
                
                df = fetcher.fetch_historical_data(yf_symbol, period=period, interval=interval)
            
            else:
                logger.error("❌ No data source available")
                return pd.DataFrame()
            
            if not df.empty:
                logger.info(f"✅ Fetched {len(df)} candles from {source}")
            else:
                logger.warning(f"⚠️  No data from {source}, trying fallback...")
                df = self._try_fallback(symbol, resolution, from_date, to_date, exchange, source)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching from {source}: {e}")
            return self._try_fallback(symbol, resolution, from_date, to_date, exchange, source)
    
    def get_quote(self, symbol: str, exchange: str = 'NSE') -> Dict:
        """
        Get real-time quote
        
        Args:
            symbol: Stock symbol
            exchange: NSE, BSE, US
        
        Returns:
            Dict with current price, change, etc.
        """
        source, fetcher = self._select_source(symbol, exchange)
        
        try:
            if source == 'Zerodha':
                # Format for Zerodha
                zerodha_symbol = f"{exchange}:{symbol}"
                quotes = fetcher.get_quote([zerodha_symbol])
                quote_data = quotes.get(zerodha_symbol, {})
                
                return {
                    'symbol': symbol,
                    'current_price': quote_data.get('last_price', 0),
                    'change': quote_data.get('change', 0),
                    'percent_change': quote_data.get('net_change', 0),
                    'high': quote_data.get('ohlc', {}).get('high', 0),
                    'low': quote_data.get('ohlc', {}).get('low', 0),
                    'open': quote_data.get('ohlc', {}).get('open', 0),
                    'volume': quote_data.get('volume', 0),
                    'source': source
                }
            
            elif source == 'nsepy':
                # nsepy: get latest candle
                from nsepy import get_history
                from datetime import date
                
                df = get_history(symbol=symbol, start=date.today(), end=date.today())
                if not df.empty:
                    latest = df.iloc[-1]
                    return {
                        'symbol': symbol,
                        'current_price': latest['Close'],
                        'change': latest['Close'] - latest['Open'],
                        'percent_change': ((latest['Close'] - latest['Open']) / latest['Open']) * 100 if latest['Open'] else 0,
                        'high': latest['High'],
                        'low': latest['Low'],
                        'open': latest['Open'],
                        'volume': latest['Volume'],
                        'source': source
                    }
                return {'symbol': symbol, 'error': 'No data from nsepy'}
            
            elif source == 'Finnhub':
                quote = fetcher.get_quote(symbol, exchange)
                if quote:
                    quote['source'] = source
                return quote
                
            elif source == 'yfinance':
                # yfinance doesn't have real-time quotes, fallback to Finnhub
                if self.finnhub and exchange == 'US':
                    return self.finnhub.get_quote(symbol, 'US')
                
                # For NSE/BSE, use yfinance live data
                yf_symbol = symbol if exchange != 'NSE' else f"{symbol}.NS"
                import yfinance as yf
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                
                return {
                    'symbol': symbol,
                    'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                    'change': info.get('regularMarketChange', 0),
                    'percent_change': info.get('regularMarketChangePercent', 0),
                    'high': info.get('dayHigh', 0),
                    'low': info.get('dayLow', 0),
                    'open': info.get('open', 0),
                    'volume': info.get('volume', 0),
                    'source': source
                }
            
        except Exception as e:
            logger.error(f"❌ Error getting quote: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _select_source(self, symbol: str, exchange: str):
        """Select best data source based on asset type"""
        
        logger.debug(f"_select_source called: symbol={symbol}, exchange={exchange}")
        logger.debug(f"Available: yfinance={self.yfinance is not None}, nsepython={self.nsepython_available}, finnhub={self.finnhub is not None}")
        
        # Check if forex/commodity (e.g., OANDA:EUR_USD)
        if ':' in symbol or exchange == '':
            if self.finnhub:
                logger.debug("Selected: Finnhub for forex")
                return 'Finnhub', self.finnhub
            else:
                logger.debug("Selected: yfinance for forex")
                return 'yfinance', self.yfinance
        
        # NSE/BSE: nsepython > yfinance
        if exchange in ['NSE', 'BSE']:
            if self.zerodha:
                logger.debug("Selected: Zerodha for NSE/BSE")
                return 'Zerodha', self.zerodha
            elif self.nsepython_available:
                logger.debug("Selected: nsepython for NSE/BSE")
                return 'nsepython', None
            elif self.yfinance:
                logger.debug("Selected: yfinance for NSE/BSE")
                return 'yfinance', self.yfinance
            else:
                logger.error("❌ No source available for NSE/BSE!")
                return None, None
        
        # US Stocks: prefer Finnhub, fallback to yfinance
        if exchange == 'US':
            if self.finnhub:
                logger.debug("Selected: Finnhub for US")
                return 'Finnhub', self.finnhub
            if self.yfinance:
                logger.debug("Selected: yfinance fallback for US")
                return 'yfinance', self.yfinance
            logger.error("❌ No source available for US stocks!")
            return None, None
        
        # Default
        logger.warning(f"⚠️  No source selected for {symbol} ({exchange})")
        return None, None
    
    def _try_fallback(self, symbol, resolution, from_date, to_date, exchange, failed_source):
        """Try fallback sources if primary fails"""
        
        # Build fallback list
        fallbacks = []
        if failed_source != 'yfinance' and self.yfinance:
            fallbacks.append(('yfinance', self.yfinance))
        if failed_source != 'nsepython' and self.nsepython_available and exchange in ['NSE', 'BSE']:
            fallbacks.append(('nsepython', None))
        if failed_source != 'Finnhub' and self.finnhub:
            fallbacks.append(('Finnhub', self.finnhub))
        if failed_source != 'Zerodha' and self.zerodha:
            fallbacks.append(('Zerodha', self.zerodha))
        
        for source, fetcher in fallbacks:
            try:
                logger.info(f"🔄 Trying fallback: {source}...")
                
                if source == 'yfinance':
                    period = self._calculate_yfinance_period(from_date, to_date)
                    interval_map = {'D': '1d', 'W': '1wk', 'M': '1mo'}
                    interval = interval_map.get(resolution, '1d')
                    
                    # Symbol conversion
                    yf_symbol = symbol
                    if exchange == 'NSE':
                        yf_symbol = f"{symbol}.NS"
                    elif 'OANDA:XAU' in symbol.upper() or 'XAU_USD' in symbol.upper():
                        yf_symbol = 'GLD'
                        logger.info(f"💡 Using GLD (Gold ETF) instead of {symbol}")
                    
                    df = fetcher.fetch_historical_data(yf_symbol, period=period, interval=interval)
                    if not df.empty:
                        logger.info(f"✅ Fallback successful: {source}")
                        return df
                
                elif source == 'nsepy':
                    from nsepy import get_history
                    df = get_history(
                        symbol=symbol,
                        start=from_date.date() if hasattr(from_date, 'date') else from_date,
                        end=to_date.date() if hasattr(to_date, 'date') else to_date
                    )
                    if not df.empty:
                        df = df.rename(columns={'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
                        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                        logger.info(f"✅ Fallback successful: {source}")
                        return df
                        
            except Exception as e:
                logger.warning(f"⚠️  Fallback {source} failed: {e}")
                continue
        
        return pd.DataFrame()
    
    def _calculate_yfinance_period(self, from_date, to_date):
        """Calculate yfinance period string"""
        days = (to_date - from_date).days
        
        if days <= 7:
            return '7d'
        elif days <= 30:
            return '1mo'
        elif days <= 90:
            return '3mo'
        elif days <= 180:
            return '6mo'
        elif days <= 365:
            return '1y'
        elif days <= 730:
            return '2y'
        elif days <= 1825:
            return '5y'
        else:
            return 'max'
    
    def get_source_status(self) -> Dict:
        """Get status of all data sources"""
        return {
            'Finnhub': 'Available (quotes only)' if self.finnhub else 'Not available',
            'nsepython': 'Available (NSE stocks)' if self.nsepython_available else 'Not available',
            'yfinance': 'Available (all markets, fallback)' if self.yfinance else 'Not available',
            'Zerodha': 'Available' if self.zerodha else 'Not available (need API credentials)'
        }


# Convenience functions
def get_data(symbol: str, exchange: str = 'NSE', days: int = 365) -> pd.DataFrame:
    """Quick function to fetch data"""
    fetcher = UnifiedDataFetcher()
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)
    return fetcher.fetch_historical_data(symbol, 'D', from_date, to_date, exchange)


def get_live_price(symbol: str, exchange: str = 'NSE') -> float:
    """Quick function to get live price"""
    fetcher = UnifiedDataFetcher()
    quote = fetcher.get_quote(symbol, exchange)
    return quote.get('current_price', 0)


# Example usage
if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 UNIFIED DATA FETCHER - MULTI-SOURCE TEST")
    print("="*70)
    
    # Initialize with Finnhub API key
    import os
    finnhub_key = os.getenv('FINNHUB_API_KEY', 'd4jv009r01qgcb0voap0d4jv009r01qgcb0voapg')
    fetcher = UnifiedDataFetcher(finnhub_api_key=finnhub_key)
    
    # Show status
    print("\n📊 Data Sources Status:")
    for source, status in fetcher.get_source_status().items():
        print(f"   {source}: {status}")
    
    # Test NSE stock (will use nsepy)
    print("\n" + "-"*70)
    print("📊 Test 1: NSE Stock (RELIANCE)")
    print("-"*70)
    from_date = datetime.now() - timedelta(days=30)
    to_date = datetime.now()
    df = fetcher.fetch_historical_data('RELIANCE', 'D', from_date, to_date, exchange='NSE')
    if not df.empty:
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Latest Close: ₹{df['Close'].iloc[-1]:.2f}")
    else:
        print("❌ No data")
    
    # Test US stock (will use Finnhub)
    print("\n" + "-"*70)
    print("📊 Test 2: US Stock (AAPL)")
    print("-"*70)
    from_date = datetime.now() - timedelta(days=30)
    to_date = datetime.now()
    df = fetcher.fetch_historical_data('AAPL', 'D', from_date, to_date, exchange='US')
    if not df.empty:
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Latest Close: ${df['Close'].iloc[-1]:.2f}")
    else:
        print("❌ No data")
    
    # Test Gold
    print("\n" + "-"*70)
    print("📊 Test 3: Gold (GLD ETF)")
    print("-"*70)
    from_date = datetime.now() - timedelta(days=30)
    to_date = datetime.now()
    df = fetcher.fetch_historical_data('OANDA:XAU_USD', 'D', from_date, to_date, exchange='')
    if not df.empty:
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Latest Close: ${df['Close'].iloc[-1]:.2f}")
    else:
        print("❌ No data")
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETE")
    print("="*70)
    print("\n💡 Data Source Strategy:")
    print("   • yfinance: All markets (NSE/BSE/US stocks, Gold ETF)")
    print("   • Finnhub: Real-time quotes only (API key limited)")
    print("   • Zerodha: Production real-time (when API key provided)")
    print("\n✅ What works:")
    print("   • NSE/BSE: RELIANCE.NS, TCS.NS, etc.")
    print("   • US Stocks: AAPL, MSFT, GOOGL")
    print("   • Gold: GLD ETF (tracks gold price)")
    print("   • Forex: EUR=X, GBP=X, etc.")
    print()
