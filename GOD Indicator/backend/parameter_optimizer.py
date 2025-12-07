"""
Parameter Optimizer - Hit and Trial optimization for strategy parameters
Tests different parameter combinations to find best performing setup
"""

import pandas as pd
import numpy as np
from itertools import product
import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParameterOptimizer:
    """
    Optimize strategy parameters using grid search (hit and trial method)
    Tests all parameter combinations and ranks by win rate, profit factor, or Sharpe ratio
    """
    
    def __init__(self, strategy_class, optimization_metric='win_rate'):
        """
        Initialize parameter optimizer
        
        Args:
            strategy_class: Strategy class to optimize
            optimization_metric (str): 'win_rate', 'profit_factor', 'sharpe_ratio', or 'return'
        """
        self.strategy_class = strategy_class
        self.optimization_metric = optimization_metric
        self.results = []
        self.best_params = None
        self.best_score = -np.inf
    
    def get_parameter_grid(self):
        """
        Define parameter grid for optimization
        Customize based on strategy
        
        Returns:
            dict: {param_name: [values_to_test]}
        """
        # For ICT Strategy
        if 'ICT' in self.strategy_class.__name__:
            return {
                'lookback_period': [100, 150, 200, 250],
                'fvg_threshold': [0.0003, 0.0005, 0.0008, 0.001],
                'ob_threshold': [1, 2, 3],
            }
        
        # For EMA 30 Strategy (9 EMA + 30 WMA with pullback)
        elif 'EMA' in self.strategy_class.__name__:
            return {
                'fast_period': [9, 10, 12, 15],  # 9 EMA period variations
                'slow_period': [25, 30, 35, 40],  # 30 WMA period variations
                'rsi_period': [12, 14, 16],  # RSI period for confirmation
                'pullback_bars': [2, 3, 4, 5],  # Pullback zone detection window
            }
        
        else:
            return {}
    
    def optimize(self, df, initial_capital=10000, verbose=True):
        """
        Run grid search optimization
        
        Args:
            df (pd.DataFrame): Historical OHLCV data
            initial_capital (float): Initial capital for backtesting
            verbose (bool): Print progress
            
        Returns:
            list: Ranked results [best to worst]
        """
        param_grid = self.get_parameter_grid()
        
        if not param_grid:
            logger.warning("No parameter grid defined for this strategy")
            return []
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))
        
        total_combinations = len(param_combinations)
        logger.info(f"Testing {total_combinations} parameter combinations...")
        
        for idx, combination in enumerate(param_combinations, 1):
            params = dict(zip(param_names, combination))
            
            try:
                # Create strategy with parameters
                strategy = self.strategy_class(**params)
                
                # Generate signals
                df_signals = strategy.generate_signals(df.copy())
                
                # Calculate metrics (simplified backtest)
                metrics = self._backtest_signals(df_signals, initial_capital)
                
                # Store result
                result = {
                    'params': params,
                    'metrics': metrics,
                    'score': metrics.get(self.optimization_metric, 0)
                }
                self.results.append(result)
                
                # Track best
                if result['score'] > self.best_score:
                    self.best_score = result['score']
                    self.best_params = params
                
                if verbose and idx % max(1, total_combinations // 10) == 0:
                    logger.info(f"Progress: {idx}/{total_combinations} - Best score: {self.best_score:.2f}")
                    
            except Exception as e:
                logger.warning(f"Error testing params {params}: {e}")
                continue
        
        # Sort by optimization metric
        self.results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"\n✓ Optimization complete!")
        logger.info(f"  Best parameters: {self.best_params}")
        logger.info(f"  Best {self.optimization_metric}: {self.best_score:.2f}")
        
        return self.results
    
    def _backtest_signals(self, df_signals, initial_capital=10000):
        """
        Simple backtest on signals to calculate metrics
        
        Args:
            df_signals (pd.DataFrame): DataFrame with signals
            initial_capital (float): Initial capital
            
        Returns:
            dict: Performance metrics
        """
        if 'Signal' not in df_signals.columns:
            return self._get_empty_metrics()
        
        trades = []
        position = None
        
        for i in range(len(df_signals)):
            signal = df_signals.iloc[i]['Signal']
            
            # Close existing position
            if position and (signal == -1 * position['direction'] or signal == 0):
                position['exit_price'] = df_signals.iloc[i]['Close']
                position['pnl'] = (position['exit_price'] - position['entry_price']) * position['direction']
                position['pnl_percent'] = (position['pnl'] / position['entry_price']) * 100
                trades.append(position)
                position = None
            
            # Open new position
            if signal != 0 and position is None:
                position = {
                    'entry_price': df_signals.iloc[i]['Close'],
                    'direction': signal,
                    'entry_idx': i,
                    'exit_price': None,
                    'pnl': None,
                }
        
        # Close remaining position
        if position:
            position['exit_price'] = df_signals.iloc[-1]['Close']
            position['pnl'] = (position['exit_price'] - position['entry_price']) * position['direction']
            position['pnl_percent'] = (position['pnl'] / position['entry_price']) * 100
            trades.append(position)
        
        if not trades:
            return self._get_empty_metrics()
        
        # Calculate metrics
        df_trades = pd.DataFrame(trades)
        
        total_trades = len(df_trades)
        winning = (df_trades['pnl'] > 0).sum()
        losing = (df_trades['pnl'] <= 0).sum()
        
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        
        wins_sum = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        losses_sum = df_trades[df_trades['pnl'] <= 0]['pnl'].sum()
        
        avg_win = (wins_sum / winning) if winning > 0 else 0
        avg_loss = (abs(losses_sum) / losing) if losing > 0 else 0
        
        profit_factor = (wins_sum / abs(losses_sum)) if losses_sum < 0 else (wins_sum if wins_sum > 0 else 0)
        
        total_return = df_trades['pnl'].sum()
        return_percent = (total_return / initial_capital) * 100
        
        # Sharpe Ratio
        pnl_array = df_trades['pnl'].values
        if len(pnl_array) > 1 and np.std(pnl_array) > 0:
            sharpe_ratio = np.mean(pnl_array) / np.std(pnl_array)
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 4),
            'avg_loss': round(avg_loss, 4),
            'profit_factor': round(profit_factor, 2),
            'total_return': round(total_return, 2),
            'return_percent': round(return_percent, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
        }
    
    def _get_empty_metrics(self):
        """Return empty metrics"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'total_return': 0,
            'return_percent': 0,
            'sharpe_ratio': 0,
        }
    
    def get_top_parameters(self, top_n=10):
        """
        Get top N best parameter combinations
        
        Args:
            top_n (int): Number of top results to return
            
        Returns:
            list: Top N results
        """
        return self.results[:top_n]
    
    def print_results(self, top_n=10):
        """Print optimization results"""
        if not self.results:
            logger.info("No results to display")
            return
        
        print("\n" + "="*100)
        print("PARAMETER OPTIMIZATION RESULTS (Top 10)")
        print("="*100 + "\n")
        
        print(f"{'Rank':<5} {'Win Rate':<12} {'Profit Factor':<15} {'Sharpe Ratio':<15} {'Parameters':<50}")
        print("-"*100)
        
        for rank, result in enumerate(self.results[:top_n], 1):
            metrics = result['metrics']
            params_str = str(result['params'])[:40] + "..." if len(str(result['params'])) > 40 else str(result['params'])
            
            print(f"{rank:<5} {metrics['win_rate']:<12.2f} {metrics['profit_factor']:<15.2f} {metrics['sharpe_ratio']:<15.2f} {params_str:<50}")
        
        print("\n")
    
    def export_results(self, filepath='reports/optimization_results.json'):
        """Export optimization results to JSON"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'strategy': self.strategy_class.__name__,
                'optimization_metric': self.optimization_metric,
                'best_params': self.best_params,
                'best_score': self.best_score,
                'total_combinations_tested': len(self.results),
                'top_10_results': self.results[:10]
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"✓ Optimization results exported to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting results: {e}")


if __name__ == '__main__':
    # Test optimizer (example)
    print("\n🚀 Parameter Optimizer Test\n")
    
    from ict_strategy import ICTStrategy
    from data_fetch_yfinance import YFinanceDataFetcher
    
    # Fetch data
    fetcher = YFinanceDataFetcher()
    df = fetcher.fetch_historical_data('XAUUSD', period='1y', interval='1d')
    
    # Run optimization
    optimizer = ParameterOptimizer(ICTStrategy, optimization_metric='win_rate')
    results = optimizer.optimize(df, verbose=True)
    
    # Display results
    optimizer.print_results(top_n=10)
    optimizer.export_results()
