"""
Backtester Module for Strategy Validation
Uses vectorbt for high-performance backtesting with realistic slippage and spread.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleBacktester:
    """Simple but effective backtester for trading signals (vectorbt alternative)."""
    
    def __init__(
        self,
        initial_capital: float = 10000,
        position_size: float = 0.95,  # 95% of capital per trade
        slippage_pips: float = 1.0,
        spread_pips: float = 0.5,
        pip_value: float = 1.0,  # For gold, 1 pip = 0.01
        commission_pct: float = 0.0010,  # 0.1% commission per trade (entry+exit)
        slippage_pct: float = 0.0005,  # 0.05% slippage per trade
        spread_pct: float = 0.0003  # 0.03% spread for gold futures
    ):
        """
        Initialize backtester with realistic transaction costs.
        
        Args:
            initial_capital: Starting capital in USD
            position_size: Fraction of capital per trade (0-1)
            slippage_pips: Entry/exit slippage in pips (legacy, use pct instead)
            spread_pips: Bid-ask spread in pips (legacy, use pct instead)
            pip_value: Value of 1 pip in USD
            commission_pct: Commission as % of trade value (default 0.1% = $10 per $10k)
            slippage_pct: Slippage as % of price (default 0.05% = realistic for gold)
            spread_pct: Bid-ask spread as % of price (default 0.03% for gold futures)
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.slippage_pips = slippage_pips
        self.spread_pips = spread_pips
        self.pip_value = pip_value
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.spread_pct = spread_pct
    
    def run_backtest(self, df: pd.DataFrame) -> Dict:
        """
        Run backtest on signal DataFrame.
        
        Args:
            df: DataFrame with columns: Close, Signal, EntryPrice, StopLoss, TakeProfit
        
        Returns:
            Dictionary with backtest results and metrics
        """
        # Validate required columns
        required_columns = ['Close', 'High', 'Low']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'gross_profit': 0,
                'gross_loss': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'trades': [],
                'error': f"Missing required columns: {missing_columns}"
            }
        
        # Check if Signal column exists; if not, create it with no signals
        if 'Signal' not in df.columns:
            logger.warning("Signal column not found in DataFrame. Creating empty signal column.")
            df = df.copy()
            df['Signal'] = 0
            df['EntryPrice'] = 0
            df['StopLoss'] = 0
            df['TakeProfit'] = 0
        
        # Ensure signal-related columns exist
        for col in ['Signal', 'EntryPrice', 'StopLoss', 'TakeProfit']:
            if col not in df.columns:
                df[col] = 0
        
        trades = []
        equity = self.initial_capital
        balance = self.initial_capital
        
        i = 0
        while i < len(df):
            signal = df['Signal'].iloc[i]
            
            if signal == 0:  # No signal
                i += 1
                continue
            
            entry_price = df['EntryPrice'].iloc[i]
            stop_loss = df['StopLoss'].iloc[i]
            take_profit = df['TakeProfit'].iloc[i]
            entry_time = df.index[i]
            
            # Calculate position size
            risk = abs(entry_price - stop_loss)
            if risk == 0:
                logger.warning(f"Invalid risk at index {i}")
                i += 1
                continue
            
            # Position size in lots (simplified)
            account_risk = balance * 0.02  # Risk 2% per trade
            contracts = account_risk / (risk * self.pip_value)
            
            # Apply realistic transaction costs (percentage-based)
            # Entry: slippage + spread + commission
            # Exit: slippage + commission
            entry_cost_pct = self.slippage_pct + self.spread_pct + (self.commission_pct / 2)
            exit_cost_pct = self.slippage_pct + (self.commission_pct / 2)
            
            if signal == 1:  # BUY
                # Pay spread + slippage + commission on entry
                entry = entry_price * (1 + entry_cost_pct)
                # Pay slippage + commission on exit
                exit_stop = stop_loss * (1 - exit_cost_pct)
                exit_profit = take_profit * (1 - exit_cost_pct)
            else:  # SELL
                # Pay spread + slippage + commission on entry
                entry = entry_price * (1 - entry_cost_pct)
                # Pay slippage + commission on exit
                exit_stop = stop_loss * (1 + exit_cost_pct)
                exit_profit = take_profit * (1 + exit_cost_pct)
            
            # Simulate trade until exit
            exit_index = None
            exit_price = None
            exit_type = None
            
            for j in range(i + 1, len(df)):
                high = df['High'].iloc[j]
                low = df['Low'].iloc[j]
                close = df['Close'].iloc[j]
                
                if signal == 1:  # BUY
                    if low <= exit_stop:
                        exit_index = j
                        exit_price = exit_stop
                        exit_type = 'SL'
                        break
                    elif high >= exit_profit:
                        exit_index = j
                        exit_price = exit_profit
                        exit_type = 'TP'
                        break
                else:  # SELL
                    if high >= exit_stop:
                        exit_index = j
                        exit_price = exit_stop
                        exit_type = 'SL'
                        break
                    elif low <= exit_profit:
                        exit_index = j
                        exit_price = exit_profit
                        exit_type = 'TP'
                        break
            
            # If no exit found, close at last candle
            if exit_index is None:
                exit_index = len(df) - 1
                exit_price = df['Close'].iloc[exit_index]
                exit_type = 'EOD'  # End of data
            
            exit_time = df.index[exit_index]
            
            # Calculate P&L
            if signal == 1:  # BUY
                pnl = (exit_price - entry) * contracts * self.pip_value / 0.01
            else:  # SELL
                pnl = (entry - exit_price) * contracts * self.pip_value / 0.01
            
            balance += pnl
            
            trade = {
                'entry_time': entry_time,
                'exit_time': exit_time,
                'direction': 'BUY' if signal == 1 else 'SELL',
                'entry_price': entry,
                'exit_price': exit_price,
                'exit_type': exit_type,
                'contracts': contracts,
                'pnl': pnl,
                'balance': balance,
                'return_pct': (pnl / (contracts * entry)) * 100 if contracts else 0
            }
            
            trades.append(trade)
            i = exit_index + 1
        
        # Calculate metrics
        trades_df = pd.DataFrame(trades)
        
        if len(trades_df) == 0:
            logger.warning("No completed trades in backtest")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl': 0,
                'gross_profit': 0,
                'gross_loss': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'trades': []
            }
        
        winning = trades_df[trades_df['pnl'] > 0]
        losing = trades_df[trades_df['pnl'] < 0]
        
        total_trades = len(trades_df)
        winning_trades = len(winning)
        losing_trades = len(losing)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        gross_profit = winning['pnl'].sum() if len(winning) > 0 else 0
        gross_loss = abs(losing['pnl'].sum()) if len(losing) > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        total_pnl = trades_df['pnl'].sum()
        avg_win = winning['pnl'].mean() if len(winning) > 0 else 0
        avg_loss = losing['pnl'].mean() if len(losing) > 0 else 0
        largest_win = winning['pnl'].max() if len(winning) > 0 else 0
        largest_loss = losing['pnl'].min() if len(losing) > 0 else 0
        
        # Drawdown calculation
        equity_curve = trades_df['balance'].values
        cummax = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown_pct = np.min(drawdown) * 100 if len(drawdown) > 0 else 0
        
        # Sharpe & Sortino ratios (simplified)
        returns = trades_df['pnl'].pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        downside_returns = returns[returns < 0]
        sortino_ratio = (returns.mean() / downside_returns.std() * np.sqrt(252)) if len(downside_returns) > 0 and downside_returns.std() > 0 else 0
        
        # Consecutive wins/losses
        results = np.sign(trades_df['pnl'].values)
        consecutive_wins = []
        consecutive_losses = []
        current_streak = 1
        
        for j in range(1, len(results)):
            if results[j] == results[j - 1]:
                current_streak += 1
            else:
                if results[j - 1] > 0:
                    consecutive_wins.append(current_streak)
                else:
                    consecutive_losses.append(current_streak)
                current_streak = 1
        
        max_consecutive_wins = max(consecutive_wins) if consecutive_wins else 0
        max_consecutive_losses = max(consecutive_losses) if consecutive_losses else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'trades': trades
        }
    
    def print_backtest_report(self, results: Dict) -> str:
        """
        Format backtest results as readable report.
        
        Args:
            results: Dictionary from run_backtest()
        
        Returns:
            Formatted report string
        """
        report = "\n" + "="*60 + "\n"
        report += "BACKTEST RESULTS REPORT\n"
        report += "="*60 + "\n\n"
        
        report += f"Total Trades:            {results['total_trades']}\n"
        report += f"Winning Trades:          {results['winning_trades']} ({results['win_rate']:.2f}%)\n"
        report += f"Losing Trades:           {results['losing_trades']}\n\n"
        
        report += f"Total P&L:               ${results['total_pnl']:.2f}\n"
        report += f"Gross Profit:            ${results['gross_profit']:.2f}\n"
        report += f"Gross Loss:              ${results['gross_loss']:.2f}\n"
        report += f"Profit Factor:           {results['profit_factor']:.2f}\n\n"
        
        report += f"Avg Win:                 ${results['avg_win']:.2f}\n"
        report += f"Avg Loss:                ${results['avg_loss']:.2f}\n"
        report += f"Largest Win:             ${results['largest_win']:.2f}\n"
        report += f"Largest Loss:            ${results['largest_loss']:.2f}\n\n"
        
        report += f"Max Consecutive Wins:    {results['max_consecutive_wins']}\n"
        report += f"Max Consecutive Losses:  {results['max_consecutive_losses']}\n"
        report += f"Max Drawdown:            {results['max_drawdown_pct']:.2f}%\n\n"
        
        report += f"Sharpe Ratio:            {results['sharpe_ratio']:.2f}\n"
        report += f"Sortino Ratio:           {results['sortino_ratio']:.2f}\n"
        report += "="*60 + "\n"
        
        return report


def export_trades_csv(trades: list, filepath: str) -> None:
    """Export trades to CSV file."""
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv(filepath, index=False)
    logger.info(f"Trades exported to {filepath}")


if __name__ == "__main__":
    from data_fetch import load_demo_data
    from zone_detector import ZoneDetector
    from signal_generator import SignalGenerator
    
    # Load data
    df = load_demo_data()
    df = df.tail(500)
    
    # Detect zones and generate signals
    detector = ZoneDetector()
    swing_highs, swing_lows = detector.detect_swings(df)
    zones = detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
    zones = detector.update_zone_mitigation(zones, df)
    
    obs = detector.detect_order_blocks(df)
    fvgs = detector.detect_fair_value_gaps(df)
    srl = detector.detect_support_resistance(df)
    
    generator = SignalGenerator()
    df = generator.generate_signals(df, zones, obs, fvgs, srl)
    
    # Run backtest
    backtester = SimpleBacktester(initial_capital=10000)
    results = backtester.run_backtest(df)
    
    # Print report
    report = backtester.print_backtest_report(results)
    print(report)
    
    # Export trades
    export_trades_csv(results['trades'], './reports/trades.csv')
