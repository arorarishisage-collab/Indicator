"""
Zone Detection Module for ICT Trading Strategy
Identifies supply/demand zones, support/resistance, order blocks, and fair value gaps.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Zone:
    """Represents a trading zone (supply or demand)."""
    zone_type: str  # 'supply' or 'demand'
    entry_price: float  # Zone entry level (swing high/low)
    top: float  # Zone upper bound
    bottom: float  # Zone lower bound
    candle_index: int  # Index of swing candle
    mitigated: bool = False  # True if price has broken through zone
    mitigation_price: float = None  # Price at mitigation
    
    def width(self) -> float:
        """Return zone width in pips."""
        return self.top - self.bottom
    
    def contains(self, price: float) -> bool:
        """Check if price is within zone."""
        return self.bottom <= price <= self.top


@dataclass
class OrderBlock:
    """Represents an order block (OB) from ICT strategy."""
    ob_type: str  # 'bullish' or 'bearish'
    candle_index: int  # Index of OB candle
    high: float
    low: float
    
    def contains(self, price: float) -> bool:
        """Check if price is within OB."""
        return self.low <= price <= self.high


@dataclass
class FairValueGap:
    """Represents a Fair Value Gap (FVG) from ICT strategy."""
    fvg_type: str  # 'bullish' or 'bearish'
    candle_index: int  # Index of candle 3 in the 3-candle setup
    gap_top: float  # Upper boundary of gap
    gap_bottom: float  # Lower boundary of gap
    gap_size: float  # Gap width in pips
    
    def contains(self, price: float) -> bool:
        """Check if price is within gap."""
        return self.gap_bottom <= price <= self.gap_top


class ZoneDetector:
    """Detects supply/demand zones, S/R levels, and ICT elements."""
    
    def __init__(self, lookback: int = 20, atr_multiplier: float = 1.5):
        """
        Initialize ZoneDetector.
        
        Args:
            lookback: Period for swing high/low detection (default: 20)
            atr_multiplier: ATR multiplier for zone expansion (default: 1.5)
        """
        self.lookback = lookback
        self.atr_multiplier = atr_multiplier
    
    def detect_swings(self, df: pd.DataFrame) -> Tuple[List[int], List[int]]:
        """
        Detect swing highs and lows using fractals.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            Tuple of (swing_high_indices, swing_low_indices)
        """
        swing_highs = []
        swing_lows = []
        
        half_lookback = self.lookback // 2
        
        for i in range(half_lookback, len(df) - half_lookback):
            high_val = df['High'].iloc[i]
            low_val = df['Low'].iloc[i]
            
            # Check for swing high (local maximum)
            if high_val == df['High'].iloc[i - half_lookback:i + half_lookback + 1].max():
                swing_highs.append(i)
            
            # Check for swing low (local minimum)
            if low_val == df['Low'].iloc[i - half_lookback:i + half_lookback + 1].min():
                swing_lows.append(i)
        
        logger.info(f"Detected {len(swing_highs)} swing highs and {len(swing_lows)} swing lows")
        return swing_highs, swing_lows
    
    def detect_supply_demand_zones(
        self,
        df: pd.DataFrame,
        swing_highs: List[int],
        swing_lows: List[int]
    ) -> List[Zone]:
        """
        Identify supply and demand zones around swings.
        
        Args:
            df: OHLCV DataFrame
            swing_highs: Indices of swing highs
            swing_lows: Indices of swing lows
        
        Returns:
            List of Zone objects
        """
        zones = []
        
        # Ensure ATR column exists
        if 'ATR' not in df.columns:
            df['ATR'] = df['High'].rolling(14).mean() - df['Low'].rolling(14).mean()
        
        # Demand zones (below price after upswing)
        for idx in swing_lows:
            if idx < len(df) - 1:
                entry_price = df['Low'].iloc[idx]
                atr = df['ATR'].iloc[idx] if pd.notna(df['ATR'].iloc[idx]) else (df['High'].iloc[idx] - df['Low'].iloc[idx]) * 1.5
                zone_width = atr * self.atr_multiplier
                
                zone = Zone(
                    zone_type='demand',
                    entry_price=entry_price,
                    top=entry_price + zone_width * 0.5,
                    bottom=entry_price - zone_width * 0.5,
                    candle_index=idx
                )
                zones.append(zone)
        
        # Supply zones (above price after downswing)
        for idx in swing_highs:
            if idx < len(df) - 1:
                entry_price = df['High'].iloc[idx]
                atr = df['ATR'].iloc[idx] if pd.notna(df['ATR'].iloc[idx]) else (df['High'].iloc[idx] - df['Low'].iloc[idx]) * 1.5
                zone_width = atr * self.atr_multiplier
                
                zone = Zone(
                    zone_type='supply',
                    entry_price=entry_price,
                    top=entry_price + zone_width * 0.5,
                    bottom=entry_price - zone_width * 0.5,
                    candle_index=idx
                )
                zones.append(zone)
        
        logger.info(f"Identified {len(zones)} supply/demand zones")
        return zones
    
    def detect_support_resistance(self, df: pd.DataFrame, n_recent: int = 5) -> Dict[str, List[float]]:
        """
        Detect support and resistance levels from recent swings.
        
        Args:
            df: OHLCV DataFrame
            n_recent: Number of recent swings to consider
        
        Returns:
            Dictionary with 'support' and 'resistance' lists
        """
        swing_highs, swing_lows = self.detect_swings(df)
        
        # Get recent swings
        recent_highs = [df['High'].iloc[idx] for idx in swing_highs[-n_recent:]]
        recent_lows = [df['Low'].iloc[idx] for idx in swing_lows[-n_recent:]]
        
        return {
            'resistance': sorted(recent_highs, reverse=True),
            'support': sorted(recent_lows)
        }
    
    def detect_order_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """
        Detect order blocks (OB): last opposing candle before impulse move.
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            List of OrderBlock objects
        """
        order_blocks = []
        
        # Look for impulse moves (3+ consecutive candles in same direction)
        for i in range(2, len(df) - 1):
            # Bullish impulse: 3 consecutive bullish candles (close > open)
            if (df['Close'].iloc[i-2] > df['Open'].iloc[i-2] and
                df['Close'].iloc[i-1] > df['Open'].iloc[i-1] and
                df['Close'].iloc[i] > df['Open'].iloc[i]):
                
                # Last bearish candle before impulse = bullish OB
                if i >= 2 and df['Close'].iloc[i-3] < df['Open'].iloc[i-3]:
                    ob = OrderBlock(
                        ob_type='bullish',
                        candle_index=i - 3,
                        high=df['High'].iloc[i - 3],
                        low=df['Low'].iloc[i - 3]
                    )
                    order_blocks.append(ob)
            
            # Bearish impulse: 3 consecutive bearish candles (close < open)
            if (df['Close'].iloc[i-2] < df['Open'].iloc[i-2] and
                df['Close'].iloc[i-1] < df['Open'].iloc[i-1] and
                df['Close'].iloc[i] < df['Open'].iloc[i]):
                
                # Last bullish candle before impulse = bearish OB
                if i >= 2 and df['Close'].iloc[i-3] > df['Open'].iloc[i-3]:
                    ob = OrderBlock(
                        ob_type='bearish',
                        candle_index=i - 3,
                        high=df['High'].iloc[i - 3],
                        low=df['Low'].iloc[i - 3]
                    )
                    order_blocks.append(ob)
        
        logger.info(f"Detected {len(order_blocks)} order blocks")
        return order_blocks
    
    def detect_fair_value_gaps(self, df: pd.DataFrame) -> List[FairValueGap]:
        """
        Detect Fair Value Gaps (FVG): 3-candle inefficiency gaps.
        
        Bullish FVG: high(candle1) < low(candle3) with candle2 as bridge
        Bearish FVG: low(candle1) > high(candle3)
        
        Args:
            df: OHLCV DataFrame
        
        Returns:
            List of FairValueGap objects
        """
        fvgs = []
        
        for i in range(2, len(df)):
            high_1 = df['High'].iloc[i - 2]
            low_1 = df['Low'].iloc[i - 2]
            high_2 = df['High'].iloc[i - 1]
            low_2 = df['Low'].iloc[i - 1]
            high_3 = df['High'].iloc[i]
            low_3 = df['Low'].iloc[i]
            
            # Bullish FVG: high(1) < low(3)
            if high_1 < low_3:
                gap_size = low_3 - high_1
                fvg = FairValueGap(
                    fvg_type='bullish',
                    candle_index=i,
                    gap_top=low_3,
                    gap_bottom=high_1,
                    gap_size=gap_size
                )
                fvgs.append(fvg)
            
            # Bearish FVG: low(1) > high(3)
            if low_1 > high_3:
                gap_size = low_1 - high_3
                fvg = FairValueGap(
                    fvg_type='bearish',
                    candle_index=i,
                    gap_top=low_1,
                    gap_bottom=high_3,
                    gap_size=gap_size
                )
                fvgs.append(fvg)
        
        logger.info(f"Detected {len(fvgs)} fair value gaps")
        return fvgs
    
    def update_zone_mitigation(self, zones: List[Zone], df: pd.DataFrame) -> List[Zone]:
        """
        Update zone mitigation status based on price action.
        
        Args:
            zones: List of Zone objects
            df: OHLCV DataFrame
        
        Returns:
            Updated zones with mitigation info
        """
        for zone in zones:
            for i in range(zone.candle_index + 1, len(df)):
                price = df['Close'].iloc[i]
                
                if zone.zone_type == 'demand' and price > zone.top:
                    zone.mitigated = True
                    zone.mitigation_price = price
                    break
                elif zone.zone_type == 'supply' and price < zone.bottom:
                    zone.mitigated = True
                    zone.mitigation_price = price
                    break
        
        unmitigated = sum(1 for z in zones if not z.mitigated)
        logger.info(f"Zone status: {unmitigated} unmitigated, {len(zones) - unmitigated} mitigated")
        
        return zones
    
    def get_active_zones(self, zones: List[Zone], df: pd.DataFrame) -> List[Zone]:
        """Get only unmitigated zones that are close to current price."""
        current_price = df['Close'].iloc[-1]
        
        # Filter unmitigated zones within 100 pips
        active = [
            z for z in zones
            if not z.mitigated and abs(current_price - z.entry_price) < 100
        ]
        
        return sorted(active, key=lambda z: abs(current_price - z.entry_price))


def analyze_zones_for_signal(
    df: pd.DataFrame,
    zones: List[Zone],
    order_blocks: List[OrderBlock],
    fvgs: List[FairValueGap],
    detector: ZoneDetector
) -> Dict:
    """
    Analyze zones and ICT elements for trading signals.
    
    Args:
        df: OHLCV DataFrame
        zones: List of Zone objects
        order_blocks: List of OrderBlock objects
        fvgs: List of FairValueGap objects
        detector: ZoneDetector instance
    
    Returns:
        Dictionary with analysis results
    """
    current_price = df['Close'].iloc[-1]
    current_high = df['High'].iloc[-1]
    current_low = df['Low'].iloc[-1]
    
    # Find nearest demand zone
    demand_zones = [z for z in zones if z.zone_type == 'demand' and not z.mitigated]
    nearest_demand = min(demand_zones, key=lambda z: abs(z.entry_price - current_price), default=None)
    
    # Find nearest supply zone
    supply_zones = [z for z in zones if z.zone_type == 'supply' and not z.mitigated]
    nearest_supply = min(supply_zones, key=lambda z: abs(z.entry_price - current_price), default=None)
    
    # Check for bullish OBs near price
    bullish_obs = [ob for ob in order_blocks if ob.ob_type == 'bullish' and abs(ob.low - current_price) < 50]
    
    # Check for bearish OBs near price
    bearish_obs = [ob for ob in order_blocks if ob.ob_type == 'bearish' and abs(ob.high - current_price) < 50]
    
    # Check for bullish FVGs near price
    bullish_fvgs = [fvg for fvg in fvgs if fvg.fvg_type == 'bullish' and fvg.contains(current_price)]
    
    # Check for bearish FVGs near price
    bearish_fvgs = [fvg for fvg in fvgs if fvg.fvg_type == 'bearish' and fvg.contains(current_price)]
    
    return {
        'current_price': current_price,
        'nearest_demand': nearest_demand,
        'nearest_supply': nearest_supply,
        'bullish_obs_nearby': len(bullish_obs),
        'bearish_obs_nearby': len(bearish_obs),
        'bullish_fvgs_nearby': len(bullish_fvgs),
        'bearish_fvgs_nearby': len(bearish_fvgs)
    }


if __name__ == "__main__":
    # Example usage
    from data_fetch import load_demo_data
    
    df = load_demo_data()
    df = df.tail(500)  # Last 500 candles
    
    detector = ZoneDetector(lookback=20, atr_multiplier=1.5)
    
    swing_highs, swing_lows = detector.detect_swings(df)
    zones = detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
    zones = detector.update_zone_mitigation(zones, df)
    
    srl = detector.detect_support_resistance(df)
    print(f"\nSupport Levels: {srl['support']}")
    print(f"Resistance Levels: {srl['resistance']}")
    
    obs = detector.detect_order_blocks(df)
    print(f"\nOrder Blocks: {len(obs)}")
    
    fvgs = detector.detect_fair_value_gaps(df)
    print(f"Fair Value Gaps: {len(fvgs)}")
    
    print(f"\nZones: {len(zones)}")
    for z in zones[-5:]:
        print(f"  {z.zone_type}: {z.bottom:.2f} - {z.top:.2f} (mitigated: {z.mitigated})")
