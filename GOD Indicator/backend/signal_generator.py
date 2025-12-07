"""
Signal Generator Module for ICT Trading Strategy
Generates buy/sell signals based on supply/demand zones, S/R, OBs, and FVGs.
"""

import pandas as pd
import numpy as np
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalType(Enum):
    BUY = 1
    SELL = -1
    NONE = 0


@dataclass
class TradeSignal:
    """Represents a trading signal with entry, stop loss, and take profit."""
    signal_type: SignalType
    candle_index: int  # Index in DataFrame where signal triggered
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str  # Reason for signal (for logging)
    
    def risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio."""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        if risk == 0:
            return 0
        return reward / risk


class SignalGenerator:
    """Generates trading signals based on ICT strategy rules."""
    
    def __init__(
        self,
        min_risk_reward: float = 1.5,
        ema_fast: int = 30,
        ema_slow: int = 200,
        atr_period: int = 14,
        atr_multiplier_sl: float = 2.0,
        atr_multiplier_tp: float = 3.0
    ):
        """
        Initialize SignalGenerator.
        
        Args:
            min_risk_reward: Minimum risk/reward ratio to accept (default: 1.5)
            ema_fast: Fast EMA period (default: 30)
            ema_slow: Slow EMA period (default: 200)
            atr_period: ATR period (default: 14)
            atr_multiplier_sl: ATR multiplier for stop loss (default: 2.0)
            atr_multiplier_tp: ATR multiplier for take profit (default: 3.0)
        """
        self.min_risk_reward = min_risk_reward
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.atr_period = atr_period
        self.atr_multiplier_sl = atr_multiplier_sl
        self.atr_multiplier_tp = atr_multiplier_tp
    
    def check_trend(self, df: pd.DataFrame, index: int, direction: str = 'up') -> bool:
        """
        Check if multi-timeframe trend aligns.
        
        Args:
            df: OHLCV DataFrame
            index: Current candle index
            direction: 'up' or 'down'
        
        Returns:
            True if trend aligns, False otherwise
        """
        if 'EMA_200' not in df.columns:
            logger.warning("EMA_200 not found. Skipping trend check.")
            return True
        
        current_price = df['Close'].iloc[index]
        ema_200 = df['EMA_200'].iloc[index]
        
        if pd.isna(ema_200):
            return False
        
        if direction == 'up':
            return current_price > ema_200
        else:
            return current_price < ema_200
    
    def check_price_in_zone(
        self,
        df: pd.DataFrame,
        index: int,
        zones: List,
        zone_type: str = 'demand'
    ) -> bool:
        """
        Check if price is touching a supply/demand zone.
        
        Args:
            df: OHLCV DataFrame
            index: Current candle index
            zones: List of Zone objects
            zone_type: 'demand' or 'supply'
        
        Returns:
            True if price is in zone
        """
        current_low = df['Low'].iloc[index]
        current_high = df['High'].iloc[index]
        
        target_zones = [z for z in zones if z.zone_type == zone_type and not z.mitigated]
        
        for zone in target_zones:
            # Check if candle touches zone
            if zone_type == 'demand':
                if current_low <= zone.top and current_low >= zone.bottom:
                    return True
            else:  # supply
                if current_high >= zone.bottom and current_high <= zone.top:
                    return True
        
        return False
    
    def check_support_rejection(
        self,
        df: pd.DataFrame,
        index: int,
        support_levels: List[float],
        threshold: float = 5.0
    ) -> bool:
        """
        Check if price rejects off support level.
        
        Args:
            df: OHLCV DataFrame
            index: Current candle index
            support_levels: List of support price levels
            threshold: Price proximity threshold
        
        Returns:
            True if rejection detected
        """
        if index < 2:
            return False
        
        current_low = df['Low'].iloc[index]
        current_close = df['Close'].iloc[index]
        prev_close = df['Close'].iloc[index - 1]
        
        for support in support_levels:
            # Check if price touched support and closed above it
            if abs(current_low - support) < threshold:
                if current_close > support:
                    # Check for bounce pattern
                    if current_close > prev_close:
                        return True
        
        return False
    
    def check_resistance_rejection(
        self,
        df: pd.DataFrame,
        index: int,
        resistance_levels: List[float],
        threshold: float = 5.0
    ) -> bool:
        """
        Check if price rejects off resistance level.
        
        Args:
            df: OHLCV DataFrame
            index: Current candle index
            resistance_levels: List of resistance price levels
            threshold: Price proximity threshold
        
        Returns:
            True if rejection detected
        """
        if index < 2:
            return False
        
        current_high = df['High'].iloc[index]
        current_close = df['Close'].iloc[index]
        prev_close = df['Close'].iloc[index - 1]
        
        for resistance in resistance_levels:
            # Check if price touched resistance and closed below it
            if abs(current_high - resistance) < threshold:
                if current_close < resistance:
                    # Check for rejection pattern
                    if current_close < prev_close:
                        return True
        
        return False
    
    def check_order_block_alignment(
        self,
        df: pd.DataFrame,
        index: int,
        order_blocks: List,
        ob_type: str = 'bullish',
        threshold: float = 10.0
    ) -> bool:
        """
        Check if price is near aligned order block.
        
        Args:
            df: OHLCV DataFrame
            index: Current candle index
            order_blocks: List of OrderBlock objects
            ob_type: 'bullish' or 'bearish'
            threshold: Price proximity threshold
        
        Returns:
            True if price near OB
        """
        current_price = df['Close'].iloc[index]
        
        target_obs = [ob for ob in order_blocks if ob.ob_type == ob_type]
        
        for ob in target_obs:
            if ob_type == 'bullish':
                # For bullish OB, check if price is near lower bound
                if abs(current_price - ob.low) < threshold:
                    return True
            else:  # bearish
                # For bearish OB, check if price is near upper bound
                if abs(current_price - ob.high) < threshold:
                    return True
        
        return False
    
    def check_fvg_alignment(
        self,
        df: pd.DataFrame,
        index: int,
        fvgs: List,
        fvg_type: str = 'bullish',
        retrace_threshold: float = 0.6
    ) -> bool:
        """
        Check if price retraces to FVG (50% rule check).
        
        Args:
            df: OHLCV DataFrame
            index: Current candle index
            fvgs: List of FairValueGap objects
            fvg_type: 'bullish' or 'bearish'
            retrace_threshold: Retrace level (0.5 = 50% retrace)
        
        Returns:
            True if price at FVG retrace level
        """
        current_price = df['Close'].iloc[index]
        
        target_fvgs = [fvg for fvg in fvgs if fvg.fvg_type == fvg_type]
        
        for fvg in target_fvgs:
            gap_size = fvg.gap_top - fvg.gap_bottom
            retrace_level = fvg.gap_bottom + (gap_size * retrace_threshold)
            
            # Check if price is within 5 pips of retrace level
            if abs(current_price - retrace_level) < 5:
                return True
        
        return False
    
    def calculate_stop_loss_take_profit(
        self,
        entry_price: float,
        df: pd.DataFrame,
        index: int,
        signal_type: SignalType,
        support_resistance: dict = None
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and take profit levels.
        
        Args:
            entry_price: Entry price
            df: OHLCV DataFrame
            index: Current candle index
            signal_type: BUY or SELL
            support_resistance: Dict with 'support' and 'resistance' lists
        
        Returns:
            Tuple of (stop_loss, take_profit)
        """
        if 'ATR' not in df.columns:
            # Fallback: use recent volatility
            atr = (df['High'].iloc[index] - df['Low'].iloc[index]) * 1.5
        else:
            atr = df['ATR'].iloc[index]
            if pd.isna(atr):
                atr = (df['High'].iloc[index] - df['Low'].iloc[index]) * 1.5
        
        if signal_type == SignalType.BUY:
            # Stop loss: below entry or below recent support
            sl_dist = atr * self.atr_multiplier_sl
            stop_loss = entry_price - sl_dist
            
            # Take profit: above entry
            tp_dist = atr * self.atr_multiplier_tp
            take_profit = entry_price + tp_dist
            
            # Adjust if recent support/resistance available
            if support_resistance:
                if support_resistance['support']:
                    recent_support = max(support_resistance['support'])
                    stop_loss = min(stop_loss, recent_support - 1)
        
        else:  # SELL
            # Stop loss: above entry or above recent resistance
            sl_dist = atr * self.atr_multiplier_sl
            stop_loss = entry_price + sl_dist
            
            # Take profit: below entry
            tp_dist = atr * self.atr_multiplier_tp
            take_profit = entry_price - tp_dist
            
            # Adjust if recent support/resistance available
            if support_resistance:
                if support_resistance['resistance']:
                    recent_resistance = min(support_resistance['resistance'])
                    stop_loss = max(stop_loss, recent_resistance + 1)
        
        return stop_loss, take_profit
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        zones: List,
        order_blocks: List,
        fvgs: List,
        support_resistance: dict,
        lookback: int = 50
    ) -> pd.DataFrame:
        """
        Generate trading signals for all candles in DataFrame.
        
        Args:
            df: OHLCV DataFrame with indicators (EMA_200, ATR)
            zones: List of Zone objects
            order_blocks: List of OrderBlock objects
            fvgs: List of FairValueGap objects
            support_resistance: Dict with 'support' and 'resistance' lists
            lookback: Number of recent candles to analyze
        
        Returns:
            DataFrame with signal columns added
        """
        df = df.copy()
        df['Signal'] = SignalType.NONE.value
        df['EntryPrice'] = np.nan
        df['StopLoss'] = np.nan
        df['TakeProfit'] = np.nan
        df['Reason'] = ''
        df['RiskReward'] = np.nan
        
        start_idx = max(0, len(df) - lookback)
        
        for i in range(start_idx, len(df)):
            current_price = df['Close'].iloc[i]
            
            # BUY Signal Conditions
            buy_conditions = []
            
            # Condition 1: Price in demand zone
            if self.check_price_in_zone(df, i, zones, 'demand'):
                buy_conditions.append('in_demand_zone')
            
            # Condition 2: Reject support
            if self.check_support_rejection(df, i, support_resistance.get('support', [])):
                buy_conditions.append('support_rejection')
            
            # Condition 3: Bullish order block alignment
            if self.check_order_block_alignment(df, i, order_blocks, 'bullish'):
                buy_conditions.append('bullish_ob')
            
            # Condition 4: Bullish FVG retrace
            if self.check_fvg_alignment(df, i, fvgs, 'bullish'):
                buy_conditions.append('bullish_fvg')
            
            # Condition 5: Multi-timeframe trend
            if self.check_trend(df, i, 'up'):
                buy_conditions.append('bullish_trend')
            
            # Apply BUY signal if at least 2 conditions met
            if len(buy_conditions) >= 2:
                sl, tp = self.calculate_stop_loss_take_profit(
                    current_price, df, i, SignalType.BUY, support_resistance
                )
                
                signal = TradeSignal(
                    signal_type=SignalType.BUY,
                    candle_index=i,
                    entry_price=current_price,
                    stop_loss=sl,
                    take_profit=tp,
                    reason=','.join(buy_conditions)
                )
                
                # Check minimum risk/reward
                if signal.risk_reward_ratio() >= self.min_risk_reward:
                    df.loc[df.index[i], 'Signal'] = SignalType.BUY.value
                    df.loc[df.index[i], 'EntryPrice'] = current_price
                    df.loc[df.index[i], 'StopLoss'] = sl
                    df.loc[df.index[i], 'TakeProfit'] = tp
                    df.loc[df.index[i], 'Reason'] = signal.reason
                    df.loc[df.index[i], 'RiskReward'] = signal.risk_reward_ratio()
            
            # SELL Signal Conditions
            sell_conditions = []
            
            # Condition 1: Price in supply zone
            if self.check_price_in_zone(df, i, zones, 'supply'):
                sell_conditions.append('in_supply_zone')
            
            # Condition 2: Reject resistance
            if self.check_resistance_rejection(df, i, support_resistance.get('resistance', [])):
                sell_conditions.append('resistance_rejection')
            
            # Condition 3: Bearish order block alignment
            if self.check_order_block_alignment(df, i, order_blocks, 'bearish'):
                sell_conditions.append('bearish_ob')
            
            # Condition 4: Bearish FVG retrace
            if self.check_fvg_alignment(df, i, fvgs, 'bearish'):
                sell_conditions.append('bearish_fvg')
            
            # Condition 5: Multi-timeframe trend
            if self.check_trend(df, i, 'down'):
                sell_conditions.append('bearish_trend')
            
            # Apply SELL signal if at least 2 conditions met
            if len(sell_conditions) >= 2:
                sl, tp = self.calculate_stop_loss_take_profit(
                    current_price, df, i, SignalType.SELL, support_resistance
                )
                
                signal = TradeSignal(
                    signal_type=SignalType.SELL,
                    candle_index=i,
                    entry_price=current_price,
                    stop_loss=sl,
                    take_profit=tp,
                    reason=','.join(sell_conditions)
                )
                
                # Check minimum risk/reward
                if signal.risk_reward_ratio() >= self.min_risk_reward:
                    df.loc[df.index[i], 'Signal'] = SignalType.SELL.value
                    df.loc[df.index[i], 'EntryPrice'] = current_price
                    df.loc[df.index[i], 'StopLoss'] = sl
                    df.loc[df.index[i], 'TakeProfit'] = tp
                    df.loc[df.index[i], 'Reason'] = signal.reason
                    df.loc[df.index[i], 'RiskReward'] = signal.risk_reward_ratio()
        
        signal_count = len(df[df['Signal'] != 0])
        buy_count = len(df[df['Signal'] == SignalType.BUY.value])
        sell_count = len(df[df['Signal'] == SignalType.SELL.value])
        
        logger.info(f"Generated {signal_count} signals ({buy_count} BUY, {sell_count} SELL)")
        
        return df


if __name__ == "__main__":
    from data_fetch import load_demo_data
    from zone_detector import ZoneDetector
    
    df = load_demo_data()
    df = df.tail(500)
    
    detector = ZoneDetector()
    swing_highs, swing_lows = detector.detect_swings(df)
    zones = detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
    zones = detector.update_zone_mitigation(zones, df)
    
    obs = detector.detect_order_blocks(df)
    fvgs = detector.detect_fair_value_gaps(df)
    srl = detector.detect_support_resistance(df)
    
    generator = SignalGenerator()
    df = generator.generate_signals(df, zones, obs, fvgs, srl)
    
    signals_df = df[df['Signal'] != 0]
    print(f"\nTotal Signals: {len(signals_df)}")
    print(signals_df[['Close', 'Signal', 'EntryPrice', 'StopLoss', 'TakeProfit', 'Reason']].tail(10))
