"""
Chart visualization module for backtesting results and price analysis.
Supports candlestick charts with overlays and trade markers.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json


class ChartGenerator:
    """Generate trading charts using Plotly for interactive visualization"""
    
    @staticmethod
    def create_candlestick_chart(df: pd.DataFrame,
                                title: str = "Gold Price Chart",
                                height: int = 600,
                                show_volume: bool = True) -> str:
        """
        Create interactive candlestick chart
        
        Args:
            df: OHLCV DataFrame with required columns
            title: Chart title
            height: Chart height in pixels
            show_volume: Show volume subplot
            
        Returns:
            HTML string for chart
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            return ChartGenerator._get_fallback_chart("Candlestick Chart", 
                                                      "Install plotly: pip install plotly")
        
        if df.empty:
            return "<p>No data available for chart</p>"
        
        # Create subplots if volume is shown
        if show_volume:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                row_heights=[0.7, 0.3],
                vertical_spacing=0.1
            )
        else:
            fig = go.Figure()
        
        # Add candlestick
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='Gold Price',
                row=1, col=1 if show_volume else None
            )
        )
        
        # Add volume if available
        if show_volume and 'Volume' in df.columns:
            colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green' 
                     for i in range(len(df))]
            
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['Volume'],
                    name='Volume',
                    marker_color=colors,
                    showlegend=False,
                    row=2, col=1
                )
            )
            
            fig.update_yaxes(title_text="Volume", row=2, col=1)
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            height=height,
            hovermode='x unified',
            template='plotly_dark'
        )
        
        return fig.to_html(include_plotlyjs='cdn')
    
    @staticmethod
    def add_indicators_to_chart(html_chart: str,
                               indicators: Dict[str, pd.Series]) -> str:
        """
        Add technical indicators to existing chart
        
        Args:
            html_chart: Existing chart HTML
            indicators: Dict of indicator name -> Series
            
        Returns:
            Updated HTML chart
        """
        # Note: For full implementation, would need to parse and update plotly figure
        return html_chart
    
    @staticmethod
    def create_trade_chart(df: pd.DataFrame,
                          trades: List[Dict],
                          title: str = "Backtest Results with Trades",
                          height: int = 600) -> str:
        """
        Create candlestick chart with trade markers
        
        Args:
            df: OHLCV DataFrame
            trades: List of trade dicts with entry/exit prices and indices
            title: Chart title
            height: Chart height
            
        Returns:
            HTML string for chart
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            return ChartGenerator._get_fallback_chart("Trade Chart",
                                                      "Install plotly: pip install plotly")
        
        fig = go.Figure()
        
        # Add candlestick
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='Price'
            )
        )
        
        # Add trade markers
        entry_indices = [t['entry_index'] for t in trades]
        exit_indices = [t['exit_index'] for t in trades]
        entry_prices = [t['entry_price'] for t in trades]
        exit_prices = [t['exit_price'] for t in trades]
        pnls = [t['pnl'] for t in trades]
        
        # Entry markers (green for long, red for short)
        entry_colors = ['green' if t['direction'] == 1 else 'red' for t in trades]
        
        fig.add_trace(
            go.Scatter(
                x=[df.index[i] for i in entry_indices],
                y=entry_prices,
                mode='markers',
                name='Entry',
                marker=dict(size=8, color=entry_colors, symbol='triangle-up'),
                text=[f"Entry: ${p:.2f}" for p in entry_prices],
                hoverinfo='text'
            )
        )
        
        # Exit markers
        exit_colors = ['green' if pnl > 0 else 'red' for pnl in pnls]
        
        fig.add_trace(
            go.Scatter(
                x=[df.index[i] for i in exit_indices],
                y=exit_prices,
                mode='markers',
                name='Exit',
                marker=dict(size=8, color=exit_colors, symbol='triangle-down'),
                text=[f"Exit: ${p:.2f}<br>P&L: ${pnl:.2f}" 
                     for p, pnl in zip(exit_prices, pnls)],
                hoverinfo='text'
            )
        )
        
        # Trade lines
        for trade in trades:
            entry_idx = trade['entry_index']
            exit_idx = trade['exit_index']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            pnl = trade['pnl']
            
            line_color = 'green' if pnl > 0 else 'red'
            
            fig.add_trace(
                go.Scatter(
                    x=[df.index[entry_idx], df.index[exit_idx]],
                    y=[entry_price, exit_price],
                    mode='lines',
                    line=dict(color=line_color, width=1, dash='dash'),
                    name='Trade',
                    showlegend=False,
                    hoverinfo='skip'
                )
            )
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            height=height,
            hovermode='x unified',
            template='plotly_dark'
        )
        
        return fig.to_html(include_plotlyjs='cdn')
    
    @staticmethod
    def create_equity_curve(equity_curve: List[float],
                           drawdown_curve: List[float],
                           title: str = "Equity & Drawdown",
                           height: int = 500) -> str:
        """
        Create equity curve with drawdown
        
        Args:
            equity_curve: List of equity values
            drawdown_curve: List of drawdown percentages
            title: Chart title
            height: Chart height
            
        Returns:
            HTML string for chart
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError:
            return ChartGenerator._get_fallback_chart("Equity Curve",
                                                      "Install plotly: pip install plotly")
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.1,
            subplot_titles=("Equity Curve", "Drawdown")
        )
        
        x_axis = list(range(len(equity_curve)))
        
        # Equity curve
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=equity_curve,
                name='Equity',
                line=dict(color='#00CC96', width=2),
                fill='tozeroy',
                row=1, col=1
            )
        )
        
        # Drawdown
        colors = ['red' if dd < 0 else 'gray' for dd in drawdown_curve]
        
        fig.add_trace(
            go.Bar(
                x=x_axis,
                y=drawdown_curve,
                name='Drawdown %',
                marker_color=colors,
                showlegend=False,
                row=2, col=1
            )
        )
        
        fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
        fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
        fig.update_xaxes(title_text="Bars", row=2, col=1)
        
        fig.update_layout(
            title=title,
            height=height,
            template='plotly_dark'
        )
        
        return fig.to_html(include_plotlyjs='cdn')
    
    @staticmethod
    def create_performance_table(metrics: Dict) -> str:
        """
        Create HTML performance metrics table
        
        Args:
            metrics: Dict of metric names and values
            
        Returns:
            HTML string for table
        """
        html = """
        <table style="border-collapse: collapse; width: 100%; font-family: monospace;">
            <tr style="background-color: #2d2d2d;">
                <th style="border: 1px solid #555; padding: 8px; text-align: left;">Metric</th>
                <th style="border: 1px solid #555; padding: 8px; text-align: right;">Value</th>
            </tr>
        """
        
        for key, value in metrics.items():
            if isinstance(value, float):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            
            html += f"""
            <tr style="background-color: #1e1e1e;">
                <td style="border: 1px solid #555; padding: 8px;">{key.replace('_', ' ').title()}</td>
                <td style="border: 1px solid #555; padding: 8px; text-align: right;">{formatted_value}</td>
            </tr>
            """
        
        html += "</table>"
        return html
    
    @staticmethod
    def _get_fallback_chart(title: str, message: str) -> str:
        """Get fallback chart when plotly not available"""
        return f"""
        <div style="padding: 20px; background-color: #1e1e1e; color: #fff; border-radius: 5px;">
            <h3>{title}</h3>
            <p>{message}</p>
            <p style="color: #888; font-size: 12px;">Install with: pip install plotly</p>
        </div>
        """


class StaticChartGenerator:
    """Fallback chart generator using ASCII or simple visualization"""
    
    @staticmethod
    def create_ascii_chart(values: List[float], width: int = 60, height: int = 15) -> str:
        """Create ASCII chart from values"""
        if not values:
            return "No data available"
        
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val if max_val != min_val else 1
        
        chart = []
        for h in range(height, -1, -1):
            line = ""
            for w in range(len(values)):
                normalized = (values[w] - min_val) / range_val * height
                if normalized >= h:
                    line += "█"
                else:
                    line += " "
            chart.append(line)
        
        return "\n".join(chart)
