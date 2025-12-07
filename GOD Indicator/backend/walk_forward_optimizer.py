"""
Walk-Forward Optimization - Prevents Overfitting
Trains on past data, tests on future unseen data (out-of-sample)
More realistic than standard backtesting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from itertools import product
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization for robust strategy validation
    
    Process:
    1. Split data into windows (e.g., 6 months training + 3 months testing)
    2. Optimize parameters on training window
    3. Test best parameters on out-of-sample testing window
    4. Move window forward and repeat
    5. Aggregate results to see true performance
    """
    
    def __init__(self,
                 strategy_class,
                 training_window_months: int = 6,
                 testing_window_months: int = 3,
                 optimization_metric: str = 'sharpe_ratio'):
        """
        Initialize walk-forward optimizer
        
        Args:
            strategy_class: Strategy class to optimize
            training_window_months: Months of data for optimization
            testing_window_months: Months of data for out-of-sample testing
            optimization_metric: Metric to optimize ('win_rate', 'profit_factor', 'sharpe_ratio')
        """
        self.strategy_class = strategy_class
        self.training_months = training_window_months
        self.testing_months = testing_window_months
        self.optimization_metric = optimization_metric
        self.results = []
        self.best_params_per_window = []
    
    def get_parameter_grid(self) -> Dict:
        """Define parameter grid for strategy"""
        if 'ICT' in self.strategy_class.__name__:
            return {
                'lookback_period': [100, 150, 200],
                'fvg_threshold': [0.0003, 0.0005, 0.0008],
                'ob_threshold': [1, 2, 3],
            }
        elif 'EMA' in self.strategy_class.__name__:
            return {
                'fast_period': [9, 12, 15],
                'slow_period': [25, 30, 35],
                'rsi_period': [12, 14, 16],
                'pullback_bars': [2, 3, 4],
            }
        else:
            return {}
    
    def split_data_by_date(self, df: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Split data into overlapping train/test windows
        
        Args:
            df: Full dataset with DatetimeIndex
            
        Returns:
            List of (train_df, test_df) tuples
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.error("DataFrame must have DatetimeIndex")
            return []
        
        windows = []
        
        # Calculate window sizes
        train_days = self.training_months * 30
        test_days = self.testing_months * 30
        step_days = test_days  # Move forward by test window size
        
        start_date = df.index[0]
        end_date = df.index[-1]
        
        current_start = start_date
        
        while current_start + timedelta(days=train_days + test_days) <= end_date:
            # Training window
            train_end = current_start + timedelta(days=train_days)
            train_df = df[current_start:train_end]
            
            # Testing window (immediately after training)
            test_start = train_end
            test_end = test_start + timedelta(days=test_days)
            test_df = df[test_start:test_end]
            
            if len(train_df) > 0 and len(test_df) > 0:
                windows.append((train_df, test_df))
                logger.info(f"Window {len(windows)}: Train {current_start.date()} to {train_end.date()}, "
                          f"Test {test_start.date()} to {test_end.date()}")
            
            # Move to next window
            current_start += timedelta(days=step_days)
        
        logger.info(f"Created {len(windows)} walk-forward windows")
        return windows
    
    def optimize_on_window(self, train_df: pd.DataFrame, verbose: bool = False) -> Tuple[Dict, float]:
        """
        Optimize parameters on training window
        
        Args:
            train_df: Training data
            verbose: Print progress
            
        Returns:
            Tuple of (best_params, best_score)
        """
        param_grid = self.get_parameter_grid()
        
        if not param_grid:
            logger.warning("No parameter grid defined")
            return {}, 0.0
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        best_params = None
        best_score = -np.inf
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            try:
                # Create strategy with params
                strategy = self.strategy_class(**params)
                
                # Generate signals
                df_signals = strategy.generate_signals(train_df.copy())
                
                # Quick backtest
                metrics = self._quick_backtest(df_signals)
                
                score = metrics.get(self.optimization_metric, 0)
                
                if score > best_score:
                    best_score = score
                    best_params = params
                    
            except Exception as e:
                if verbose:
                    logger.warning(f"Error testing params {params}: {e}")
                continue
        
        if verbose:
            logger.info(f"  Best {self.optimization_metric}: {best_score:.2f} with {best_params}")
        
        return best_params, best_score
    
    def test_on_window(self, test_df: pd.DataFrame, params: Dict) -> Dict:
        """
        Test parameters on out-of-sample window
        
        Args:
            test_df: Testing data (unseen)
            params: Parameters to test
            
        Returns:
            Performance metrics dictionary
        """
        try:
            # Create strategy with optimized params
            strategy = self.strategy_class(**params)
            
            # Generate signals on unseen data
            df_signals = strategy.generate_signals(test_df.copy())
            
            # Backtest
            metrics = self._quick_backtest(df_signals)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error testing on window: {e}")
            return self._get_empty_metrics()
    
    def run_walk_forward(self, df: pd.DataFrame, verbose: bool = True) -> Dict:
        """
        Run complete walk-forward optimization
        
        Args:
            df: Full historical dataset
            verbose: Print detailed progress
            
        Returns:
            Aggregated results dictionary
        """
        if verbose:
            logger.info(f"\n{'='*70}")
            logger.info(f"WALK-FORWARD OPTIMIZATION")
            logger.info(f"  Training: {self.training_months} months")
            logger.info(f"  Testing: {self.testing_months} months")
            logger.info(f"  Metric: {self.optimization_metric}")
            logger.info(f"{'='*70}\n")
        
        # Split data into windows
        windows = self.split_data_by_date(df)
        
        if not windows:
            logger.error("Failed to create walk-forward windows")
            return {'error': 'No windows created'}
        
        # Process each window
        all_test_metrics = []
        
        for i, (train_df, test_df) in enumerate(windows, 1):
            if verbose:
                logger.info(f"\n{'─'*70}")
                logger.info(f"WINDOW {i}/{len(windows)}")
                logger.info(f"{'─'*70}")
            
            # Optimize on training data
            best_params, train_score = self.optimize_on_window(train_df, verbose=verbose)
            
            # Test on unseen data
            test_metrics = self.test_on_window(test_df, best_params)
            
            # Store results
            window_result = {
                'window': i,
                'train_start': train_df.index[0],
                'train_end': train_df.index[-1],
                'test_start': test_df.index[0],
                'test_end': test_df.index[-1],
                'best_params': best_params,
                'train_score': train_score,
                'test_metrics': test_metrics
            }
            
            self.results.append(window_result)
            self.best_params_per_window.append(best_params)
            all_test_metrics.append(test_metrics)
            
            if verbose:
                logger.info(f"  Train {self.optimization_metric}: {train_score:.2f}")
                logger.info(f"  Test Win Rate: {test_metrics.get('win_rate', 0):.1f}%")
                logger.info(f"  Test Profit Factor: {test_metrics.get('profit_factor', 0):.2f}")
                logger.info(f"  Test Sharpe: {test_metrics.get('sharpe_ratio', 0):.2f}")
        
        # Aggregate all out-of-sample results
        aggregated = self._aggregate_metrics(all_test_metrics)
        
        if verbose:
            logger.info(f"\n{'='*70}")
            logger.info(f"WALK-FORWARD RESULTS (OUT-OF-SAMPLE)")
            logger.info(f"{'='*70}")
            logger.info(f"  Total Windows: {len(windows)}")
            logger.info(f"  Avg Win Rate: {aggregated['avg_win_rate']:.1f}%")
            logger.info(f"  Avg Profit Factor: {aggregated['avg_profit_factor']:.2f}")
            logger.info(f"  Avg Sharpe Ratio: {aggregated['avg_sharpe_ratio']:.2f}")
            logger.info(f"  Total Return: {aggregated['total_return_pct']:.2f}%")
            logger.info(f"  Consistency Score: {aggregated['consistency_score']:.1f}/10")
            logger.info(f"{'='*70}\n")
        
        return {
            'aggregated': aggregated,
            'window_results': self.results,
            'best_params_frequency': self._analyze_param_stability()
        }
    
    def _quick_backtest(self, df_signals: pd.DataFrame) -> Dict:
        """Quick backtest for parameter optimization"""
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
                trades.append(position)
                position = None
            
            # Open new position
            if signal != 0 and position is None:
                position = {
                    'entry_price': df_signals.iloc[i]['Close'],
                    'direction': signal,
                }
        
        # Close remaining position
        if position:
            position['exit_price'] = df_signals.iloc[-1]['Close']
            position['pnl'] = (position['exit_price'] - position['entry_price']) * position['direction']
            trades.append(position)
        
        if not trades:
            return self._get_empty_metrics()
        
        df_trades = pd.DataFrame(trades)
        
        total_trades = len(df_trades)
        winning = (df_trades['pnl'] > 0).sum()
        
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        
        wins_sum = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        losses_sum = df_trades[df_trades['pnl'] <= 0]['pnl'].sum()
        
        profit_factor = (wins_sum / abs(losses_sum)) if losses_sum < 0 else (wins_sum if wins_sum > 0 else 0)
        
        # Sharpe Ratio
        pnl_array = df_trades['pnl'].values
        sharpe_ratio = np.mean(pnl_array) / np.std(pnl_array) if np.std(pnl_array) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'total_return': round(df_trades['pnl'].sum(), 2),
        }
    
    def _get_empty_metrics(self) -> Dict:
        """Return empty metrics"""
        return {
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'total_return': 0,
        }
    
    def _aggregate_metrics(self, all_metrics: List[Dict]) -> Dict:
        """Aggregate metrics across all windows"""
        if not all_metrics:
            return {}
        
        # Calculate averages
        avg_win_rate = np.mean([m.get('win_rate', 0) for m in all_metrics])
        avg_profit_factor = np.mean([m.get('profit_factor', 0) for m in all_metrics])
        avg_sharpe = np.mean([m.get('sharpe_ratio', 0) for m in all_metrics])
        total_return = sum([m.get('total_return', 0) for m in all_metrics])
        
        # Consistency score (how many windows were profitable)
        profitable_windows = sum(1 for m in all_metrics if m.get('total_return', 0) > 0)
        consistency_score = (profitable_windows / len(all_metrics)) * 10
        
        return {
            'avg_win_rate': round(avg_win_rate, 2),
            'avg_profit_factor': round(avg_profit_factor, 2),
            'avg_sharpe_ratio': round(avg_sharpe, 2),
            'total_return_pct': round(total_return, 2),
            'profitable_windows': profitable_windows,
            'total_windows': len(all_metrics),
            'consistency_score': round(consistency_score, 1),
        }
    
    def _analyze_param_stability(self) -> Dict:
        """Analyze how often each parameter value was selected"""
        if not self.best_params_per_window:
            return {}
        
        param_frequency = {}
        
        for params in self.best_params_per_window:
            for key, value in params.items():
                if key not in param_frequency:
                    param_frequency[key] = {}
                
                value_str = str(value)
                if value_str not in param_frequency[key]:
                    param_frequency[key][value_str] = 0
                
                param_frequency[key][value_str] += 1
        
        # Convert to percentages
        for key in param_frequency:
            total = sum(param_frequency[key].values())
            param_frequency[key] = {
                v: round((count / total) * 100, 1) 
                for v, count in param_frequency[key].items()
            }
        
        return param_frequency
    
    def export_results(self, filepath: str = 'reports/walk_forward_results.json'):
        """Export walk-forward results to JSON"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Convert datetime objects to strings
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'strategy': self.strategy_class.__name__,
                'training_months': self.training_months,
                'testing_months': self.testing_months,
                'optimization_metric': self.optimization_metric,
                'results': []
            }
            
            for result in self.results:
                result_copy = result.copy()
                result_copy['train_start'] = result['train_start'].isoformat()
                result_copy['train_end'] = result['train_end'].isoformat()
                result_copy['test_start'] = result['test_start'].isoformat()
                result_copy['test_end'] = result['test_end'].isoformat()
                export_data['results'].append(result_copy)
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"✓ Walk-forward results exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")


if __name__ == '__main__':
    # Test walk-forward optimizer
    print("\n🧪 Testing Walk-Forward Optimizer\n")
    
    from data_fetch_yfinance import YFinanceDataFetcher
    from ict_strategy import ICTStrategy
    
    fetcher = YFinanceDataFetcher()
    
    # Fetch 2 years of data
    print("Fetching historical data...")
    df = fetcher.fetch_historical_data('GC=F', period='2y', interval='1d')
    
    print(f"Data: {len(df)} days from {df.index[0].date()} to {df.index[-1].date()}\n")
    
    # Run walk-forward optimization
    optimizer = WalkForwardOptimizer(
        strategy_class=ICTStrategy,
        training_window_months=6,
        testing_window_months=3,
        optimization_metric='sharpe_ratio'
    )
    
    results = optimizer.run_walk_forward(df, verbose=True)
    
    # Show parameter stability
    print("\n📊 PARAMETER STABILITY (% of windows each value was selected):")
    print("="*70)
    for param, frequencies in results['best_params_frequency'].items():
        print(f"\n{param}:")
        for value, pct in sorted(frequencies.items(), key=lambda x: x[1], reverse=True):
            print(f"  {value}: {pct}%")
    
    # Export
    optimizer.export_results()
    
    print("\n✅ Walk-Forward Optimization Complete\n")
