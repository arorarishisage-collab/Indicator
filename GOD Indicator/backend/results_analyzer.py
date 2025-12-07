"""
Results analysis and reporting for backtests.
Provides comparison, export, and detailed trade analysis.
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class ResultsAnalyzer:
    """Analyze and export backtest results."""
    
    def __init__(self, output_dir: str = 'reports'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
    
    def add_result(self, strategy_name: str, result_dict: Dict) -> None:
        """Store a backtest result."""
        self.results[strategy_name] = result_dict
    
    def compare_strategies(self) -> pd.DataFrame:
        """
        Create a comparison DataFrame of all strategies.
        
        Returns:
            DataFrame with metrics for each strategy
        """
        if not self.results:
            return pd.DataFrame()
        
        rows = []
        for strategy_name, result in self.results.items():
            metrics = result.get('metrics', {})
            if isinstance(metrics, dict):
                m = metrics
            else:
                m = metrics.to_dict if hasattr(metrics, 'to_dict') else vars(metrics)
            
            row = {
                'Strategy': strategy_name,
                'Total Trades': m.get('total_trades', 0),
                'Win Rate %': m.get('win_rate', 0),
                'Total Return %': m.get('total_return', 0),
                'Sharpe Ratio': m.get('sharpe_ratio', 0),
                'Max Drawdown %': m.get('max_drawdown', 0),
                'Profit Factor': m.get('profit_factor', 0),
                'Avg Win %': m.get('average_win', 0),
                'Avg Loss %': m.get('average_loss', 0),
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def export_csv(self, filename: str = None) -> str:
        """
        Export strategy comparison to CSV.
        
        Args:
            filename: Optional custom filename
            
        Returns:
            Path to saved CSV file
        """
        if not self.results:
            raise ValueError("No results to export")
        
        df = self.compare_strategies()
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'strategy_comparison_{timestamp}.csv'
        
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def export_json(self, filename: str = None) -> str:
        """
        Export all results to JSON.
        
        Args:
            filename: Optional custom filename
            
        Returns:
            Path to saved JSON file
        """
        if not self.results:
            raise ValueError("No results to export")
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'backtest_results_{timestamp}.json'
        
        filepath = self.output_dir / filename
        
        # Convert to JSON-serializable format
        export_data = {}
        for strategy_name, result in self.results.items():
            metrics = result.get('metrics', {})
            trades = result.get('trades', [])
            
            # Ensure metrics is a dict
            if not isinstance(metrics, dict):
                if hasattr(metrics, 'to_dict'):
                    metrics = metrics.to_dict
                else:
                    metrics = vars(metrics)
            
            export_data[strategy_name] = {
                'metrics': metrics,
                'trades': trades,
                'timestamp': datetime.now().isoformat()
            }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return str(filepath)
    
    def export_trades_csv(self, strategy_name: str, filename: str = None) -> str:
        """
        Export trade details for a specific strategy to CSV.
        
        Args:
            strategy_name: Name of strategy
            filename: Optional custom filename
            
        Returns:
            Path to saved CSV file
        """
        if strategy_name not in self.results:
            raise ValueError(f"Strategy '{strategy_name}' not found")
        
        trades = self.results[strategy_name].get('trades', [])
        if not trades:
            raise ValueError(f"No trades found for strategy '{strategy_name}'")
        
        df = pd.DataFrame(trades)
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{strategy_name}_trades_{timestamp}.csv'
        
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def get_best_strategy(self, metric: str = 'total_return') -> Tuple[str, Dict]:
        """
        Get the best performing strategy by a given metric.
        
        Args:
            metric: Metric to compare (default: 'total_return')
            
        Returns:
            Tuple of (strategy_name, metrics_dict)
        """
        if not self.results:
            return None, {}
        
        best_name = None
        best_value = float('-inf')
        best_metrics = {}
        
        for strategy_name, result in self.results.items():
            metrics = result.get('metrics', {})
            if not isinstance(metrics, dict):
                if hasattr(metrics, 'to_dict'):
                    metrics = metrics.to_dict
                else:
                    metrics = vars(metrics)
            
            value = metrics.get(metric, 0)
            if value > best_value:
                best_value = value
                best_name = strategy_name
                best_metrics = metrics
        
        return best_name, best_metrics
    
    def print_summary(self) -> None:
        """Print a formatted summary of all results."""
        if not self.results:
            print("No results to summarize")
            return
        
        df = self.compare_strategies()
        
        print("\n" + "="*100)
        print("STRATEGY COMPARISON SUMMARY")
        print("="*100)
        print(df.to_string(index=False))
        print("="*100)
        
        # Best performers
        best_return, metrics = self.get_best_strategy('total_return')
        if best_return:
            print(f"\n🏆 Best Total Return: {best_return} ({metrics.get('total_return', 0):.2f}%)")
        
        best_sharpe, metrics = self.get_best_strategy('sharpe_ratio')
        if best_sharpe:
            print(f"🏆 Best Sharpe Ratio: {best_sharpe} ({metrics.get('sharpe_ratio', 0):.2f})")
        
        best_wr, metrics = self.get_best_strategy('win_rate')
        if best_wr:
            print(f"🏆 Best Win Rate: {best_wr} ({metrics.get('win_rate', 0):.1f}%)")
        
        best_dd, metrics = self.get_best_strategy('max_drawdown')
        # For drawdown, lower is better, so we want the max (least negative)
        best_dd_value = float('-inf')
        best_dd_name = None
        for strategy_name, result in self.results.items():
            m = result.get('metrics', {})
            if not isinstance(m, dict):
                m = vars(m) if hasattr(m, '__dict__') else {}
            dd = m.get('max_drawdown', 0)
            if dd > best_dd_value:
                best_dd_value = dd
                best_dd_name = strategy_name
        if best_dd_name:
            print(f"🏆 Best Max Drawdown (smallest loss): {best_dd_name} ({best_dd_value:.2f}%)")


class SignalInsights:
    """Generate insights about trading signals."""
    
    @staticmethod
    def analyze_signal_quality(df: pd.DataFrame) -> Dict:
        """
        Analyze the quality of generated signals.
        
        Args:
            df: DataFrame with 'Signal' column
            
        Returns:
            Dictionary with signal metrics
        """
        if 'Signal' not in df.columns:
            return {}
        
        signals = df['Signal']
        
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        total_signals = buy_signals + sell_signals
        
        # Calculate signal density
        signal_density = (total_signals / len(df) * 100) if len(df) > 0 else 0
        
        return {
            'total_signals': int(total_signals),
            'buy_signals': int(buy_signals),
            'sell_signals': int(sell_signals),
            'signal_density_%': round(signal_density, 2),
            'avg_bars_between_signals': int(len(df) / total_signals) if total_signals > 0 else 0,
        }
