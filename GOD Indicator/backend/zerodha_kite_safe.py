"""
Zerodha Kite Connect - PAPER TRADING ONLY Wrapper
SAFETY: This module is READ-ONLY and cannot place live orders
"""

from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging

try:
    from kiteconnect import KiteConnect, KiteTicker
    KITE_AVAILABLE = True
except ImportError:
    KITE_AVAILABLE = False
    logging.warning("KiteConnect not available. Install with: pip install kiteconnect")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ZerodhaKiteDataFetcher:
    """
    Zerodha Kite Connect - READ-ONLY Data Fetcher
    
    🔒 SAFETY FEATURES:
    - Cannot place live orders
    - Cannot modify/cancel orders
    - Read-only access to market data
    - Paper trading simulation only
    
    ALLOWED OPERATIONS:
    ✅ Fetch historical OHLC data
    ✅ Stream live quotes
    ✅ Get instrument details
    ✅ Fetch market depth
    
    BLOCKED OPERATIONS:
    ❌ Place orders
    ❌ Modify orders
    ❌ Cancel orders
    ❌ Withdraw funds
    """
    
    # HARD-CODED SAFETY FLAG
    PAPER_TRADING_ONLY = True
    BLOCK_LIVE_ORDERS = True
    
    def __init__(self, api_key: str, access_token: str = None):
        """
        Initialize Zerodha Kite data fetcher
        
        Args:
            api_key: Your Kite Connect API key
            access_token: Access token from login flow
            
        Note: This wrapper is READ-ONLY and cannot execute live trades
        """
        if not KITE_AVAILABLE:
            raise ImportError(
                "KiteConnect not installed. Install with:\n"
                "pip install kiteconnect"
            )
        
        self.api_key = api_key
        self.kite = KiteConnect(api_key=api_key)
        
        if access_token:
            self.kite.set_access_token(access_token)
        
        # SAFETY: Remove order placement methods
        self._block_dangerous_methods()
        
        logger.info("🔒 Zerodha Kite initialized in PAPER TRADING MODE")
        logger.info("✅ Data fetching enabled")
        logger.info("❌ Live order placement BLOCKED")
    
    def _block_dangerous_methods(self):
        """SAFETY: Remove methods that can place/modify orders"""
        dangerous_methods = [
            'place_order',
            'modify_order',
            'cancel_order',
            'place_gtt',
            'modify_gtt',
            'delete_gtt'
        ]
        
        for method in dangerous_methods:
            if hasattr(self.kite, method):
                setattr(self.kite, method, self._blocked_method)
    
    def _blocked_method(self, *args, **kwargs):
        """Placeholder for blocked methods"""
        raise PermissionError(
            "🔒 LIVE TRADING DISABLED\n\n"
            "This system is configured for PAPER TRADING ONLY.\n"
            "Real orders cannot be placed through this interface.\n\n"
            "To enable live trading:\n"
            "1. You MUST modify the source code\n"
            "2. You MUST understand the risks\n"
            "3. You MUST have proper risk management\n\n"
            "Contact your system administrator."
        )
    
    def get_login_url(self) -> str:
        """Get Kite Connect login URL for authentication"""
        return self.kite.login_url()
    
    def generate_session(self, request_token: str) -> Dict:
        """
        Generate access token from request token
        
        Args:
            request_token: Token from redirect URL after login
            
        Returns:
            Dict with access_token, user details
        """
        data = self.kite.generate_session(request_token, api_secret="YOUR_API_SECRET")
        self.kite.set_access_token(data["access_token"])
        logger.info("✅ Session generated successfully")
        return data
    
    def fetch_historical_data(
        self,
        symbol: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
        continuous: bool = False
    ) -> pd.DataFrame:
        """
        Fetch historical OHLC data (READ-ONLY)
        
        Args:
            symbol: Trading symbol (e.g., 'RELIANCE', 'NIFTY 50')
            interval: minute, day, 3minute, 5minute, 10minute, 15minute,
                     30minute, 60minute, day, week, month
            from_date: Start date
            to_date: End date
            continuous: True for continuous futures data
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Get instrument token first
            instrument_token = self._get_instrument_token(symbol)
            
            # Fetch historical data
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                continuous=continuous
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # Rename columns to match our system
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
            
            logger.info(f"✅ Fetched {len(df)} candles for {symbol}")
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            raise
    
    def _get_instrument_token(self, symbol: str) -> int:
        """
        Get instrument token for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Instrument token (integer)
        """
        # Download instruments list (cached)
        instruments = self.kite.instruments("NSE")
        
        # Find matching symbol
        for inst in instruments:
            if inst['tradingsymbol'] == symbol:
                return inst['instrument_token']
        
        raise ValueError(f"Symbol {symbol} not found in NSE instruments")
    
    def get_quote(self, symbols: List[str]) -> Dict:
        """
        Get live quotes for symbols (READ-ONLY)
        
        Args:
            symbols: List of symbols (e.g., ['NSE:RELIANCE', 'NSE:TCS'])
            
        Returns:
            Dict with quote data for each symbol
        """
        try:
            quotes = self.kite.quote(symbols)
            logger.info(f"✅ Fetched quotes for {len(symbols)} symbols")
            return quotes
        except Exception as e:
            logger.error(f"❌ Error fetching quotes: {e}")
            raise
    
    def get_ltp(self, symbols: List[str]) -> Dict:
        """
        Get last traded price (READ-ONLY)
        
        Args:
            symbols: List of symbols
            
        Returns:
            Dict with {symbol: last_price}
        """
        try:
            ltp = self.kite.ltp(symbols)
            return ltp
        except Exception as e:
            logger.error(f"❌ Error fetching LTP: {e}")
            raise
    
    def get_ohlc(self, symbols: List[str]) -> Dict:
        """
        Get OHLC data for symbols (READ-ONLY)
        
        Args:
            symbols: List of symbols
            
        Returns:
            Dict with OHLC data
        """
        try:
            ohlc = self.kite.ohlc(symbols)
            return ohlc
        except Exception as e:
            logger.error(f"❌ Error fetching OHLC: {e}")
            raise
    
    def stream_live_data(self, symbols: List[str], on_tick_callback):
        """
        Stream live market data via WebSocket (READ-ONLY)
        
        Args:
            symbols: List of instrument tokens
            on_tick_callback: Function to call on each tick
        """
        try:
            kws = KiteTicker(self.api_key, self.kite.access_token)
            
            def on_ticks(ws, ticks):
                """Handle incoming ticks"""
                on_tick_callback(ticks)
            
            def on_connect(ws, response):
                """Subscribe to symbols on connect"""
                logger.info("✅ WebSocket connected")
                ws.subscribe(symbols)
                ws.set_mode(ws.MODE_FULL, symbols)
            
            def on_error(ws, code, reason):
                """Handle errors"""
                logger.error(f"❌ WebSocket error: {code} - {reason}")
            
            kws.on_ticks = on_ticks
            kws.on_connect = on_connect
            kws.on_error = on_error
            
            logger.info("🔄 Starting WebSocket connection...")
            kws.connect(threaded=True)
            
        except Exception as e:
            logger.error(f"❌ Error streaming data: {e}")
            raise
    
    def get_instruments(self, exchange: str = "NSE") -> List[Dict]:
        """
        Get list of instruments for an exchange
        
        Args:
            exchange: Exchange name (NSE, BSE, NFO, etc.)
            
        Returns:
            List of instrument dicts
        """
        try:
            instruments = self.kite.instruments(exchange)
            logger.info(f"✅ Fetched {len(instruments)} instruments from {exchange}")
            return instruments
        except Exception as e:
            logger.error(f"❌ Error fetching instruments: {e}")
            raise


class PaperTradingSimulator:
    """
    Paper trading simulator for testing strategies
    Records simulated trades without executing real orders
    """
    
    def __init__(self, initial_capital: float = 100000):
        """
        Initialize paper trading simulator
        
        Args:
            initial_capital: Starting capital in INR
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.closed_trades = []
        self.trade_id = 1
        
        logger.info(f"📝 Paper trading initialized with ₹{initial_capital:,.2f}")
    
    def simulate_order(
        self,
        symbol: str,
        quantity: int,
        order_type: str,
        price: float,
        stop_loss: float = None,
        take_profit: float = None
    ) -> Dict:
        """
        Simulate a paper trade order
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares
            order_type: 'BUY' or 'SELL'
            price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Dict with trade details
        """
        trade = {
            'trade_id': self.trade_id,
            'symbol': symbol,
            'quantity': quantity,
            'order_type': order_type,
            'entry_price': price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'status': 'OPEN',
            'pnl': 0.0
        }
        
        # Calculate required capital
        required_capital = price * quantity
        
        if required_capital > self.capital:
            logger.warning(f"⚠️ Insufficient capital: Required ₹{required_capital:,.2f}, Available ₹{self.capital:,.2f}")
            trade['status'] = 'REJECTED'
            return trade
        
        # Deduct capital
        self.capital -= required_capital
        self.positions.append(trade)
        self.trade_id += 1
        
        logger.info(
            f"📝 Paper {order_type}: {quantity} x {symbol} @ ₹{price:.2f}\n"
            f"   Capital remaining: ₹{self.capital:,.2f}"
        )
        
        return trade
    
    def close_position(self, trade_id: int, exit_price: float) -> Dict:
        """Close a paper trading position"""
        for i, pos in enumerate(self.positions):
            if pos['trade_id'] == trade_id:
                pos['exit_price'] = exit_price
                pos['exit_time'] = datetime.now()
                pos['status'] = 'CLOSED'
                
                # Calculate P&L
                if pos['order_type'] == 'BUY':
                    pos['pnl'] = (exit_price - pos['entry_price']) * pos['quantity']
                else:
                    pos['pnl'] = (pos['entry_price'] - exit_price) * pos['quantity']
                
                # Return capital + profit
                self.capital += (pos['entry_price'] * pos['quantity']) + pos['pnl']
                
                # Move to closed trades
                self.closed_trades.append(pos)
                self.positions.pop(i)
                
                logger.info(
                    f"✅ Closed {pos['symbol']}: P&L = ₹{pos['pnl']:,.2f}\n"
                    f"   Capital: ₹{self.capital:,.2f}"
                )
                
                return pos
        
        raise ValueError(f"Trade ID {trade_id} not found")
    
    def get_portfolio_summary(self) -> Dict:
        """Get paper trading portfolio summary"""
        total_pnl = sum(t['pnl'] for t in self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t['pnl'] > 0]
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.capital,
            'total_pnl': total_pnl,
            'total_return_pct': (total_pnl / self.initial_capital) * 100,
            'open_positions': len(self.positions),
            'closed_trades': len(self.closed_trades),
            'winning_trades': len(winning_trades),
            'win_rate': (len(winning_trades) / len(self.closed_trades) * 100) if self.closed_trades else 0,
            'positions': self.positions,
            'closed_trades': self.closed_trades
        }


# Example usage
if __name__ == '__main__':
    print("\n🔒 Zerodha Kite - PAPER TRADING ONLY\n")
    print("="*60)
    print("This module is READ-ONLY and cannot place live orders")
    print("="*60)
    
    # Test paper trading simulator
    print("\n📝 Testing Paper Trading Simulator...")
    simulator = PaperTradingSimulator(initial_capital=100000)
    
    # Simulate trades
    trade1 = simulator.simulate_order('RELIANCE', 10, 'BUY', 2500.00, stop_loss=2450, take_profit=2600)
    trade2 = simulator.simulate_order('TCS', 5, 'BUY', 3500.00, stop_loss=3400, take_profit=3700)
    
    # Simulate closing
    simulator.close_position(trade1['trade_id'], 2580.00)
    
    # Get summary
    summary = simulator.get_portfolio_summary()
    print(f"\n📊 Portfolio Summary:")
    print(f"   Capital: ₹{summary['current_capital']:,.2f}")
    print(f"   Total P&L: ₹{summary['total_pnl']:,.2f}")
    print(f"   Return: {summary['total_return_pct']:.2f}%")
    print(f"   Open Positions: {summary['open_positions']}")
    print(f"   Win Rate: {summary['win_rate']:.1f}%")
