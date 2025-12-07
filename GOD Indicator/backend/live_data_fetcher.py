"""
Live Data Fetcher - Real-time market data acquisition for live trading
Supports yfinance (immediate), extensible for broker APIs
"""

import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveDataFetcher:
    """
    Fetches and maintains real-time market data
    
    Features:
    - Live price streaming (yfinance)
    - Intraday data (1m, 5m, 15m)
    - Real-time alerts and monitoring
    - Future: Broker API integration
    """
    
    def __init__(self, refresh_interval: int = 60):
        """
        Initialize live data fetcher
        
        Args:
            refresh_interval: Seconds between data refreshes
        """
        self.refresh_interval = refresh_interval
        self.watched_symbols = {}
        self.live_data = {}
        self.is_running = False
        self.fetch_thread = None
    
    def watch_symbol(self, symbol: str, is_nse: bool = False) -> Dict:
        """
        Start watching a symbol for live data
        
        Args:
            symbol: Stock symbol
            is_nse: If True, append .NS for NSE
        
        Returns:
            Initial live data
        """
        if is_nse and not symbol.endswith('.NS'):
            symbol = f"{symbol}.NS"
        
        self.watched_symbols[symbol] = {
            'added_time': datetime.now(),
            'last_price': 0,
            'price_change': 0,
            'price_change_percent': 0,
            'alerts': []
        }
        
        # Fetch initial data
        return self.fetch_live_data(symbol)
    
    def fetch_live_data(self, symbol: str) -> Dict:
        """
        Fetch current live data for a symbol
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dictionary with live market data
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            previous_close = info.get('previousClose', 0)
            
            live_data = {
                'symbol': symbol,
                'current_price': current_price,
                'previous_close': previous_close,
                'open': info.get('open', 0),
                'high': info.get('dayHigh', 0),
                'low': info.get('dayLow', 0),
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'dividend_yield': info.get('dividendYield', 0),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0),
                'timestamp': datetime.now().isoformat(),
            }
            
            # Calculate changes
            if previous_close > 0:
                live_data['change'] = current_price - previous_close
                live_data['change_percent'] = ((current_price - previous_close) / previous_close) * 100
            else:
                live_data['change'] = 0
                live_data['change_percent'] = 0
            
            # Update watched symbols
            if symbol in self.watched_symbols:
                self.watched_symbols[symbol]['last_price'] = current_price
                self.watched_symbols[symbol]['price_change'] = live_data['change']
                self.watched_symbols[symbol]['price_change_percent'] = live_data['change_percent']
            
            self.live_data[symbol] = live_data
            return live_data
        
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {e}")
            return {}
    
    def fetch_intraday_data(self, symbol: str, interval: str = '1m', 
                           periods: int = 1) -> pd.DataFrame:
        """
        Fetch intraday data (1-minute candles)
        
        Args:
            symbol: Stock symbol
            interval: '1m', '5m', '15m', '30m', '1h'
            periods: Number of periods to fetch (1=today, 5=1 week)
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Map period to days
            period_map = {1: '1d', 5: '5d', 22: '1mo'}
            period = period_map.get(periods, '1d')
            
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False
            )
            
            if df.empty:
                logger.warning(f"No intraday data for {symbol}")
                return pd.DataFrame()
            
            # Clean columns
            df.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            df = df.drop('Adj Close', axis=1)
            df.index.name = 'DateTime'
            df = df.reset_index()
            
            logger.info(f"✓ Fetched {len(df)} intraday bars for {symbol} ({interval})")
            return df
        
        except Exception as e:
            logger.error(f"Error fetching intraday data: {e}")
            return pd.DataFrame()
    
    def start_monitoring(self) -> None:
        """Start continuous monitoring thread"""
        if self.is_running:
            logger.warning("Monitoring already running")
            return
        
        self.is_running = True
        self.fetch_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.fetch_thread.start()
        logger.info("✓ Live data monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring thread"""
        self.is_running = False
        if self.fetch_thread:
            self.fetch_thread.join(timeout=5)
        logger.info("✓ Live data monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Continuous monitoring loop"""
        while self.is_running:
            try:
                for symbol in list(self.watched_symbols.keys()):
                    self.fetch_live_data(symbol)
                
                time.sleep(self.refresh_interval)
            
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(5)
    
    def get_live_data(self, symbol: str) -> Optional[Dict]:
        """Get cached live data"""
        return self.live_data.get(symbol)
    
    def get_all_live_data(self) -> Dict[str, Dict]:
        """Get all cached live data"""
        return self.live_data.copy()
    
    def set_price_alert(self, symbol: str, price_target: float, 
                       alert_type: str = 'above', callback=None) -> bool:
        """
        Set price alert
        
        Args:
            symbol: Stock symbol
            price_target: Target price for alert
            alert_type: 'above' or 'below'
            callback: Optional callback function when alert triggers
        
        Returns:
            True if alert set successfully
        """
        if symbol not in self.watched_symbols:
            logger.warning(f"Symbol {symbol} not being watched")
            return False
        
        alert = {
            'price_target': price_target,
            'type': alert_type,
            'created_time': datetime.now(),
            'triggered': False,
            'callback': callback
        }
        
        self.watched_symbols[symbol]['alerts'].append(alert)
        logger.info(f"✓ Alert set for {symbol} {alert_type} ₹{price_target}")
        
        return True
    
    def check_alerts(self) -> List[Dict]:
        """
        Check if any price alerts have triggered
        
        Returns:
            List of triggered alerts with details
        """
        triggered = []
        
        for symbol, data in self.watched_symbols.items():
            current_price = data['last_price']
            
            for alert in data['alerts']:
                if alert['triggered']:
                    continue
                
                should_trigger = False
                if alert['type'] == 'above' and current_price >= alert['price_target']:
                    should_trigger = True
                elif alert['type'] == 'below' and current_price <= alert['price_target']:
                    should_trigger = True
                
                if should_trigger:
                    alert['triggered'] = True
                    alert['trigger_price'] = current_price
                    alert['trigger_time'] = datetime.now()
                    
                    triggered.append({
                        'symbol': symbol,
                        'alert': alert,
                        'current_price': current_price
                    })
                    
                    logger.warning(
                        f"🚨 ALERT: {symbol} {alert['type']} ₹{alert['price_target']} "
                        f"(Current: ₹{current_price:.2f})"
                    )
                    
                    # Call callback if provided
                    if alert['callback']:
                        try:
                            alert['callback'](symbol, current_price)
                        except Exception as e:
                            logger.error(f"Alert callback error: {e}")
        
        return triggered
    
    def get_market_summary(self) -> pd.DataFrame:
        """Get summary of all watched symbols"""
        if not self.live_data:
            return pd.DataFrame()
        
        summary_data = []
        for symbol, data in self.live_data.items():
            summary_data.append({
                'Symbol': symbol,
                'Price': data.get('current_price', 0),
                'Change': data.get('change', 0),
                'Change %': data.get('change_percent', 0),
                'Volume': data.get('volume', 0),
                'High': data.get('high', 0),
                'Low': data.get('low', 0),
                'PE Ratio': data.get('pe_ratio', 0),
            })
        
        return pd.DataFrame(summary_data)
    
    def export_live_data(self, filename: str) -> bool:
        """Export live data to CSV"""
        try:
            summary = self.get_market_summary()
            summary.to_csv(filename, index=False)
            logger.info(f"✓ Live data exported to {filename}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False


class RealTimeSignalGenerator:
    """Generate trading signals based on live data"""
    
    def __init__(self, live_fetcher: LiveDataFetcher):
        """
        Initialize signal generator
        
        Args:
            live_fetcher: LiveDataFetcher instance
        """
        self.live_fetcher = live_fetcher
    
    def check_signals(self) -> Dict[str, str]:
        """
        Check live data for buy/sell signals
        
        Returns:
            Dictionary mapping symbol to signal ('BUY', 'SELL', 'HOLD')
        """
        signals = {}
        
        for symbol, data in self.live_fetcher.get_all_live_data().items():
            signal = self._generate_signal(symbol, data)
            if signal:
                signals[symbol] = signal
        
        return signals
    
    def _generate_signal(self, symbol: str, data: Dict) -> Optional[str]:
        """
        Simple signal generation based on price movement
        Extensible for custom strategies
        
        Args:
            symbol: Stock symbol
            data: Live market data
        
        Returns:
            'BUY', 'SELL', or None
        """
        change_percent = data.get('change_percent', 0)
        
        # Simple momentum-based signals
        if change_percent < -2:  # Down 2%+ = potential buy
            return 'BUY'
        elif change_percent > 3:  # Up 3%+ = potential sell
            return 'SELL'
        
        return None
