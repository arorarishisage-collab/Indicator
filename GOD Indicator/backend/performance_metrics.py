"""
Performance Metrics - Comprehensive analytics and reporting
Industry-standard metrics for strategy evaluation and optimization
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Comprehensive performance analysis and reporting
    Calculates 20+ metrics for thorough strategy evaluation
    """
    
    def __init__(self, initial_capital: float = 100000):
        """Initialize analyzer"""
        self.initial_capital = initial_capital
    
    def analyze(self, result) -> Dict:
        """
        Generate comprehensive performance report
        
        Args:
            result: BacktestResult from ProfessionalBacktester
        
        Returns:
            Dictionary with all metrics
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'initial_capital': result.initial_capital,
            'final_capital': result.final_capital,
            'profitability': self._analyze_profitability(result),
            'risk': self._analyze_risk(result),
            'efficiency': self._analyze_efficiency(result),
            'consistency': self._analyze_consistency(result),
            'volatility': self._analyze_volatility(result),
        }
        
        return metrics
    
    def _analyze_profitability(self, result) -> Dict:
        """Profitability metrics"""
        
        if not result.trades:
            return {}
        
        total_profit = sum([t.pnl for t in result.trades if t.pnl > 0])
        total_loss = abs(sum([t.pnl for t in result.trades if t.pnl < 0]))
        
        return {
            'total_return_percent': result.total_return_percent,
            'total_return_amount': result.total_return,
            'monthly_return_percent': (result.total_return_percent / 12) if len(result.trades) > 0 else 0,
            'gross_profit': total_profit,
            'gross_loss': total_loss,
            'profit_factor': result.profit_factor,
            'best_trade': result.best_trade,
            'worst_trade': result.worst_trade,
            'avg_trade': result.avg_trade,
        }
    
    def _analyze_risk(self, result) -> Dict:
        """Risk metrics"""
        
        return {
            'max_drawdown_percent': result.max_drawdown_percent,
            'max_drawdown_amount': result.max_drawdown,
            'recovery_factor': result.recovery_factor,
            'sharpe_ratio': result.sharpe_ratio,
            'sortino_ratio': result.sortino_ratio,
            'calmar_ratio': result.calmar_ratio,
        }
    
    def _analyze_efficiency(self, result) -> Dict:
        """Trading efficiency metrics"""
        
        if not result.trades:
            return {}
        
        trades_per_year = len(result.trades) * 252 / len(result.equity_curve) if result.equity_curve else 0
        return_per_trade = result.total_return / len(result.trades) if result.trades else 0
        
        return {
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate_percent': result.win_rate,
            'trades_per_year': trades_per_year,
            'return_per_trade': return_per_trade,
        }
    
    def _analyze_consistency(self, result) -> Dict:
        """Consistency and stability metrics"""
        
        if not result.trades:
            return {}
        
        pnl_values = [t.pnl for t in result.trades]
        pnl_percent = [t.pnl_percent for t in result.trades]
        
        consecutive_wins = self._max_consecutive(result.trades, lambda t: t.pnl > 0)
        consecutive_losses = self._max_consecutive(result.trades, lambda t: t.pnl <= 0)
        
        return {
            'std_dev_trade_pnl': np.std(pnl_values),
            'std_dev_trade_pnl_percent': np.std(pnl_percent),
            'max_consecutive_wins': consecutive_wins,
            'max_consecutive_losses': consecutive_losses,
            'avg_win_pnl': np.mean([t.pnl for t in result.trades if t.pnl > 0]) if result.winning_trades > 0 else 0,
            'avg_loss_pnl': np.mean([t.pnl for t in result.trades if t.pnl < 0]) if result.losing_trades > 0 else 0,
            'payoff_ratio': (np.mean([t.pnl for t in result.trades if t.pnl > 0]) / 
                           abs(np.mean([t.pnl for t in result.trades if t.pnl < 0]))) 
                           if result.losing_trades > 0 and result.winning_trades > 0 else 0,
        }
    
    def _analyze_volatility(self, result) -> Dict:
        """Volatility metrics"""
        
        if len(result.equity_curve) < 2:
            return {}
        
        returns = np.diff(result.equity_curve) / np.array(result.equity_curve[:-1])
        
        if len(returns) == 0:
            return {}
        
        return {
            'volatility_daily': np.std(returns),
            'volatility_annual': np.std(returns) * np.sqrt(252),
            'return_volatility_ratio': (np.mean(returns) / np.std(returns)) if np.std(returns) > 0 else 0,
        }
    
    @staticmethod
    def _max_consecutive(trades: List, condition) -> int:
        """Calculate max consecutive trades meeting condition"""
        max_count = 0
        current_count = 0
        
        for trade in trades:
            if condition(trade):
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count
    
    def generate_report(self, result, filename: str = None) -> str:
        """
        Generate comprehensive performance report
        
        Args:
            result: BacktestResult
            filename: Optional filename to save report
        
        Returns:
            Formatted report string
        """
        metrics = self.analyze(result)
        
        report = self._format_report(metrics)
        
        if filename:
            with open(filename, 'w') as f:
                f.write(report)
            logger.info(f"✓ Report saved to {filename}")
        
        return report
    
    def _format_report(self, metrics: Dict) -> str:
        """Format metrics as readable report"""
        
        lines = [
            "=" * 70,
            "PERFORMANCE ANALYSIS REPORT",
            "=" * 70,
            f"Generated: {metrics['timestamp']}",
            "",
            "CAPITAL",
            "-" * 70,
            f"  Initial Capital:                    ₹{metrics['initial_capital']:,.2f}",
            f"  Final Capital:                      ₹{metrics['final_capital']:,.2f}",
            "",
            "PROFITABILITY",
            "-" * 70,
        ]
        
        prof = metrics['profitability']
        lines.extend([
            f"  Total Return:                       {prof['total_return_percent']:>7.2f}% (₹{prof['total_return_amount']:,.2f})",
            f"  Monthly Return (Avg):               {prof['monthly_return_percent']:>7.2f}%",
            f"  Gross Profit:                       ₹{prof['gross_profit']:,.2f}",
            f"  Gross Loss:                         ₹{prof['gross_loss']:,.2f}",
            f"  Profit Factor:                      {prof['profit_factor']:>7.2f}",
            f"  Best Trade:                         ₹{prof['best_trade']:,.2f}",
            f"  Worst Trade:                        ₹{prof['worst_trade']:,.2f}",
            f"  Avg Trade:                          ₹{prof['avg_trade']:,.2f}",
            "",
            "EFFICIENCY",
            "-" * 70,
        ])
        
        eff = metrics['efficiency']
        lines.extend([
            f"  Total Trades:                       {eff['total_trades']:>7.0f}",
            f"  Winning Trades:                     {eff['winning_trades']:>7.0f}",
            f"  Losing Trades:                      {eff['losing_trades']:>7.0f}",
            f"  Win Rate:                           {eff['win_rate_percent']:>7.2f}%",
            f"  Trades Per Year:                    {eff['trades_per_year']:>7.2f}",
            f"  Return Per Trade:                   ₹{eff['return_per_trade']:>7,.2f}",
            "",
            "CONSISTENCY",
            "-" * 70,
        ])
        
        cons = metrics['consistency']
        lines.extend([
            f"  Std Dev Trade PnL:                  ₹{cons['std_dev_trade_pnl']:,.2f}",
            f"  Std Dev Trade PnL %:                {cons['std_dev_trade_pnl_percent']:>7.2f}%",
            f"  Max Consecutive Wins:               {cons['max_consecutive_wins']:>7.0f}",
            f"  Max Consecutive Losses:             {cons['max_consecutive_losses']:>7.0f}",
            f"  Avg Winning Trade:                  ₹{cons['avg_win_pnl']:,.2f}",
            f"  Avg Losing Trade:                   ₹{cons['avg_loss_pnl']:,.2f}",
            f"  Payoff Ratio:                       {cons['payoff_ratio']:>7.2f}",
            "",
            "RISK METRICS",
            "-" * 70,
        ])
        
        risk = metrics['risk']
        lines.extend([
            f"  Max Drawdown:                       {risk['max_drawdown_percent']:>7.2f}% (₹{risk['max_drawdown_amount']:,.2f})",
            f"  Recovery Factor:                    {risk['recovery_factor']:>7.2f}",
            f"  Sharpe Ratio:                       {risk['sharpe_ratio']:>7.2f}",
            f"  Sortino Ratio:                      {risk['sortino_ratio']:>7.2f}",
            f"  Calmar Ratio:                       {risk['calmar_ratio']:>7.2f}",
            "",
            "VOLATILITY",
            "-" * 70,
        ])
        
        vol = metrics['volatility']
        lines.extend([
            f"  Daily Volatility:                   {vol['volatility_daily']:>7.4f}",
            f"  Annual Volatility:                  {vol['volatility_annual']:>7.4f}",
            f"  Return/Volatility Ratio:            {vol['return_volatility_ratio']:>7.2f}",
            "",
            "=" * 70,
        ])
        
        return "\n".join(lines)
    
    def export_to_csv(self, result, filename: str) -> bool:
        """Export trades to CSV"""
        try:
            trades_df = result.get_trades_dataframe()
            trades_df.to_csv(filename, index=False)
            logger.info(f"✓ Trades exported to {filename}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def export_to_json(self, result, filename: str) -> bool:
        """Export results to JSON"""
        try:
            import json
            metrics = self.analyze(result)
            with open(filename, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            logger.info(f"✓ Metrics exported to {filename}")
            return True
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False


class StrategyComparator:
    """Compare multiple strategy backtests"""
    
    @staticmethod
    def compare(results: Dict[str, Dict]) -> pd.DataFrame:
        """
        Compare multiple backtest results
        
        Args:
            results: Dict mapping strategy name to metrics dict
        
        Returns:
            DataFrame with comparison
        """
        comparison_data = []
        
        for strategy_name, metrics in results.items():
            prof = metrics.get('profitability', {})
            eff = metrics.get('efficiency', {})
            risk = metrics.get('risk', {})
            
            comparison_data.append({
                'Strategy': strategy_name,
                'Total Return %': prof.get('total_return_percent', 0),
                'Win Rate %': eff.get('win_rate_percent', 0),
                'Profit Factor': prof.get('profit_factor', 0),
                'Sharpe Ratio': risk.get('sharpe_ratio', 0),
                'Max Drawdown %': risk.get('max_drawdown_percent', 0),
                'Trades': eff.get('total_trades', 0),
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        return comparison_df.sort_values('Total Return %', ascending=False)
    
    @staticmethod
    def rank_strategies(results: Dict[str, Dict], weights: Dict[str, float] = None) -> pd.DataFrame:
        """
        Rank strategies using weighted scoring
        
        Args:
            results: Dict mapping strategy name to metrics dict
            weights: Dict of metric weights (default: equal weight)
        
        Returns:
            DataFrame with rankings
        """
        default_weights = {
            'return': 0.3,
            'win_rate': 0.2,
            'profit_factor': 0.2,
            'sharpe': 0.15,
            'max_dd': 0.15,
        }
        
        weights = weights or default_weights
        
        ranked = []
        for strategy_name, metrics in results.items():
            prof = metrics.get('profitability', {})
            eff = metrics.get('efficiency', {})
            risk = metrics.get('risk', {})
            
            # Normalize scores (0-100)
            return_score = min(100, max(0, (prof.get('total_return_percent', 0) + 100) * 0.5))
            win_rate_score = eff.get('win_rate_percent', 0)
            pf_score = min(100, prof.get('profit_factor', 0) * 10)
            sharpe_score = min(100, max(0, (risk.get('sharpe_ratio', 0) + 3) * 10))
            dd_score = max(0, 100 + risk.get('max_drawdown_percent', 0))
            
            # Calculate weighted score
            overall_score = (
                return_score * weights.get('return', 0.3) +
                win_rate_score * weights.get('win_rate', 0.2) +
                pf_score * weights.get('profit_factor', 0.2) +
                sharpe_score * weights.get('sharpe', 0.15) +
                dd_score * weights.get('max_dd', 0.15)
            )
            
            ranked.append({
                'Strategy': strategy_name,
                'Overall Score': overall_score,
                'Return %': prof.get('total_return_percent', 0),
                'Win Rate %': eff.get('win_rate_percent', 0),
                'Profit Factor': prof.get('profit_factor', 0),
                'Sharpe Ratio': risk.get('sharpe_ratio', 0),
                'Max Drawdown %': risk.get('max_drawdown_percent', 0),
            })
        
        ranked_df = pd.DataFrame(ranked)
        return ranked_df.sort_values('Overall Score', ascending=False)
