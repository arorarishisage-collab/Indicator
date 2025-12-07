"""
ICT (Inner Circle Trading) Strategy Implementation.
Detects supply/demand zones, order blocks, fair value gaps, and generates signals.
"""

import pandas as pd
import numpy as np
from backend.base_strategy import BaseStrategy, StrategyFactory
from backend.zone_detector import ZoneDetector
from backend.signal_generator import SignalGenerator


class ICTStrategy(BaseStrategy):
    """
    Inner Circle Trading (ICT) Strategy
    
    Detects:
    - Supply and Demand Zones
    - Order Blocks (institutional accumulation/distribution)
    - Fair Value Gaps (liquidity voids)
    - Support/Resistance Levels
    
    Generates signals when price interacts with these zones.
    """
    
    def __init__(self, 
                 zone_threshold: float = 0.015,
                 confluence_strength: int = 2,
                 use_order_blocks: bool = True,
                 use_fvg: bool = True):
        """
        Initialize ICT Strategy
        
        Args:
            zone_threshold: Percentage threshold for zone overlap (default: 1.5%)
            confluence_strength: Minimum confluences needed for signal (default: 2)
            use_order_blocks: Include order block analysis (default: True)
            use_fvg: Include fair value gap analysis (default: True)
        """
        super().__init__(
            name="ICTStrategy",
            description="Inner Circle Trading - Multi-confluence zone trading",
            parameters={
                'zone_threshold': zone_threshold,
                'confluence_strength': confluence_strength,
                'use_order_blocks': use_order_blocks,
                'use_fvg': use_fvg
            }
        )
        
        self.detector = ZoneDetector()
        self.signal_gen = SignalGenerator()
    
    def validate_inputs(self, df: pd.DataFrame) -> bool:
        """Validate required OHLCV data"""
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        return all(col in df.columns for col in required)
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on ICT principles
        
        Process:
        1. Detect swing points
        2. Identify supply/demand zones
        3. Find order blocks
        4. Detect fair value gaps
        5. Generate confluence signals
        """
        if not self.validate_inputs(df):
            raise ValueError("Missing required OHLCV columns")
        
        df = df.copy()
        
        # Step 1: Detect swings
        swing_highs, swing_lows = self.detector.detect_swings(df)
        
        # Step 2: Detect supply/demand zones
        zones = self.detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
        zones = self.detector.update_zone_mitigation(zones, df)
        
        # Step 3: Detect order blocks (institutional levels)
        obs = self.detector.detect_order_blocks(df)
        
        # Step 4: Detect fair value gaps
        fvgs = self.detector.detect_fair_value_gaps(df)
        
        # Step 5: Detect support/resistance
        srl = self.detector.detect_support_resistance(df)
        
        # Generate confluence signals
        df = self.signal_gen.generate_signals(
            df, zones, obs, fvgs, srl
        )
        
        return df


class MovingAverageCrossStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy
    
    Generates buy signal when fast MA crosses above slow MA
    Generates sell signal when fast MA crosses below slow MA
    """
    
    def __init__(self, 
                 fast_period: int = 20,
                 slow_period: int = 50,
                 confirmation_bars: int = 1):
        """
        Initialize MA Cross Strategy
        
        Args:
            fast_period: Fast moving average period
            slow_period: Slow moving average period
            confirmation_bars: Bars to confirm crossover
        """
        super().__init__(
            name="MAStrategy",
            description="Moving Average Crossover",
            parameters={
                'fast_period': fast_period,
                'slow_period': slow_period,
                'confirmation_bars': confirmation_bars
            }
        )
    
    def validate_inputs(self, df: pd.DataFrame) -> bool:
        return 'Close' in df.columns and len(df) >= self.parameters['slow_period']
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate MA crossover signals"""
        df = df.copy()
        
        fast = self.parameters['fast_period']
        slow = self.parameters['slow_period']
        confirm = self.parameters['confirmation_bars']
        
        df['MA_Fast'] = df['Close'].rolling(fast).mean()
        df['MA_Slow'] = df['Close'].rolling(slow).mean()
        
        # Crossover logic
        df['MA_Cross'] = np.where(df['MA_Fast'] > df['MA_Slow'], 1, -1)
        df['MA_Cross_Shift'] = df['MA_Cross'].shift(1)
        
        # Signal when crossing occurs
        df['Signal'] = 0
        df.loc[df['MA_Cross'] > df['MA_Cross_Shift'], 'Signal'] = 1  # Buy
        df.loc[df['MA_Cross'] < df['MA_Cross_Shift'], 'Signal'] = -1  # Sell
        
        # Confirmation filter
        if confirm > 1:
            df['Signal'] = df['Signal'].rolling(confirm, min_periods=1).max()
        
        return df


class MomentumStrategy(BaseStrategy):
    """
    Momentum-based strategy using RSI and Rate of Change
    
    Generates signals based on momentum extremes
    """
    
    def __init__(self,
                 rsi_period: int = 14,
                 rsi_overbought: float = 70.0,
                 rsi_oversold: float = 30.0,
                 roc_period: int = 12):
        """
        Initialize Momentum Strategy
        
        Args:
            rsi_period: RSI calculation period
            rsi_overbought: Overbought threshold (0-100)
            rsi_oversold: Oversold threshold (0-100)
            roc_period: Rate of Change period
        """
        super().__init__(
            name="MomentumStrategy",
            description="Momentum-based strategy (RSI + ROC)",
            parameters={
                'rsi_period': rsi_period,
                'rsi_overbought': rsi_overbought,
                'rsi_oversold': rsi_oversold,
                'roc_period': roc_period
            }
        )
    
    def validate_inputs(self, df: pd.DataFrame) -> bool:
        return 'Close' in df.columns and len(df) >= self.parameters['rsi_period']
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gains = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        losses = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum signals"""
        df = df.copy()
        
        period = self.parameters['rsi_period']
        overbought = self.parameters['rsi_overbought']
        oversold = self.parameters['rsi_oversold']
        
        # Calculate RSI
        df['RSI'] = self._calculate_rsi(df['Close'], period)
        
        # Calculate ROC
        df['ROC'] = df['Close'].pct_change(self.parameters['roc_period']) * 100
        
        # Generate signals
        df['Signal'] = 0
        
        # Buy signals: RSI oversold or positive momentum
        buy_signal = (df['RSI'] < oversold) | (df['ROC'] > 0)
        df.loc[buy_signal, 'Signal'] = 1
        
        # Sell signals: RSI overbought or negative momentum
        sell_signal = (df['RSI'] > overbought) | (df['ROC'] < 0)
        df.loc[sell_signal, 'Signal'] = -1
        
        return df


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Volatility Breakout Strategy
    
    Generates signals when price breaks average true range bands
    """
    
    def __init__(self,
                 atr_period: int = 14,
                 atr_multiplier: float = 2.0):
        """
        Initialize Volatility Breakout Strategy
        
        Args:
            atr_period: Average True Range period
            atr_multiplier: ATR multiplier for bands
        """
        super().__init__(
            name="VolatilityBreakout",
            description="Volatility Breakout based on ATR",
            parameters={
                'atr_period': atr_period,
                'atr_multiplier': atr_multiplier
            }
        )
    
    def validate_inputs(self, df: pd.DataFrame) -> bool:
        return all(col in df.columns for col in ['High', 'Low', 'Close'])
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate volatility breakout signals"""
        df = df.copy()
        
        period = self.parameters['atr_period']
        mult = self.parameters['atr_multiplier']
        
        # Calculate ATR
        df['ATR'] = self._calculate_atr(df, period)
        
        # Calculate bands
        df['Upper_Band'] = df['Close'].rolling(period).mean() + (df['ATR'] * mult)
        df['Lower_Band'] = df['Close'].rolling(period).mean() - (df['ATR'] * mult)
        
        # Generate signals
        df['Signal'] = 0
        df.loc[df['Close'] > df['Upper_Band'], 'Signal'] = 1  # Upside breakout
        df.loc[df['Close'] < df['Lower_Band'], 'Signal'] = -1  # Downside breakout
        
        return df


# Register all strategies
StrategyFactory.register(ICTStrategy)
StrategyFactory.register(MovingAverageCrossStrategy)
StrategyFactory.register(MomentumStrategy)
StrategyFactory.register(VolatilityBreakoutStrategy)
