"""
Live Dummy Trader - Simulates live trading and learns from mistakes
Runs independently in background, tracks P&L, win rate, and optimizes parameters
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import logging
import sqlite3
from pathlib import Path

from .rl_feedback_logger import RLExperienceLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DummyTrade:
    """Represents a single dummy trade"""
    
    def __init__(self, trade_id, symbol, entry_price, entry_time, direction, strategy, signal_strength=5, profile=None):
        """
        Initialize a dummy trade
        
        Args:
            trade_id (str): Unique trade ID
            symbol (str): Trading symbol
            entry_price (float): Entry price
            entry_time (datetime): Entry time
            direction (int): 1=buy, -1=sell
            strategy (str): Strategy name
            signal_strength (float): Signal strength (0-10)
            profile (str): Optional strategy profile identifier
        """
        self.trade_id = trade_id
        self.symbol = symbol
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.direction = direction
        self.strategy = strategy
        self.signal_strength = signal_strength
        self.profile = profile
        
        self.exit_price = None
        self.exit_time = None
        self.pnl = None
        self.pnl_percent = None
        self.win = None
        self.bars_held = 0
        self.status = 'open'  # open, closed
        
    def close_trade(self, exit_price, exit_time, bars_held=0):
        """Close the trade"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.bars_held = bars_held
        self.status = 'closed'
        
        # Calculate P&L
        if self.direction == 1:  # Long
            self.pnl = exit_price - self.entry_price
            self.pnl_percent = (self.pnl / self.entry_price) * 100
        else:  # Short
            self.pnl = self.entry_price - exit_price
            self.pnl_percent = (self.pnl / self.entry_price) * 100
        
        self.win = self.pnl > 0
    
    def to_dict(self):
        """Convert trade to dictionary"""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'strategy': self.strategy,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'direction': 'BUY' if self.direction == 1 else 'SELL',
            'pnl': round(self.pnl, 4) if self.pnl else None,
            'pnl_percent': round(self.pnl_percent, 2) if self.pnl_percent else None,
            'win': self.win,
            'bars_held': self.bars_held,
            'signal_strength': round(self.signal_strength, 2),
            'status': self.status,
            'profile': self.profile,
        }


class LiveDummyTrader:
    """
    Runs dummy trades on live/historical data
    Learns from wins/losses and optimizes strategy parameters
    """
    
    def __init__(self, symbol='XAUUSD', initial_capital=10000, risk_percent=1.0, db_path='reports/trading_log.db'):
        """
        Initialize dummy trader
        
        Args:
            symbol (str): Trading symbol
            initial_capital (float): Initial capital for dummy trading
            risk_percent (float): Risk per trade as % of capital
            db_path (str): Path to store trading log database
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_percent = risk_percent
        self.db_path = db_path
        
        self.trades = []
        self.open_trades = {}
        self.trade_counter = 0
        self.performance_metrics = {}

        self.experience_logger = RLExperienceLogger()
        
        # Setup database
        self._setup_database()
    
    def _setup_database(self):
        """Setup SQLite database for trading log"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    strategy TEXT,
                    entry_price REAL,
                    entry_time TEXT,
                    exit_price REAL,
                    exit_time TEXT,
                    direction TEXT,
                    pnl REAL,
                    pnl_percent REAL,
                    win INTEGER,
                    bars_held INTEGER,
                    signal_strength REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
    
    def execute_trade(
        self,
        entry_price,
        direction,
        strategy,
        entry_time=None,
        signal_strength=5,
        stop_loss=None,
        take_profit=None,
        symbol=None,
        profile=None,
        risk_percent=None,
        context=None,
    ):
        """
        Execute a dummy trade
        
        Args:
            entry_price (float): Entry price
            entry_time (datetime): Entry time
            direction (int): 1=buy, -1=sell
            strategy (str): Strategy name
            signal_strength (float): Signal strength (0-10)
            stop_loss (float): Stop loss price (optional)
            take_profit (float): Take profit price (optional)
            profile (str): Strategy profile label if applicable
            risk_percent (float): Percent of capital risked on this trade
            
        Returns:
            DummyTrade: The created trade
        """
        entry_time = entry_time or datetime.now()
        self.trade_counter += 1
        trade_symbol = symbol or self.symbol
        trade_risk_percent = risk_percent if risk_percent is not None else self.risk_percent
        trade_id = f"{trade_symbol}_{strategy}_{self.trade_counter}_{entry_time.timestamp()}"
        
        trade = DummyTrade(
            trade_id=trade_id,
            symbol=trade_symbol,
            entry_price=entry_price,
            entry_time=entry_time,
            direction=direction,
            strategy=strategy,
            signal_strength=signal_strength,
            profile=profile
        )
        
        self.open_trades[trade_id] = {
            'trade': trade,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'direction': direction,
            'symbol': trade_symbol,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'strategy': strategy,
            'signal_strength': signal_strength,
            'profile': profile,
            'risk_percent': trade_risk_percent,
            'initial_stop_loss': stop_loss,  # Track original SL
            'trailing_stop_enabled': False,
            'breakeven_moved': False,
            'partial_close_done': False,
            'best_price': entry_price,  # Track best price for trailing
            'context': context or {}
        }
        
        logger.info(
            f"📍 {'BUY' if direction == 1 else 'SELL'} {trade_symbol} @ {entry_price} - {strategy} "
            f"(Signal: {signal_strength:.1f}/10, Risk: {trade_risk_percent:.2f}%)"
        )
        
        return trade

    def get_open_trades(self, symbol=None, strategy=None, profile=None):
        """Return list of open trade metadata filtered by optional fields."""
        trades = []
        for trade_data in self.open_trades.values():
            if profile and trade_data.get('profile') and trade_data.get('profile') != profile:
                continue
            if symbol and trade_data.get('symbol') != symbol:
                continue
            if strategy and trade_data.get('strategy') != strategy:
                continue
            if profile and not trade_data.get('profile'):
                # Legacy trades: fallback to symbol match when profile is missing
                if symbol and trade_data.get('symbol') != symbol:
                    continue
            trades.append(trade_data)
        return trades

    def get_open_exposure_percent(self, symbol=None, strategy=None, profile=None):
        """Estimate exposure as sum of risk_percent for matching open trades."""
        exposure = 0.0
        for trade_data in self.get_open_trades(symbol=symbol, strategy=strategy, profile=profile):
            exposure += trade_data.get('risk_percent', self.risk_percent)
        return exposure
    
    def update_trailing_stops(self, current_prices: dict):
        """Update trailing stops for all open trades based on current prices
        
        Args:
            current_prices: Dict of {symbol: current_price}
        """
        for trade_id, trade_data in list(self.open_trades.items()):
            symbol = trade_data['symbol']
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            direction = trade_data['direction']
            entry_price = trade_data['entry_price']
            
            # Calculate profit in pips/points
            if direction == 1:  # Long
                profit = current_price - entry_price
            else:  # Short
                profit = entry_price - current_price
            
            profit_pct = (profit / entry_price) * 100
            
            # 1. Move to breakeven after +1% profit
            if not trade_data['breakeven_moved'] and profit_pct >= 1.0:
                trade_data['stop_loss'] = entry_price
                trade_data['breakeven_moved'] = True
                logger.info(f"✓ {trade_id}: Moved SL to breakeven @ {entry_price}")
            
            # 2. Partial profit taking at +2% (close 50% of position)
            if not trade_data['partial_close_done'] and profit_pct >= 2.0:
                # Mark as partially closed (in real trading, would close 50%)
                trade_data['partial_close_done'] = True
                logger.info(f"💰 {trade_id}: Partial profit taken @ {current_price} (+{profit_pct:.1f}%)")
            
            # 3. Activate trailing stop after +3% profit
            if profit_pct >= 3.0:
                if not trade_data['trailing_stop_enabled']:
                    trade_data['trailing_stop_enabled'] = True
                    trade_data['best_price'] = current_price
                    logger.info(f"📈 {trade_id}: Trailing stop activated @ {current_price}")
                else:
                    # Update best price
                    if direction == 1 and current_price > trade_data['best_price']:
                        trade_data['best_price'] = current_price
                        # Trail SL: Keep 1.5% below best price
                        new_sl = current_price * 0.985  # 1.5% below
                        if new_sl > trade_data['stop_loss']:
                            trade_data['stop_loss'] = new_sl
                            logger.debug(f"📍 {trade_id}: Trailing SL raised to {new_sl:.2f}")
                    
                    elif direction == -1 and current_price < trade_data['best_price']:
                        trade_data['best_price'] = current_price
                        # Trail SL: Keep 1.5% above best price
                        new_sl = current_price * 1.015  # 1.5% above
                        if new_sl < trade_data['stop_loss']:
                            trade_data['stop_loss'] = new_sl
                            logger.debug(f"📍 {trade_id}: Trailing SL lowered to {new_sl:.2f}")
    
    def check_stop_loss_take_profit(self, current_prices: dict) -> list:
        """Check if any trades hit SL or TP
        
        Args:
            current_prices: Dict of {symbol: current_price}
            
        Returns:
            List of trade_ids that should be closed
        """
        trades_to_close = []
        
        for trade_id, trade_data in self.open_trades.items():
            symbol = trade_data['symbol']
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            direction = trade_data['direction']
            stop_loss = trade_data.get('stop_loss')
            take_profit = trade_data.get('take_profit')
            
            # Check Stop Loss
            if stop_loss:
                if direction == 1 and current_price <= stop_loss:
                    trades_to_close.append((trade_id, current_price, 'SL'))
                elif direction == -1 and current_price >= stop_loss:
                    trades_to_close.append((trade_id, current_price, 'SL'))
            
            # Check Take Profit
            if take_profit:
                if direction == 1 and current_price >= take_profit:
                    trades_to_close.append((trade_id, current_price, 'TP'))
                elif direction == -1 and current_price <= take_profit:
                    trades_to_close.append((trade_id, current_price, 'TP'))
        
        return trades_to_close
    
    def close_trade(self, trade_id, exit_price, exit_time=None, bars_held=0):
        """
        Close a dummy trade
        
        Args:
            trade_id (str): Trade ID
            exit_price (float): Exit price
            exit_time (datetime): Exit time
            bars_held (int): Number of bars held
        """
        if trade_id not in self.open_trades:
            logger.warning(f"Trade {trade_id} not found")
            return None
        
        exit_time = exit_time or datetime.now()
        trade_data = self.open_trades.pop(trade_id)
        trade = trade_data['trade']
        
        trade.close_trade(exit_price, exit_time, bars_held)
        self.trades.append(trade)
        
        # Update capital
        if trade.win:
            self.capital += trade.pnl
        else:
            self.capital -= abs(trade.pnl)
        
        status = "✅ WIN" if trade.win else "❌ LOSS"
        logger.info(f"{status} {trade_id}: {trade.pnl_percent:+.2f}% | Capital: ${self.capital:.2f}")
        
        # Save to database
        self._save_trade_to_db(trade)

        context = trade_data.get('context') or {}
        try:
            self.experience_logger.log_trade(trade, trade_data, context=context)
        except Exception as log_error:
            logger.error(f"Error logging RL experience: {log_error}")
        
        return trade
    
    def _save_trade_to_db(self, trade):
        """Save trade to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            trade_dict = trade.to_dict()
            cursor.execute('''
                INSERT INTO trades (
                    trade_id,
                    symbol,
                    strategy,
                    entry_price,
                    entry_time,
                    exit_price,
                    exit_time,
                    direction,
                    pnl,
                    pnl_percent,
                    win,
                    bars_held,
                    signal_strength,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.trade_id,
                trade.symbol,
                trade.strategy,
                trade.entry_price,
                trade.entry_time.isoformat(),
                trade.exit_price,
                trade.exit_time.isoformat(),
                'BUY' if trade.direction == 1 else 'SELL',
                trade.pnl,
                trade.pnl_percent,
                int(trade.win),
                trade.bars_held,
                trade.signal_strength,
                trade.status
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving trade to database: {e}")
    
    def calculate_performance_metrics(self):
        """Calculate performance metrics from closed trades"""
        if not self.trades:
            self.performance_metrics = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'current_capital': self.capital,
                'return_percent': 0,
            }
            return self.performance_metrics
        
        df_trades = pd.DataFrame([t.to_dict() for t in self.trades])
        
        total_trades = len(df_trades)
        winning_trades = (df_trades['win'] == True).sum()
        losing_trades = (df_trades['win'] == False).sum()
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        wins = df_trades[df_trades['win'] == True]['pnl'].sum()
        losses = abs(df_trades[df_trades['win'] == False]['pnl'].sum())
        
        avg_win = (wins / winning_trades) if winning_trades > 0 else 0
        avg_loss = (losses / losing_trades) if losing_trades > 0 else 0
        
        profit_factor = (wins / losses) if losses > 0 else 0
        
        total_pnl = df_trades['pnl'].sum()
        return_percent = (total_pnl / self.initial_capital) * 100
        
        # Calculate Sharpe Ratio
        pnl_series = df_trades['pnl'].values
        if len(pnl_series) > 1:
            sharpe_ratio = np.mean(pnl_series) / np.std(pnl_series) if np.std(pnl_series) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate Max Drawdown
        cumulative_pnl = np.cumsum(pnl_series)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        self.performance_metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_win': round(avg_win, 4),
            'avg_loss': round(avg_loss, 4),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 4),
            'current_capital': round(self.capital, 2),
            'return_percent': round(return_percent, 2),
        }
        
        return self.performance_metrics
    
    def get_performance_summary(self):
        """Get human-readable performance summary"""
        metrics = self.calculate_performance_metrics()
        
        return f"""
╔════════════════════════════════════════════╗
║   DUMMY TRADER PERFORMANCE SUMMARY         ║
╚════════════════════════════════════════════╝

📊 Trade Statistics:
   Total Trades:     {metrics['total_trades']}
   Winning Trades:   {metrics['winning_trades']}
   Losing Trades:    {metrics['losing_trades']}
   Win Rate:         {metrics['win_rate']}%

💰 P&L Metrics:
   Total P&L:        ${metrics['total_pnl']}
   Average Win:      ${metrics['avg_win']}
   Average Loss:     ${metrics['avg_loss']}
   Profit Factor:    {metrics['profit_factor']}x
   Return:           {metrics['return_percent']}%

📈 Risk Metrics:
   Sharpe Ratio:     {metrics['sharpe_ratio']}
   Max Drawdown:     ${metrics['max_drawdown']}
   Current Capital:  ${metrics['current_capital']}

"""
    
    def export_trades(self, filepath='reports/dummy_trades.json'):
        """Export all trades to JSON"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            trades_data = [t.to_dict() for t in self.trades]
            
            with open(filepath, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'symbol': self.symbol,
                    'total_trades': len(trades_data),
                    'performance': self.calculate_performance_metrics(),
                    'trades': trades_data
                }, f, indent=2)
            
            logger.info(f"✓ Exported {len(trades_data)} trades to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting trades: {e}")


if __name__ == '__main__':
    # Test the dummy trader
    print("\n🚀 Testing Dummy Trader\n")
    
    trader = LiveDummyTrader(symbol='XAUUSD')
    
    # Simulate some trades
    now = datetime.now()
    
    # Win trade
    trade1 = trader.execute_trade(
        entry_price=2000,
        entry_time=now,
        direction=1,
        strategy='ICTStrategy',
        signal_strength=7.5
    )
    trader.close_trade(trade1.trade_id, exit_price=2010, exit_time=now + timedelta(hours=2), bars_held=2)
    
    # Loss trade
    trade2 = trader.execute_trade(
        entry_price=2010,
        entry_time=now + timedelta(hours=3),
        direction=-1,
        strategy='ICTStrategy',
        signal_strength=6.0
    )
    trader.close_trade(trade2.trade_id, exit_price=2005, exit_time=now + timedelta(hours=5), bars_held=2)
    
    # Win trade
    trade3 = trader.execute_trade(
        entry_price=2005,
        entry_time=now + timedelta(hours=6),
        direction=1,
        strategy='ICTStrategy',
        signal_strength=8.0
    )
    trader.close_trade(trade3.trade_id, exit_price=2025, exit_time=now + timedelta(hours=10), bars_held=4)
    
    print(trader.get_performance_summary())
    trader.export_trades()
