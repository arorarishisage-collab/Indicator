"""
Simple EMA Strategy - Guaranteed to generate signals
"""

import pandas as pd
import numpy as np
from typing import Dict


class SimpleEMAStrategy:
    """
    Simple EMA crossover strategy
    Generates signals when fast EMA crosses above slow EMA
    """
    
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        """
        Initialize strategy
        
        Args:
            fast_period: Fast EMA period (default 9)
            slow_period: Slow EMA period (default 21)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with Signal column (1=buy, 0=hold, -1=sell)
        """
        if df is None or len(df) < self.slow_period:
            return pd.DataFrame()
        
        # Make a copy
        signals = df.copy()
        
        # Calculate EMAs
        signals['EMA_Fast'] = signals['Close'].ewm(span=self.fast_period, adjust=False).mean()
        signals['EMA_Slow'] = signals['Close'].ewm(span=self.slow_period, adjust=False).mean()
        
        # Generate signals: 1 when fast crosses above slow
        signals['Signal'] = 0
        
        # Crossover detection
        signals['Fast_Above_Slow'] = (signals['EMA_Fast'] > signals['EMA_Slow']).astype(int)
        signals['Prev_Fast_Above_Slow'] = signals['Fast_Above_Slow'].shift(1)
        
        # Buy signal when crossing above
        signals.loc[
            (signals['Fast_Above_Slow'] == 1) & (signals['Prev_Fast_Above_Slow'] == 0),
            'Signal'
        ] = 1
        
        # Sell signal when crossing below
        signals.loc[
            (signals['Fast_Above_Slow'] == 0) & (signals['Prev_Fast_Above_Slow'] == 1),
            'Signal'
        ] = -1
        
        # Calculate signal strength based on:
        # 1. Distance between EMAs (momentum)
        # 2. Recent price trend
        # 3. Volume confirmation
        
        ema_distance = abs(signals['EMA_Fast'] - signals['EMA_Slow']) / signals['EMA_Slow'] * 100
        
        # Recent trend (5-day return)
        signals['Return_5d'] = signals['Close'].pct_change(5) * 100
        
        # Volume trend (current vs 20-day average)
        signals['Volume_20MA'] = signals['Volume'].rolling(20).mean()
        signals['Volume_Ratio'] = signals['Volume'] / signals['Volume_20MA']
        
        # Calculate strength (0-10 scale)
        signals['Signal_Strength'] = 5.0  # Base strength
        
        # Add momentum component (up to +3 points)
        signals['Signal_Strength'] += np.clip(ema_distance, 0, 3)
        
        # Add trend component (up to +2 points)
        signals['Signal_Strength'] += np.clip(signals['Return_5d'] / 2, -2, 2)
        
        # Add volume component (up to +1 point if volume > average)
        signals['Signal_Strength'] += np.clip(signals['Volume_Ratio'] - 1, 0, 1)
        
        # Clip to 0-10 range
        signals['Signal_Strength'] = np.clip(signals['Signal_Strength'], 0, 10)
        
        # Clean up intermediate columns
        signals = signals[['Open', 'High', 'Low', 'Close', 'Volume', 
                          'EMA_Fast', 'EMA_Slow', 'Signal', 'Signal_Strength']]
        
        return signals


# For backward compatibility
class EMA30Strategy(SimpleEMAStrategy):
    """Alias for SimpleEMAStrategy with 30-period EMA"""
    def __init__(self):
        super().__init__(fast_period=9, slow_period=30)
