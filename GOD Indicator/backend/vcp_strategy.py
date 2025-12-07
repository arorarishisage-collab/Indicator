"""
Minervini's VCP (Volatility Contraction Pattern) Strategy
Implementation of Mark Minervini's VCP pattern recognition for Grade A and Grade B setups

Grade A Criteria:
- 3-4 contractions with decreasing volatility
- Final contraction < 15% depth
- Tight price action near highs
- Volume drying up on pullbacks
- Strong price increase (30%+) before pattern

Grade B Criteria:
- 2-3 contractions with decreasing volatility
- Final contraction < 25% depth
- Looser price action
- Moderate volume patterns
- Good price increase (15-30%) before pattern
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from backend.base_strategy import BaseStrategy


class VCPStrategy(BaseStrategy):
    """
    Minervini's Volatility Contraction Pattern Strategy
    
    Identifies Grade A and Grade B VCP patterns for momentum breakout trading.
    Grade A patterns are tighter and more reliable than Grade B.
    """
    
    def __init__(
        self,
        lookback_period: int = 60,
        min_base_length: int = 15,
        max_base_length: int = 90,
        grade_a_final_contraction: float = 0.15,  # 15% max depth
        grade_b_final_contraction: float = 0.25,  # 25% max depth
        volume_ma_period: int = 50,
        breakout_volume_multiplier: float = 1.5,
        pivot_resistance_threshold: float = 0.02,  # 2% above resistance
        min_contractions_grade_a: int = 3,
        min_contractions_grade_b: int = 2,
        prior_uptrend_threshold_a: float = 0.30,  # 30% gain before pattern
        prior_uptrend_threshold_b: float = 0.15,  # 15% gain before pattern
        atr_period: int = 14
    ):
        """
        Initialize VCP Strategy with configurable parameters.
        
        Args:
            lookback_period: Bars to look back for pattern detection
            min_base_length: Minimum bars in consolidation base
            max_base_length: Maximum bars in consolidation base
            grade_a_final_contraction: Max depth for Grade A final contraction (15%)
            grade_b_final_contraction: Max depth for Grade B final contraction (25%)
            volume_ma_period: Period for volume moving average
            breakout_volume_multiplier: Volume must exceed MA by this factor
            pivot_resistance_threshold: Breakout above resistance by this %
            min_contractions_grade_a: Minimum contractions for Grade A (3-4)
            min_contractions_grade_b: Minimum contractions for Grade B (2-3)
            prior_uptrend_threshold_a: Prior gain required for Grade A (30%+)
            prior_uptrend_threshold_b: Prior gain required for Grade B (15%+)
            atr_period: Period for ATR calculation (volatility)
        """
        super().__init__(
            name="VCP Strategy",
            description="Minervini's Volatility Contraction Pattern - Grade A/B breakout detection",
            parameters={
                'lookback_period': lookback_period,
                'min_base_length': min_base_length,
                'max_base_length': max_base_length,
                'grade_a_final_contraction': grade_a_final_contraction,
                'grade_b_final_contraction': grade_b_final_contraction,
                'volume_ma_period': volume_ma_period,
                'breakout_volume_multiplier': breakout_volume_multiplier,
                'pivot_resistance_threshold': pivot_resistance_threshold,
                'min_contractions_grade_a': min_contractions_grade_a,
                'min_contractions_grade_b': min_contractions_grade_b,
                'prior_uptrend_threshold_a': prior_uptrend_threshold_a,
                'prior_uptrend_threshold_b': prior_uptrend_threshold_b,
                'atr_period': atr_period
            }
        )
        self.lookback_period = lookback_period
        self.min_base_length = min_base_length
        self.max_base_length = max_base_length
        self.grade_a_final_contraction = grade_a_final_contraction
        self.grade_b_final_contraction = grade_b_final_contraction
        self.volume_ma_period = volume_ma_period
        self.breakout_volume_multiplier = breakout_volume_multiplier
        self.pivot_resistance_threshold = pivot_resistance_threshold
        self.min_contractions_grade_a = min_contractions_grade_a
        self.min_contractions_grade_b = min_contractions_grade_b
        self.prior_uptrend_threshold_a = prior_uptrend_threshold_a
        self.prior_uptrend_threshold_b = prior_uptrend_threshold_b
        self.atr_period = atr_period
    
    def validate_inputs(self, df: pd.DataFrame) -> bool:
        """
        Validate that input DataFrame has required columns for VCP strategy.
        
        Args:
            df: Input DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        return all(col in df.columns for col in required_columns)
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate VCP buy signals with Grade A/B classification.
        
        Returns dataframe with:
        - Signal: 1 (BUY), 0 (HOLD)
        - Signal_Strength: 1-10 (Grade A: 8-10, Grade B: 6-8)
        - VCP_Grade: 'A', 'B', or None
        - VCP_Pivot: Resistance level to break
        - Stop_Loss: Swing low of final contraction
        - Take_Profit: ATR-based target
        """
        df = df.copy()
        
        # Initialize columns
        df['Signal'] = 0
        df['Signal_Strength'] = 0.0
        df['VCP_Grade'] = None
        df['VCP_Pivot'] = np.nan
        df['VCP_Contractions'] = 0
        df['VCP_Base_Length'] = 0
        df['VCP_Prior_Gain'] = 0.0
        df['Stop_Loss'] = np.nan
        df['Take_Profit'] = np.nan
        
        if len(df) < self.lookback_period:
            return df
        
        # Calculate technical indicators
        df = self._calculate_indicators(df)
        
        # Detect VCP patterns
        for i in range(self.lookback_period, len(df)):
            vcp_result = self._detect_vcp_pattern(df, i)
            
            if vcp_result['detected']:
                grade = vcp_result['grade']
                df.at[df.index[i], 'VCP_Grade'] = grade
                df.at[df.index[i], 'VCP_Pivot'] = vcp_result['pivot_level']
                df.at[df.index[i], 'VCP_Contractions'] = vcp_result['num_contractions']
                df.at[df.index[i], 'VCP_Base_Length'] = vcp_result['base_length']
                df.at[df.index[i], 'VCP_Prior_Gain'] = vcp_result['prior_gain']
                
                # Check for breakout
                if self._is_breakout(df, i, vcp_result['pivot_level']):
                    df.at[df.index[i], 'Signal'] = 1
                    
                    # Signal strength based on grade and quality
                    if grade == 'A':
                        base_strength = 8.5
                    else:  # Grade B
                        base_strength = 6.5
                    
                    # Adjust for quality factors
                    strength_adjustments = 0
                    
                    # Volume confirmation
                    if df.at[df.index[i], 'Volume'] > df.at[df.index[i], 'Volume_MA'] * self.breakout_volume_multiplier:
                        strength_adjustments += 0.5
                    
                    # Strong prior uptrend
                    if vcp_result['prior_gain'] > (self.prior_uptrend_threshold_a if grade == 'A' else self.prior_uptrend_threshold_b) * 1.5:
                        strength_adjustments += 0.5
                    
                    # Tight final contraction
                    if vcp_result['final_contraction_depth'] < 0.10:  # Less than 10%
                        strength_adjustments += 0.5
                    
                    # Many contractions (4+ is excellent)
                    if vcp_result['num_contractions'] >= 4:
                        strength_adjustments += 0.5
                    
                    final_strength = min(10.0, base_strength + strength_adjustments)
                    df.at[df.index[i], 'Signal_Strength'] = final_strength
                    
                    # Set stop loss and take profit
                    stop_loss = vcp_result['swing_low']
                    df.at[df.index[i], 'Stop_Loss'] = stop_loss
                    
                    # Take profit: 2x risk (R:R = 2:1)
                    risk = df.at[df.index[i], 'Close'] - stop_loss
                    df.at[df.index[i], 'Take_Profit'] = df.at[df.index[i], 'Close'] + (risk * 2)
        
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for VCP detection."""
        # Volume moving average
        df['Volume_MA'] = df['Volume'].rolling(window=self.volume_ma_period).mean()
        
        # ATR for volatility measurement
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(window=self.atr_period).mean()
        
        # Moving averages for trend context
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # Price momentum
        df['ROC_50'] = ((df['Close'] - df['Close'].shift(50)) / df['Close'].shift(50)) * 100
        
        return df
    
    def _detect_vcp_pattern(self, df: pd.DataFrame, current_idx: int) -> Dict:
        """
        Detect VCP pattern at current index.
        
        Returns dict with pattern details or empty dict if no pattern.
        """
        result = {
            'detected': False,
            'grade': None,
            'pivot_level': None,
            'num_contractions': 0,
            'base_length': 0,
            'prior_gain': 0.0,
            'final_contraction_depth': 0.0,
            'swing_low': None
        }
        
        # Get lookback window
        start_idx = max(0, current_idx - self.lookback_period)
        window = df.iloc[start_idx:current_idx + 1]
        
        if len(window) < self.min_base_length:
            return result
        
        # Step 1: Check for prior uptrend
        prior_gain = self._calculate_prior_uptrend(df, start_idx)
        if prior_gain < self.prior_uptrend_threshold_b:  # Minimum for Grade B
            return result
        
        result['prior_gain'] = prior_gain
        
        # Step 2: Identify consolidation base
        base_high = window['High'].max()
        base_start_idx = window['High'].idxmax()
        base_start_pos = window.index.get_loc(base_start_idx)
        
        if base_start_pos < self.min_base_length or base_start_pos > self.max_base_length:
            return result
        
        base_window = window.iloc[base_start_pos:]
        result['base_length'] = len(base_window)
        
        # Step 3: Detect contractions within base
        contractions = self._find_contractions(base_window, base_high)
        
        if len(contractions) < self.min_contractions_grade_b:
            return result
        
        result['num_contractions'] = len(contractions)
        
        # Step 4: Verify decreasing volatility
        if not self._verify_decreasing_volatility(contractions):
            return result
        
        # Step 5: Check final contraction depth
        final_contraction = contractions[-1]
        final_depth = (base_high - final_contraction['low']) / base_high
        result['final_contraction_depth'] = final_depth
        result['swing_low'] = final_contraction['low']
        
        # Step 6: Determine grade
        if (len(contractions) >= self.min_contractions_grade_a and 
            final_depth <= self.grade_a_final_contraction and
            prior_gain >= self.prior_uptrend_threshold_a):
            result['grade'] = 'A'
        elif (len(contractions) >= self.min_contractions_grade_b and 
              final_depth <= self.grade_b_final_contraction):
            result['grade'] = 'B'
        else:
            return result
        
        # Step 7: Set pivot resistance level
        result['pivot_level'] = base_high
        result['detected'] = True
        
        return result
    
    def _calculate_prior_uptrend(self, df: pd.DataFrame, start_idx: int) -> float:
        """Calculate gain from prior uptrend before base formation."""
        if start_idx < 100:
            return 0.0
        
        # Look back 50-100 bars for swing low
        lookback_start = max(0, start_idx - 100)
        lookback_window = df.iloc[lookback_start:start_idx]
        
        swing_low = lookback_window['Low'].min()
        current_high = df.iloc[start_idx]['High']
        
        gain = (current_high - swing_low) / swing_low
        return gain
    
    def _find_contractions(self, base_window: pd.DataFrame, base_high: float) -> list:
        """
        Find contraction pivots within the base.
        
        A contraction is a pullback from the base high followed by a rally attempt.
        """
        contractions = []
        
        in_pullback = False
        pullback_low = float('inf')
        pullback_low_idx = None
        
        for i in range(len(base_window)):
            current_price = base_window.iloc[i]['Close']
            current_low = base_window.iloc[i]['Low']
            
            # Check if we're in a pullback (decline from base high)
            pullback_depth = (base_high - current_low) / base_high
            
            if pullback_depth > 0.05:  # At least 5% pullback
                if not in_pullback:
                    in_pullback = True
                    pullback_low = current_low
                    pullback_low_idx = i
                elif current_low < pullback_low:
                    pullback_low = current_low
                    pullback_low_idx = i
            
            # Check if pullback is over (rally attempt)
            if in_pullback and i > pullback_low_idx + 2:
                if current_price > pullback_low * 1.02:  # 2% rally from low
                    contractions.append({
                        'low': pullback_low,
                        'depth': (base_high - pullback_low) / base_high,
                        'idx': pullback_low_idx
                    })
                    in_pullback = False
                    pullback_low = float('inf')
        
        return contractions
    
    def _verify_decreasing_volatility(self, contractions: list) -> bool:
        """
        Verify that contractions show decreasing volatility.
        
        Each successive contraction should be shallower (tighter).
        """
        if len(contractions) < 2:
            return True
        
        # Check if depth decreases (with some tolerance)
        tolerance = 0.05  # Allow 5% deviation
        
        for i in range(1, len(contractions)):
            current_depth = contractions[i]['depth']
            previous_depth = contractions[i - 1]['depth']
            
            # Current should be shallower (or within tolerance)
            if current_depth > previous_depth * (1 + tolerance):
                return False
        
        return True
    
    def _is_breakout(self, df: pd.DataFrame, idx: int, pivot_level: float) -> bool:
        """
        Check if current bar represents a valid breakout.
        
        Criteria:
        - Close above pivot level
        - Volume above average
        - Strong momentum
        """
        current_bar = df.iloc[idx]
        
        # Price breakout
        breakout_threshold = pivot_level * (1 + self.pivot_resistance_threshold)
        if current_bar['Close'] < breakout_threshold:
            return False
        
        # Volume confirmation
        if 'Volume_MA' in df.columns:
            if current_bar['Volume'] < current_bar['Volume_MA'] * 1.2:  # At least 20% above average
                return False
        
        # Momentum confirmation (positive close)
        if current_bar['Close'] < current_bar['Open']:
            return False
        
        return True
    
    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        risk_percent: float = 1.0
    ) -> int:
        """
        Calculate position size based on risk management.
        
        Args:
            account_balance: Total account size
            entry_price: Entry price for trade
            stop_loss: Stop loss price
            risk_percent: Percentage of account to risk (default 1%)
            
        Returns:
            Number of shares to buy
        """
        risk_amount = account_balance * (risk_percent / 100)
        risk_per_share = entry_price - stop_loss
        
        if risk_per_share <= 0:
            return 0
        
        shares = int(risk_amount / risk_per_share)
        return shares
    
    def get_pattern_details(self, df: pd.DataFrame, idx: int) -> Dict:
        """
        Get detailed VCP pattern information for a specific bar.
        
        Returns dict with pattern metrics and classification.
        """
        if idx >= len(df):
            return {}
        
        row = df.iloc[idx]
        
        details = {
            'timestamp': df.index[idx],
            'price': row['Close'],
            'signal': row['Signal'],
            'signal_strength': row['Signal_Strength'],
            'vcp_grade': row.get('VCP_Grade'),
            'pivot_level': row.get('VCP_Pivot'),
            'num_contractions': row.get('VCP_Contractions'),
            'base_length': row.get('VCP_Base_Length'),
            'prior_gain_pct': row.get('VCP_Prior_Gain', 0) * 100,
            'stop_loss': row.get('Stop_Loss'),
            'take_profit': row.get('Take_Profit'),
        }
        
        # Calculate risk/reward
        if details['stop_loss'] and not np.isnan(details['stop_loss']):
            risk = details['price'] - details['stop_loss']
            reward = details['take_profit'] - details['price'] if details['take_profit'] else 0
            details['risk_reward_ratio'] = reward / risk if risk > 0 else 0
        
        return details
    
    def __str__(self) -> str:
        return (
            f"VCPStrategy(lookback={self.lookback_period}, "
            f"grade_a_contraction={self.grade_a_final_contraction:.1%}, "
            f"grade_b_contraction={self.grade_b_final_contraction:.1%})"
        )
