"""
Enhanced backtester with advanced analytics and multi-strategy support.
Calculates detailed performance metrics and risk analysis.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from datetime import datetime


@dataclass
class BacktestMetrics:
    """Comprehensive backtest result metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    gross_profit: float
    gross_loss: float
    average_win: float
    average_loss: float
    profit_factor: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_duration: int  # bars
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Return metrics
    total_return: float
    annualized_return: float
    monthly_return: float
    
    # Additional metrics
    recovery_factor: float
    ulcer_index: float
    expectancy: float
    risk_reward_ratio: float
    
    @property
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class EnhancedBacktester:
    """
    Enhanced backtester with comprehensive analytics.
    Supports multiple strategies and advanced performance metrics.
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 risk_per_trade: float = 0.02,
                 slippage: float = 0.001,
                 commission: float = 0.001):
        """
        Initialize backtester
        
        Args:
            initial_capital: Starting capital in USD
            risk_per_trade: Risk percentage per trade (0-1)
            slippage: Slippage percentage per trade (0-1)
            commission: Commission percentage per trade (0-1)
        """
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.slippage = slippage
        self.commission = commission
        
        self.trades = []
        self.equity_curve = []
        self.drawdown_curve = []
    
    def run_backtest(self, df: pd.DataFrame, strategy_name: str = "Strategy") -> Dict:
        """
        Run backtest on price data with signals
        
        Args:
            df: DataFrame with OHLCV and Signal columns
            strategy_name: Name of strategy being tested
            
        Returns:
            Dict with metrics and trade details
        """
        if 'Signal' not in df.columns:
            raise ValueError("DataFrame must have 'Signal' column")
        
        df = df.copy()
        df.reset_index(drop=True, inplace=True)
        
        self.trades = []
        self.equity_curve = [self.initial_capital]
        
        current_position = 0  # 0: flat, 1: long, -1: short
        entry_price = 0
        entry_index = 0
        
        # Iterate through bars
        for i in range(len(df)):
            signal = df.loc[i, 'Signal']
            close = df.loc[i, 'Close']
            
            # Exit logic
            if current_position != 0 and signal != 0 and signal != current_position:
                # Close position
                exit_price = close * (1 - self.slippage)
                
                pnl = (exit_price - entry_price) * current_position
                pnl_after_fees = pnl - (abs(entry_price + exit_price) * self.commission)
                
                self.trades.append({
                    'entry_index': entry_index,
                    'exit_index': i,
                    'entry_time': df.index[entry_index],
                    'exit_time': df.index[i],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'direction': current_position,
                    'pnl': pnl_after_fees,
                    'pnl_percent': (pnl_after_fees / entry_price) * 100,
                    'bars_held': i - entry_index
                })
                
                current_position = 0
            
            # Entry logic
            if current_position == 0 and signal != 0:
                entry_price = close * (1 + self.slippage)
                entry_index = i
                current_position = signal
            
            # Update equity curve
            if current_position != 0:
                # P&L of open position
                current_equity = self.equity_curve[-1] + (close - entry_price) * current_position
            else:
                current_equity = self.equity_curve[-1]
            
            self.equity_curve.append(current_equity)
        
        # Close final position if open
        if current_position != 0:
            exit_price = df.loc[len(df)-1, 'Close'] * (1 - self.slippage)
            pnl = (exit_price - entry_price) * current_position
            pnl_after_fees = pnl - (abs(entry_price + exit_price) * self.commission)
            
            self.trades.append({
                'entry_index': entry_index,
                'exit_index': len(df)-1,
                'entry_time': df.index[entry_index],
                'exit_time': df.index[-1],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'direction': current_position,
                'pnl': pnl_after_fees,
                'pnl_percent': (pnl_after_fees / entry_price) * 100,
                'bars_held': len(df) - 1 - entry_index
            })
        
        # Calculate metrics
        metrics = self._calculate_metrics(df)
        
        return {
            'strategy': strategy_name,
            'metrics': metrics.to_dict if hasattr(metrics, 'to_dict') else metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'drawdown_curve': self.drawdown_curve
        }
    
    def _calculate_metrics(self, df: pd.DataFrame) -> BacktestMetrics:
        """Calculate comprehensive performance metrics"""
        
        if not self.trades:
            return BacktestMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl=0,
                gross_profit=0,
                gross_loss=0,
                average_win=0,
                average_loss=0,
                profit_factor=0,
                max_drawdown=0,
                max_drawdown_duration=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                calmar_ratio=0,
                total_return=0,
                annualized_return=0,
                monthly_return=0,
                recovery_factor=0,
                ulcer_index=0,
                expectancy=0,
                risk_reward_ratio=0
            )
        
        # Basic trade stats
        trades_df = pd.DataFrame(self.trades)
        total_pnl = trades_df['pnl'].sum()
        winning = trades_df[trades_df['pnl'] > 0]
        losing = trades_df[trades_df['pnl'] <= 0]
        
        total_trades = len(trades_df)
        winning_trades = len(winning)
        losing_trades = len(losing)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        gross_profit = winning['pnl'].sum() if len(winning) > 0 else 0
        gross_loss = abs(losing['pnl'].sum()) if len(losing) > 0 else 0
        
        average_win = winning['pnl'].mean() if len(winning) > 0 else 0
        average_loss = losing['pnl'].mean() if len(losing) > 0 else 0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Drawdown analysis
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max * 100
        
        self.drawdown_curve = drawdown
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        # Drawdown duration
        drawdown_duration = 0
        current_duration = 0
        for dd in drawdown:
            if dd < 0:
                current_duration += 1
                drawdown_duration = max(drawdown_duration, current_duration)
            else:
                current_duration = 0
        
        # Return metrics
        total_return = ((self.equity_curve[-1] - self.initial_capital) / 
                       self.initial_capital * 100)
        
        # Sharpe ratio (assuming 252 trading days, 0% risk-free rate)
        returns = np.diff(self.equity_curve) / np.array(self.equity_curve[:-1])
        daily_return = returns.mean()
        daily_std = returns.std()
        sharpe_ratio = (daily_return / daily_std * np.sqrt(252)) if daily_std > 0 else 0
        
        # Sortino ratio (only downside volatility)
        negative_returns = returns[returns < 0]
        downside_std = negative_returns.std() if len(negative_returns) > 0 else 0
        sortino_ratio = (daily_return / downside_std * np.sqrt(252)) if downside_std > 0 else 0
        
        # Calmar ratio
        calmar_ratio = (daily_return * 252 / abs(max_drawdown / 100)) if max_drawdown != 0 else 0
        
        # Recovery factor
        recovery_factor = total_pnl / abs(gross_loss) if gross_loss > 0 else 0
        
        # Ulcer index
        ulcer_index = np.sqrt(np.mean(np.where(drawdown < 0, drawdown ** 2, 0)))
        
        # Expectancy
        expectancy = (win_rate / 100 * average_win + 
                     (1 - win_rate / 100) * average_loss)
        
        # Risk/Reward ratio
        risk_reward = abs(average_win / average_loss) if average_loss != 0 else 0
        
        # Annualized return (assuming 252 trading days per year)
        annualized = ((self.equity_curve[-1] / self.initial_capital) ** 
                     (252 / len(df)) - 1) * 100 if len(df) > 0 else 0
        
        # Monthly return approximation
        monthly_return = total_return / (len(df) / 252 * 12) if len(df) > 0 else 0
        
        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_duration=drawdown_duration,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_return=total_return,
            annualized_return=annualized,
            monthly_return=monthly_return,
            recovery_factor=recovery_factor,
            ulcer_index=ulcer_index,
            expectancy=expectancy,
            risk_reward_ratio=risk_reward
        )
    
    def get_trade_analysis(self) -> Dict:
        """Get detailed trade analysis"""
        if not self.trades:
            return {'message': 'No trades executed'}
        
        trades_df = pd.DataFrame(self.trades)
        
        return {
            'total_trades': len(trades_df),
            'average_bars_held': trades_df['bars_held'].mean(),
            'longest_winner': trades_df[trades_df['pnl'] > 0]['pnl'].max() if len(trades_df[trades_df['pnl'] > 0]) > 0 else 0,
            'longest_loser': trades_df[trades_df['pnl'] < 0]['pnl'].min() if len(trades_df[trades_df['pnl'] < 0]) > 0 else 0,
            'consecutive_wins': self._get_consecutive_wins(),
            'consecutive_losses': self._get_consecutive_losses(),
            'trades': trades_df.to_dict('records')
        }
    
    def _get_consecutive_wins(self) -> int:
        """Get maximum consecutive winning trades"""
        if not self.trades:
            return 0
        
        max_wins = 0
        current_wins = 0
        
        for trade in self.trades:
            if trade['pnl'] > 0:
                current_wins += 1
                max_wins = max(max_wins, current_wins)
            else:
                current_wins = 0
        
        return max_wins
    
    def _get_consecutive_losses(self) -> int:
        """Get maximum consecutive losing trades"""
        if not self.trades:
            return 0
        
        max_losses = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade['pnl'] <= 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        
        return max_losses
