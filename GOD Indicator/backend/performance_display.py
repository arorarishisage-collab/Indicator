"""
Performance metrics display and trade insights generator.
"""

from typing import Dict, List
import pandas as pd


class PerformanceDisplay:
    """Format and display backtest performance metrics."""
    
    @staticmethod
    def format_metrics(metrics: Dict) -> str:
        """Format metrics for console display."""
        if not isinstance(metrics, dict):
            metrics = vars(metrics) if hasattr(metrics, '__dict__') else {}
        
        output = []
        output.append("📊 PERFORMANCE METRICS")
        output.append("─" * 50)
        
        # Trade stats
        output.append(f"Trades:")
        output.append(f"  Total:              {int(metrics.get('total_trades', 0))}")
        output.append(f"  Wins:               {int(metrics.get('winning_trades', 0))}")
        output.append(f"  Losses:             {int(metrics.get('losing_trades', 0))}")
        output.append(f"  Win Rate:           {metrics.get('win_rate', 0):.1f}%")
        
        output.append(f"\nProfitability:")
        output.append(f"  Total P&L:          ${metrics.get('total_pnl', 0):.2f}")
        output.append(f"  Gross Profit:       ${metrics.get('gross_profit', 0):.2f}")
        output.append(f"  Gross Loss:         ${metrics.get('gross_loss', 0):.2f}")
        output.append(f"  Profit Factor:      {metrics.get('profit_factor', 0):.2f}x")
        
        output.append(f"\nAverages:")
        output.append(f"  Avg Win:            ${metrics.get('average_win', 0):.2f}")
        output.append(f"  Avg Loss:           ${metrics.get('average_loss', 0):.2f}")
        output.append(f"  Risk/Reward Ratio:  {metrics.get('risk_reward_ratio', 0):.2f}")
        output.append(f"  Expectancy:         ${metrics.get('expectancy', 0):.2f}")
        
        output.append(f"\nReturn Metrics:")
        output.append(f"  Total Return:       {metrics.get('total_return', 0):.2f}%")
        output.append(f"  Annualized Return:  {metrics.get('annualized_return', 0):.2f}%")
        output.append(f"  Monthly Return:     {metrics.get('monthly_return', 0):.2f}%")
        
        output.append(f"\nRisk Metrics:")
        output.append(f"  Max Drawdown:       {metrics.get('max_drawdown', 0):.2f}%")
        output.append(f"  Sharpe Ratio:       {metrics.get('sharpe_ratio', 0):.2f}")
        output.append(f"  Sortino Ratio:      {metrics.get('sortino_ratio', 0):.2f}")
        output.append(f"  Calmar Ratio:       {metrics.get('calmar_ratio', 0):.2f}")
        output.append(f"  Ulcer Index:        {metrics.get('ulcer_index', 0):.2f}")
        output.append(f"  Recovery Factor:    {metrics.get('recovery_factor', 0):.2f}")
        
        output.append("─" * 50)
        
        return "\n".join(output)
    
    @staticmethod
    def format_trade_summary(trades: List[Dict]) -> str:
        """Format trade summary for display."""
        if not trades:
            return "No trades executed"
        
        df = pd.DataFrame(trades)
        
        winning = df[df['pnl'] > 0]
        losing = df[df['pnl'] <= 0]
        
        output = []
        output.append("📋 TRADE SUMMARY")
        output.append("─" * 50)
        
        output.append(f"Total Trades:       {len(df)}")
        output.append(f"Winning Trades:     {len(winning)} ({len(winning)/len(df)*100:.1f}%)")
        output.append(f"Losing Trades:      {len(losing)} ({len(losing)/len(df)*100:.1f}%)")
        
        if len(winning) > 0:
            output.append(f"\nWinning Trade Stats:")
            output.append(f"  Best Trade:       ${winning['pnl'].max():.2f}")
            output.append(f"  Avg Win:          ${winning['pnl'].mean():.2f}")
            output.append(f"  Total Profits:    ${winning['pnl'].sum():.2f}")
        
        if len(losing) > 0:
            output.append(f"\nLosing Trade Stats:")
            output.append(f"  Worst Trade:      ${losing['pnl'].min():.2f}")
            output.append(f"  Avg Loss:         ${losing['pnl'].mean():.2f}")
            output.append(f"  Total Losses:     ${losing['pnl'].sum():.2f}")
        
        output.append(f"\nTrade Duration:")
        output.append(f"  Avg Bars Held:     {df['bars_held'].mean():.1f}")
        output.append(f"  Min/Max:           {df['bars_held'].min()}/{df['bars_held'].max()}")
        
        output.append("─" * 50)
        
        return "\n".join(output)
    
    @staticmethod
    def get_trade_insights(trades: List[Dict]) -> str:
        """Generate actionable insights from trades."""
        if not trades:
            return "No trades to analyze"
        
        df = pd.DataFrame(trades)
        
        insights = []
        insights.append("💡 TRADE INSIGHTS")
        insights.append("─" * 50)
        
        # Best trade
        best_idx = df['pnl'].idxmax()
        best_trade = df.loc[best_idx]
        insights.append(f"\n🏆 Best Trade:")
        insights.append(f"  Entry Price: ${best_trade['entry_price']:.2f}")
        insights.append(f"  Exit Price:  ${best_trade['exit_price']:.2f}")
        insights.append(f"  P&L:         ${best_trade['pnl']:.2f} ({best_trade['pnl_percent']:.2f}%)")
        insights.append(f"  Duration:    {int(best_trade['bars_held'])} bars")
        
        # Worst trade
        worst_idx = df['pnl'].idxmin()
        worst_trade = df.loc[worst_idx]
        insights.append(f"\n❌ Worst Trade:")
        insights.append(f"  Entry Price: ${worst_trade['entry_price']:.2f}")
        insights.append(f"  Exit Price:  ${worst_trade['exit_price']:.2f}")
        insights.append(f"  P&L:         ${worst_trade['pnl']:.2f} ({worst_trade['pnl_percent']:.2f}%)")
        insights.append(f"  Duration:    {int(worst_trade['bars_held'])} bars")
        
        # Consecutive analysis
        winning = df[df['pnl'] > 0]
        max_consecutive = 0
        current = 0
        for _, row in df.iterrows():
            if row['pnl'] > 0:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 0
        
        insights.append(f"\n📈 Win Streaks:")
        insights.append(f"  Max Consecutive Wins: {max_consecutive}")
        
        # Loss streaks
        losing = df[df['pnl'] <= 0]
        max_loss_streak = 0
        current = 0
        for _, row in df.iterrows():
            if row['pnl'] <= 0:
                current += 1
                max_loss_streak = max(max_loss_streak, current)
            else:
                current = 0
        
        insights.append(f"  Max Consecutive Losses: {max_loss_streak}")
        
        # Recovery potential
        largest_loss = df['pnl'].min()
        total_wins = df[df['pnl'] > 0]['pnl'].sum()
        if largest_loss < 0:
            trades_to_recover = abs(largest_loss) / (total_wins / len(winning)) if len(winning) > 0 else 0
            insights.append(f"\n🔄 Recovery Analysis:")
            insights.append(f"  Largest Loss: ${largest_loss:.2f}")
            insights.append(f"  Approx. Trades to Recover: {trades_to_recover:.1f}")
        
        insights.append("─" * 50)
        
        return "\n".join(insights)
