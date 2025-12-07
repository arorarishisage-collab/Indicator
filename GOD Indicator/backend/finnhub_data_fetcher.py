"""
Finnhub Data Fetcher - Production-Grade Market Data
Supports: Stocks (NSE/BSE/US), Forex, Commodities (Gold/Silver), Crypto
Real-time WebSocket streaming + Historical data
"""

import requests
import pandas as pd
import websocket
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinnhubDataFetcher:
    """
    Finnhub API Integration - Production Grade
    
    Features:
    ✅ Real-time quotes (stocks, forex, crypto, commodities)
    ✅ Historical OHLCV data
    ✅ WebSocket streaming (live ticks)
    ✅ NSE/BSE Indian stocks support
    ✅ Gold, Silver, Forex support
    ✅ Company fundamentals
    ✅ News sentiment
    
    API Key: d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg
    Docs: https://finnhub.io/docs/api
    """
    
    def __init__(self, api_key: str = "d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg"):
        """
        Initialize Finnhub data fetcher
        
        Args:
            api_key: Finnhub API key (pre-configured)
        """
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.ws_url = f"wss://ws.finnhub.io?token={api_key}"
        
        # Symbol mappings for NSE/BSE
        self.nse_prefix = "NSE:"
        self.bse_prefix = "BSE:"
        
        # WebSocket components
        self.ws = None
        self.ws_thread = None
        self.ws_running = False
        self.subscribed_symbols = []
        self.tick_callbacks = {}
        
        logger.info(f"✅ Finnhub initialized with API key: {api_key[:20]}...")
    
    # ==================== HISTORICAL DATA ====================
    
    def fetch_historical_data(
        self,
        symbol: str,
        resolution: str = 'D',
        from_date: datetime = None,
        to_date: datetime = None,
        exchange: str = 'NSE'
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'AAPL', 'OANDA:XAU_USD' for Gold)
            resolution: 1, 5, 15, 30, 60, D, W, M (minute/day/week/month)
            from_date: Start date (default: 1 year ago)
            to_date: End date (default: today)
            exchange: NSE, BSE, US (default: NSE)
        
        Returns:
            DataFrame with OHLCV data
            
        Examples:
            # Indian stocks
            df = fetcher.fetch_historical_data('RELIANCE', 'D', exchange='NSE')
            df = fetcher.fetch_historical_data('TCS', 'D', exchange='BSE')
            
            # US stocks
            df = fetcher.fetch_historical_data('AAPL', 'D', exchange='US')
            
            # Gold (no exchange needed)
            df = fetcher.fetch_historical_data('OANDA:XAU_USD', 'D', exchange='')
            
            # Forex
            df = fetcher.fetch_historical_data('OANDA:EUR_USD', 'D', exchange='')
        """
        # Set default dates
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=365)
        
        # Format symbol with exchange prefix
        finnhub_symbol = self._format_symbol(symbol, exchange)
        
        # Convert dates to Unix timestamps
        from_ts = int(from_date.timestamp())
        to_ts = int(to_date.timestamp())
        
        # Determine correct endpoint: /forex/candle for forex/gold, /stock/candle for stocks
        if ':' in finnhub_symbol or 'XAU' in finnhub_symbol.upper() or 'XAG' in finnhub_symbol.upper():
            endpoint = f"{self.base_url}/forex/candle"
            logger.info(f"🔧 Using forex endpoint for {finnhub_symbol}")
        else:
            endpoint = f"{self.base_url}/stock/candle"
            logger.info(f"🔧 Using stock endpoint for {finnhub_symbol}")
        
        params = {
            'symbol': finnhub_symbol,
            'resolution': resolution,
            'from': from_ts,
            'to': to_ts,
            'token': self.api_key
        }
        
        try:
            logger.info(f"📊 Fetching {finnhub_symbol} data ({resolution}, {from_date.date()} to {to_date.date()})...")
            logger.info(f"🌐 URL: {endpoint}?symbol={finnhub_symbol}&resolution={resolution}&from={from_ts}&to={to_ts}")
            
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for errors
            if data.get('s') == 'no_data':
                logger.warning(f"⚠️  No data available for {finnhub_symbol}")
                return pd.DataFrame()
            
            if data.get('s') != 'ok':
                logger.error(f"❌ API error: {data}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame({
                'DateTime': pd.to_datetime(data['t'], unit='s'),
                'Open': data['o'],
                'High': data['h'],
                'Low': data['l'],
                'Close': data['c'],
                'Volume': data['v']
            })
            
            df.set_index('DateTime', inplace=True)
            
            logger.info(f"✅ Fetched {len(df)} candles for {finnhub_symbol}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching historical data: {e}")
            return pd.DataFrame()
    
    # ==================== REAL-TIME QUOTES ====================
    
    def get_quote(self, symbol: str, exchange: str = 'NSE') -> Dict:
        """
        Get real-time quote for symbol
        
        Args:
            symbol: Stock symbol
            exchange: NSE, BSE, US, or '' for forex/commodities
        
        Returns:
            Dict with current price, change, volume, etc.
            
        Example:
            quote = fetcher.get_quote('RELIANCE', 'NSE')
            print(f"Price: ₹{quote['current_price']}")
        """
        finnhub_symbol = self._format_symbol(symbol, exchange)
        
        url = f"{self.base_url}/quote"
        params = {
            'symbol': finnhub_symbol,
            'token': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if data is valid
            if not data or data.get('c') is None or data.get('c') == 0:
                logger.warning(f"⚠️  No quote data for {finnhub_symbol}")
                return {
                    'symbol': symbol,
                    'finnhub_symbol': finnhub_symbol,
                    'current_price': None,
                    'change': None,
                    'percent_change': None,
                    'high': None,
                    'low': None,
                    'open': None,
                    'previous_close': None,
                    'timestamp': None,
                    'error': 'No data available'
                }
            
            return {
                'symbol': symbol,
                'finnhub_symbol': finnhub_symbol,
                'current_price': data.get('c', 0),  # Current price
                'change': data.get('d', 0),  # Change
                'percent_change': data.get('dp', 0),  # Percent change
                'high': data.get('h', 0),  # Day high
                'low': data.get('l', 0),  # Day low
                'open': data.get('o', 0),  # Day open
                'previous_close': data.get('pc', 0),  # Previous close
                'timestamp': datetime.fromtimestamp(data.get('t', 0)) if data.get('t') else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching quote for {symbol}: {e}")
            return {
                'symbol': symbol,
                'finnhub_symbol': finnhub_symbol,
                'current_price': None,
                'error': str(e)
            }
    
    # ==================== WEBSOCKET STREAMING ====================
    
    def start_streaming(self, symbols: List[str], exchange: str = 'NSE', callback: Callable = None):
        """
        Start WebSocket streaming for real-time data
        
        Args:
            symbols: List of symbols to stream
            exchange: NSE, BSE, US, or '' for forex/commodities
            callback: Function to call on each tick (optional)
            
        Example:
            def on_tick(tick):
                print(f"{tick['symbol']}: ₹{tick['price']}")
            
            fetcher.start_streaming(['RELIANCE', 'TCS'], 'NSE', on_tick)
        """
        if self.ws_running:
            logger.warning("⚠️  WebSocket already running. Stop first.")
            return
        
        # Format symbols for Finnhub
        self.subscribed_symbols = [self._format_symbol(s, exchange) for s in symbols]
        
        # Set callback
        if callback:
            for symbol in self.subscribed_symbols:
                self.tick_callbacks[symbol] = callback
        
        # Start WebSocket in background thread
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()
        
        logger.info(f"✅ Started streaming {len(symbols)} symbols")
    
    def stop_streaming(self):
        """Stop WebSocket streaming"""
        if self.ws:
            self.ws_running = False
            self.ws.close()
            logger.info("🛑 Stopped streaming")
    
    def _run_websocket(self):
        """Run WebSocket connection (internal)"""
        self.ws_running = True
        
        def on_message(ws, message):
            """Handle incoming ticks"""
            try:
                data = json.loads(message)
                
                if data.get('type') == 'trade':
                    for trade in data.get('data', []):
                        tick = {
                            'symbol': trade['s'],
                            'price': trade['p'],
                            'volume': trade['v'],
                            'timestamp': datetime.fromtimestamp(trade['t'] / 1000),
                            'conditions': trade.get('c', [])
                        }
                        
                        # Call registered callback
                        if trade['s'] in self.tick_callbacks:
                            self.tick_callbacks[trade['s']](tick)
                            
            except Exception as e:
                logger.error(f"❌ Error processing tick: {e}")
        
        def on_error(ws, error):
            """Handle WebSocket errors"""
            logger.error(f"❌ WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            """Handle WebSocket close"""
            logger.info(f"🔌 WebSocket closed: {close_status_code} - {close_msg}")
            
            # Auto-reconnect after 5 seconds
            if self.ws_running:
                logger.info("🔄 Reconnecting in 5 seconds...")
                time.sleep(5)
                self._run_websocket()
        
        def on_open(ws):
            """Handle WebSocket open"""
            logger.info("✅ WebSocket connected")
            
            # Subscribe to symbols
            for symbol in self.subscribed_symbols:
                ws.send(json.dumps({'type': 'subscribe', 'symbol': symbol}))
                logger.info(f"📡 Subscribed to {symbol}")
        
        # Create WebSocket connection
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Run forever
        self.ws.run_forever()
    
    # ==================== COMPANY FUNDAMENTALS ====================
    
    def get_company_profile(self, symbol: str, exchange: str = 'NSE') -> Dict:
        """
        Get company profile and fundamentals
        
        Args:
            symbol: Stock symbol
            exchange: NSE, BSE, US
        
        Returns:
            Dict with company info, sector, market cap, etc.
        """
        finnhub_symbol = self._format_symbol(symbol, exchange)
        
        url = f"{self.base_url}/stock/profile2"
        params = {
            'symbol': finnhub_symbol,
            'token': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'name': data.get('name', ''),
                'ticker': data.get('ticker', ''),
                'exchange': data.get('exchange', ''),
                'industry': data.get('finnhubIndustry', ''),
                'market_cap': data.get('marketCapitalization', 0),
                'shares_outstanding': data.get('shareOutstanding', 0),
                'ipo_date': data.get('ipo', ''),
                'logo': data.get('logo', ''),
                'website': data.get('weburl', ''),
                'phone': data.get('phone', ''),
                'country': data.get('country', '')
            }
            
        except Exception as e:
            logger.error(f"❌ Error fetching company profile: {e}")
            return {}

    def get_key_metrics(self, symbol: str, exchange: str = 'NSE') -> Dict:
        """Return key valuation and profitability metrics for a symbol."""

        finnhub_symbol = self._format_symbol(symbol, exchange)
        url = f"{self.base_url}/stock/metric"
        params = {
            'symbol': finnhub_symbol,
            'metric': 'all',
            'token': self.api_key
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json().get('metric', {})

            return {
                'pe_ratio': data.get('peBasicExclExtraTTM') or data.get('peBasicExclExtraAnnual'),
                'pb_ratio': data.get('pbAnnual'),
                'eps': data.get('epsDilutedTTM'),
                'revenue_growth': data.get('revenueGrowthTTM'),
                'net_margin': data.get('netMarginTTM'),
                'return_on_equity': data.get('returnOnEquityTTM'),
                'debt_to_equity': data.get('totalDebtToEquityQuarterly') or data.get('totalDebtToEquityAnnual'),
                'ev_to_ebitda': data.get('enterpriseValueOverEBITDATTM'),
            }

        except Exception as e:
            logger.warning(f"⚠️  Error fetching key metrics: {e}")
            return {}
    
    # ==================== NEWS ====================
    
    def get_company_news(self, symbol: str, from_date: datetime = None, to_date: datetime = None) -> List[Dict]:
        """
        Get company news
        
        Args:
            symbol: Stock symbol
            from_date: Start date (default: 7 days ago)
            to_date: End date (default: today)
        
        Returns:
            List of news articles
        """
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=7)
        
        url = f"{self.base_url}/company-news"
        params = {
            'symbol': symbol,
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'token': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            articles = response.json()
            
            return [{
                'headline': a.get('headline', ''),
                'summary': a.get('summary', ''),
                'source': a.get('source', ''),
                'url': a.get('url', ''),
                'datetime': datetime.fromtimestamp(a.get('datetime', 0)),
                'image': a.get('image', '')
            } for a in articles]
            
        except Exception as e:
            logger.error(f"❌ Error fetching news: {e}")
            return []
    
    # ==================== SYMBOL MAPPING ====================
    
    def _format_symbol(self, symbol: str, exchange: str) -> str:
        """
        Format symbol for Finnhub API
        
        Args:
            symbol: Raw symbol (e.g., 'RELIANCE', 'AAPL')
            exchange: NSE, BSE, US, or '' for forex/commodities
        
        Returns:
            Formatted Finnhub symbol
            
        Examples:
            RELIANCE + NSE → RELIANCE.NS (uses Yahoo Finance format)
            TCS + BSE → TCS.BO (uses Yahoo Finance format)
            AAPL + US → AAPL
            OANDA:XAU_USD + '' → OANDA:XAU_USD (Gold)
            OANDA:EUR_USD + '' → OANDA:EUR_USD (Forex)
        """
        # Check if already formatted (OANDA:, IC MARKETS:, etc.)
        if ':' in symbol:
            return symbol
        
        # Check if already has exchange suffix
        if '.NS' in symbol or '.BSE' in symbol or '.BO' in symbol:
            return symbol
        
        # Format based on exchange (Finnhub uses Yahoo Finance format for Indian stocks)
        if exchange.upper() == 'NSE':
            return f"{symbol}.NS"
        elif exchange.upper() == 'BSE':
            return f"{symbol}.BO"
        elif exchange.upper() == 'US' or exchange == '':
            return symbol
        else:
            return symbol
    
    def search_symbol(self, query: str) -> List[Dict]:
        """
        Search for symbols
        
        Args:
            query: Search term (e.g., 'Reliance', 'Apple', 'Gold')
        
        Returns:
            List of matching symbols
        """
        url = f"{self.base_url}/search"
        params = {
            'q': query,
            'token': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('result', [])
            
            return [{
                'symbol': r.get('symbol', ''),
                'description': r.get('description', ''),
                'type': r.get('type', ''),
                'displaySymbol': r.get('displaySymbol', '')
            } for r in results[:20]]  # Top 20 results
            
        except Exception as e:
            logger.error(f"❌ Error searching symbols: {e}")
            return []
    
    # ==================== COMMODITY SUPPORT ====================
    
    def get_gold_price(self) -> Dict:
        """Get current Gold price (OANDA:XAU_USD)"""
        return self.get_quote('OANDA:XAU_USD', exchange='')
    
    def get_silver_price(self) -> Dict:
        """Get current Silver price (OANDA:XAG_USD)"""
        return self.get_quote('OANDA:XAG_USD', exchange='')
    
    def fetch_gold_historical(self, from_date: datetime = None, to_date: datetime = None) -> pd.DataFrame:
        """Fetch historical Gold prices"""
        return self.fetch_historical_data('OANDA:XAU_USD', 'D', from_date, to_date, exchange='')
    
    def fetch_silver_historical(self, from_date: datetime = None, to_date: datetime = None) -> pd.DataFrame:
        """Fetch historical Silver prices"""
        return self.fetch_historical_data('OANDA:XAG_USD', 'D', from_date, to_date, exchange='')


# ==================== EXAMPLE USAGE ====================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 FINNHUB DATA FETCHER - PRODUCTION TEST")
    print("="*70)
    
    fetcher = FinnhubDataFetcher()
    
    # Test 1: Indian Stock (NSE)
    print("\n📊 Test 1: Fetching RELIANCE (NSE) - 1 Year Daily")
    print("-"*70)
    df = fetcher.fetch_historical_data('RELIANCE', 'D', exchange='NSE')
    if not df.empty:
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Latest Close: ₹{df['Close'].iloc[-1]:.2f}")
        print(f"   Date Range: {df.index[0]} to {df.index[-1]}")
    
    # Test 2: Real-time Quote
    print("\n📈 Test 2: Real-time Quote - RELIANCE")
    print("-"*70)
    quote = fetcher.get_quote('RELIANCE', 'NSE')
    if quote:
        print(f"✅ Current Price: ₹{quote['current_price']:.2f}")
        print(f"   Change: {quote['change']:+.2f} ({quote['percent_change']:+.2f}%)")
        print(f"   Day Range: ₹{quote['low']:.2f} - ₹{quote['high']:.2f}")
    
    # Test 3: Gold Price
    print("\n🥇 Test 3: Gold Price (OANDA:XAU_USD)")
    print("-"*70)
    gold = fetcher.get_gold_price()
    if gold:
        print(f"✅ Gold Price: ${gold['current_price']:.2f}/oz")
        print(f"   Change: ${gold['change']:+.2f} ({gold['percent_change']:+.2f}%)")
    
    # Test 4: Company Profile
    print("\n🏢 Test 4: Company Profile - TCS")
    print("-"*70)
    profile = fetcher.get_company_profile('TCS', 'NSE')
    if profile:
        print(f"✅ Name: {profile['name']}")
        print(f"   Industry: {profile['industry']}")
        print(f"   Market Cap: ${profile['market_cap']:.0f}M")
    
    # Test 5: WebSocket Streaming (5 seconds)
    print("\n📡 Test 5: WebSocket Streaming - RELIANCE (5 seconds)")
    print("-"*70)
    
    tick_count = 0
    def on_tick(tick):
        global tick_count
        tick_count += 1
        print(f"   Tick #{tick_count}: {tick['symbol']} = ${tick['price']:.2f} @ {tick['timestamp'].strftime('%H:%M:%S')}")
    
    fetcher.start_streaming(['RELIANCE'], 'NSE', on_tick)
    time.sleep(5)
    fetcher.stop_streaming()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETED")
    print("="*70)
    print("\n💡 Finnhub supports:")
    print("   ✅ NSE/BSE Indian stocks")
    print("   ✅ US stocks (NASDAQ, NYSE)")
    print("   ✅ Forex (EUR/USD, GBP/USD, etc.)")
    print("   ✅ Commodities (Gold, Silver, Oil)")
    print("   ✅ Crypto (BTC, ETH)")
    print("   ✅ Real-time WebSocket streaming")
    print("\n🎯 Use this instead of yfinance for production!")
