"""
Example plugin strategy that can be dropped into `backend/strategy_plugins/`.
This file demonstrates the plugin API: subclass `BaseStrategy` and implement
`validate_inputs` and `generate_signals`.
"""

from backend.base_strategy import BaseStrategy
import pandas as pd


class ExampleMeanReversionStrategy(BaseStrategy):
    def __init__(self, lookback: int = 20, threshold: float = 0.01):
        super().__init__(
            name="ExampleMeanReversion",
            description="Simple mean-reversion based on recent returns",
            parameters={'lookback': lookback, 'threshold': threshold}
        )

    def validate_inputs(self, df: pd.DataFrame) -> bool:
        return 'Close' in df.columns and len(df) >= self.parameters['lookback']

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        lb = self.parameters['lookback']
        thr = self.parameters['threshold']
        df['Ret'] = df['Close'].pct_change()
        df['MA_Ret'] = df['Ret'].rolling(lb).mean()
        df['Signal'] = 0
        df.loc[df['MA_Ret'] < -thr, 'Signal'] = 1
        df.loc[df['MA_Ret'] > thr, 'Signal'] = -1
        return df
