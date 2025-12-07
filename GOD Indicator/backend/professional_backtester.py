"""
Professional Backtester - Industry-standard backtesting engine
Features: Realistic execution (commissions, slippage), position sizing, equity tracking
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    initial_capital: float = 100000  # Starting capital
    commission: float = 0.001  # 0.1% per trade
    slippage: float = 0.0005  # 0.05% slippage
    position_size_percent: float = 0.95  # Use 95% of capital per trade
    max_position_size: Optional[float] = None  # Max units per trade (None = no limit)
    use_atr_stop_loss: bool = True  # Use ATR for stop loss
    atr_multiplier: float = 2.0  # Stop loss at 2 * ATR
    take_profit_atr_multiplier: float = 3.0  # Take profit at 3 * ATR


@dataclass
class Trade:
    """Represents a single trade"""
    entry_date: datetime
    entry_price: float
    entry_qty: float
    entry_commission: float
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_qty: Optional[float] = None
    exit_commission: Optional[float] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0
    direction: str = 'LONG'  # LONG or SHORT


@dataclass
class BacktestResult:
    """Complete backtest results"""
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    dates: List[datetime] = field(default_factory=list)
    initial_capital: float = 0
    final_capital: float = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    total_return_percent: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_trade: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    recovery_factor: float = 0.0


class ProfessionalBacktester:
    """
    Industry-standard backtester with realistic trade execution
    
    4-Step Process:
    1. Data Acquisition: Load historical OHLCV data
    2. Strategy Implementation: Generate buy/sell signals
    3. Backtesting: Execute trades with realistic costs
    4. Performance Analysis: Calculate comprehensive metrics
    """
    
    def __init__(self, config: BacktestConfig = None):
        """Initialize backtester"""
        self.config = config or BacktestConfig()
        self.result = BacktestResult()
    
    def backtest(self, df: pd.DataFrame, signals: pd.Series) -> BacktestResult:
        """
        Run complete backtest
        
        Args:
            df: DataFrame with OHLCV data (must have columns: Open, High, Low, Close, Volume)
            signals: Series with signals (1=BUY, -1=SELL, 0=HOLD)
        
        Returns:
            BacktestResult with complete analysis
        """
        logger.info("=" * 60)
        logger.info("BACKTESTING INITIATED")
        logger.info("=" * 60)
        
        # Validate inputs
        if df.empty or len(signals) == 0:
            logger.error("Empty data or signals")
            return self.result
        
        if len(df) != len(signals):
            logger.error(f"Data length {len(df)} != signals length {len(signals)}")
            return self.result
        
        # Reset state
        self.result = BacktestResult()
        self.result.initial_capital = self.config.initial_capital
        
        # Trading state
        current_position = None  # Current open trade
        cash = self.config.initial_capital
        equity = self.config.initial_capital
        
        # History
        equity_curve = [equity]
        dates = []
        
        # Process each bar
        for i in range(len(df)):
            bar = df.iloc[i]
            signal = signals.iloc[i]
            
            dates.append(bar['DateTime'] if 'DateTime' in bar else i)
            
            # Close position on SELL signal
            if signal == -1 and current_position is not None:
                exit_price = bar['Close'] * (1 + self.config.slippage)
                exit_commission = exit_price * current_position.entry_qty * self.config.commission
                
                current_position.exit_date = dates[-1]
                current_position.exit_price = exit_price
                current_position.exit_qty = current_position.entry_qty
                current_position.exit_commission = exit_commission
                
                # Calculate PnL
                pnl = (exit_price - current_position.entry_price) * current_position.entry_qty
                pnl -= exit_commission + current_position.entry_commission
                
                current_position.pnl = pnl
                current_position.pnl_percent = (pnl / (current_position.entry_price * current_position.entry_qty)) * 100
                
                self.result.trades.append(current_position)
                
                # Update cash
                cash += exit_price * current_position.entry_qty - exit_commission
                
                logger.info(f"[{dates[-1]}] SELL: {current_position.entry_qty:.2f} @ ₹{exit_price:.2f} | PnL: ₹{pnl:.2f} ({current_position.pnl_percent:.2f}%)")
                
                current_position = None
            
            # Open position on BUY signal
            elif signal == 1 and current_position is None:
                entry_price = bar['Close'] * (1 + self.config.slippage)
                
                # Calculate position size
                if self.config.max_position_size:
                    qty = min(
                        self.config.max_position_size,
                        (cash * self.config.position_size_percent) / entry_price
                    )
                else:
                    qty = (cash * self.config.position_size_percent) / entry_price
                
                entry_commission = entry_price * qty * self.config.commission
                
                current_position = Trade(
                    entry_date=dates[-1],
                    entry_price=entry_price,
                    entry_qty=qty,
                    entry_commission=entry_commission,
                    direction='LONG'
                )
                
                # Update cash
                cash -= entry_price * qty + entry_commission
                
                logger.info(f"[{dates[-1]}] BUY: {qty:.2f} @ ₹{entry_price:.2f} | Cash: ₹{cash:.2f}")
            
            # Update equity
            if current_position is not None:
                unrealized_pnl = (bar['Close'] - current_position.entry_price) * current_position.entry_qty
                equity = cash + (current_position.entry_price * current_position.entry_qty) + unrealized_pnl
            else:
                equity = cash
            
            equity_curve.append(equity)
        
        # Close any remaining position at last price
        if current_position is not None:
            last_bar = df.iloc[-1]
            exit_price = last_bar['Close']
            exit_commission = exit_price * current_position.entry_qty * self.config.commission
            
            current_position.exit_date = dates[-1]
            current_position.exit_price = exit_price
            current_position.exit_qty = current_position.entry_qty
            current_position.exit_commission = exit_commission
            
            pnl = (exit_price - current_position.entry_price) * current_position.entry_qty
            pnl -= exit_commission + current_position.entry_commission
            
            current_position.pnl = pnl
            current_position.pnl_percent = (pnl / (current_position.entry_price * current_position.entry_qty)) * 100
            
            self.result.trades.append(current_position)
        
        # Store results
        self.result.equity_curve = equity_curve
        self.result.dates = dates
        self.result.final_capital = equity_curve[-1]
        
        # Calculate metrics
        self._calculate_metrics()
        
        logger.info("=" * 60)
        logger.info("BACKTEST COMPLETE")
        logger.info("=" * 60)
        
        return self.result
    
    def _calculate_metrics(self) -> None:
        """Calculate comprehensive performance metrics"""
        
        if not self.result.trades:
            logger.warning("No trades executed")
            return
        
        # Basic trade statistics
        self.result.total_trades = len(self.result.trades)
        
        pnl_values = [t.pnl for t in self.result.trades]
        winning_trades = [t for t in self.result.trades if t.pnl > 0]
        losing_trades = [t for t in self.result.trades if t.pnl < 0]
        
        self.result.winning_trades = len(winning_trades)
        self.result.losing_trades = len(losing_trades)
        self.result.win_rate = (self.result.winning_trades / self.result.total_trades * 100) if self.result.total_trades > 0 else 0
        
        # Return metrics
        self.result.total_return = self.result.final_capital - self.result.initial_capital
        self.result.total_return_percent = (self.result.total_return / self.result.initial_capital) * 100
        
        # Trade metrics
        if pnl_values:
            self.result.best_trade = max(pnl_values)
            self.result.worst_trade = min(pnl_values)
            self.result.avg_trade = np.mean(pnl_values)
        
        # Profit factor
        gross_profit = sum([t.pnl for t in winning_trades])
        gross_loss = abs(sum([t.pnl for t in losing_trades]))
        self.result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Drawdown metrics
        equity_array = np.array(self.result.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        
        self.result.max_drawdown = np.min(running_max - equity_array)
        self.result.max_drawdown_percent = np.min(drawdown) * 100
        
        # Risk-adjusted returns
        self._calculate_risk_metrics()
        
        # Log summary
        self._log_summary()
    
    def _calculate_risk_metrics(self) -> None:
        """Calculate Sharpe, Sortino, Calmar ratios"""
        
        if len(self.result.equity_curve) < 2:
            return
        
        # Daily returns
        returns = np.diff(self.result.equity_curve) / np.array(self.result.equity_curve[:-1])
        
        if len(returns) == 0:
            return
        
        # Sharpe Ratio (assuming 252 trading days per year)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return > 0:
            self.result.sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
        
        # Sortino Ratio (only downside volatility)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = np.std(downside_returns)
            if downside_std > 0:
                self.result.sortino_ratio = (mean_return / downside_std) * np.sqrt(252)
        
        # Calmar Ratio
        if self.result.max_drawdown_percent != 0:
            self.result.calmar_ratio = self.result.total_return_percent / abs(self.result.max_drawdown_percent)
        
        # Recovery Factor
        if self.result.max_drawdown != 0:
            self.result.recovery_factor = self.result.total_return / self.result.max_drawdown
    
    def _log_summary(self) -> None:
        """Log performance summary"""
        
        logger.info("\n" + "=" * 60)
        logger.info("PERFORMANCE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Initial Capital:        ₹{self.result.initial_capital:,.2f}")
        logger.info(f"Final Capital:          ₹{self.result.final_capital:,.2f}")
        logger.info(f"Total Return:           ₹{self.result.total_return:,.2f} ({self.result.total_return_percent:.2f}%)")
        logger.info("")
        logger.info(f"Total Trades:           {self.result.total_trades}")
        logger.info(f"Winning Trades:         {self.result.winning_trades}")
        logger.info(f"Losing Trades:          {self.result.losing_trades}")
        logger.info(f"Win Rate:               {self.result.win_rate:.2f}%")
        logger.info("")
        logger.info(f"Best Trade:             ₹{self.result.best_trade:,.2f}")
        logger.info(f"Worst Trade:            ₹{self.result.worst_trade:,.2f}")
        logger.info(f"Avg Trade:              ₹{self.result.avg_trade:,.2f}")
        logger.info(f"Profit Factor:          {self.result.profit_factor:.2f}")
        logger.info("")
        logger.info(f"Max Drawdown:           ₹{self.result.max_drawdown:,.2f} ({self.result.max_drawdown_percent:.2f}%)")
        logger.info(f"Sharpe Ratio:           {self.result.sharpe_ratio:.2f}")
        logger.info(f"Sortino Ratio:          {self.result.sortino_ratio:.2f}")
        logger.info(f"Calmar Ratio:           {self.result.calmar_ratio:.2f}")
        logger.info(f"Recovery Factor:        {self.result.recovery_factor:.2f}")
        logger.info("=" * 60 + "\n")
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """Export trades as DataFrame"""
        if not self.result.trades:
            return pd.DataFrame()
        
        trades_data = []
        for i, trade in enumerate(self.result.trades, 1):
            trades_data.append({
                'Trade_ID': i,
                'Entry_Date': trade.entry_date,
                'Entry_Price': trade.entry_price,
                'Entry_Qty': trade.entry_qty,
                'Exit_Date': trade.exit_date,
                'Exit_Price': trade.exit_price,
                'Exit_Qty': trade.exit_qty,
                'PnL': trade.pnl,
                'PnL_%': trade.pnl_percent,
                'Duration_Days': (trade.exit_date - trade.entry_date).days if trade.exit_date else 0
            })
        
        return pd.DataFrame(trades_data)
    
    def get_equity_dataframe(self) -> pd.DataFrame:
        """Export equity curve as DataFrame"""
        return pd.DataFrame({
            'DateTime': self.result.dates,
            'Equity': self.result.equity_curve
        })
