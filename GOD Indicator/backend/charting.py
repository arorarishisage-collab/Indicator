"""
Charting utilities for backtest visualization.
Provides simple matplotlib plots for headless and GUI use.
"""

from pathlib import Path
import matplotlib
# Use Agg for headless environments
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def plot_price_with_signals(df: pd.DataFrame, strategy_name: str = 'strategy',
                            signal_col: str = 'Signal', output_dir: str = 'reports/charts') -> str:
    """
    Plot price series with buy/sell signals and save to PNG.

    Args:
        df: DataFrame containing at least 'Close' and signal_col
        strategy_name: Name used for output file
        signal_col: Column name containing -1/0/1 signals
        output_dir: Directory where chart will be saved

    Returns:
        Path to the saved PNG file
    """
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))

    if 'Close' not in df.columns:
        raise ValueError("DataFrame must contain 'Close' column for plotting")

    ax.plot(df.index, df['Close'], label='Close', color='black', linewidth=1.0)

    # Plot buy/sell markers
    if signal_col in df.columns:
        buys = df[df[signal_col] == 1]
        sells = df[df[signal_col] == -1]

        if not buys.empty:
            ax.scatter(buys.index, buys['Close'], marker='^', color='green', s=60, label='Buy')
        if not sells.empty:
            ax.scatter(sells.index, sells['Close'], marker='v', color='red', s=60, label='Sell')

    ax.set_title(f"{strategy_name} - Price with Signals")
    ax.set_xlabel('Bar')
    ax.set_ylabel('Price')
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.4)

    out_file = p / f"{strategy_name.replace(' ', '_')}.png"
    fig.tight_layout()
    fig.savefig(out_file)
    plt.close(fig)

    return str(out_file)
