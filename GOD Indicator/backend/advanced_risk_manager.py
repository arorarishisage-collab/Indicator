"""
Advanced Risk Manager - Kelly Criterion, Drawdown Scaling, Volatility Adjustment
Dynamically adjusts position size based on edge, recent performance, and market conditions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedRiskManager:
    """
    Advanced position sizing and risk management
    - Kelly Criterion for optimal position sizing
    - Drawdown-based risk reduction
    - Volatility-adjusted sizing
    - Max correlation limits
    """
    
    def __init__(self,
                 base_risk_pct: float = 0.01,  # 1% base risk per trade
                 max_risk_pct: float = 0.03,  # 3% maximum risk per trade
                 max_total_risk_pct: float = 0.10,  # 10% total portfolio risk
                 max_drawdown_threshold: float = 0.15,  # 15% max drawdown
                 kelly_fraction: float = 0.25,  # Use 25% of Kelly (Quarter Kelly)
                 atr_baseline: Optional[float] = None,  # Baseline ATR for normalization
                 recent_trades_window: int = 20):  # Look back 20 trades for performance
        """
        Initialize advanced risk manager
        
        Args:
            base_risk_pct: Base risk per trade as % of capital
            max_risk_pct: Maximum risk per trade
            max_total_risk_pct: Maximum total portfolio risk
            max_drawdown_threshold: Reduce risk if drawdown exceeds this
            kelly_fraction: Fraction of Kelly to use (0.25 = Quarter Kelly, conservative)
            atr_baseline: Baseline ATR for volatility normalization
            recent_trades_window: Number of recent trades to analyze
        """
        self.base_risk_pct = base_risk_pct
        self.max_risk_pct = max_risk_pct
        self.max_total_risk_pct = max_total_risk_pct
        self.max_drawdown_threshold = max_drawdown_threshold
        self.kelly_fraction = kelly_fraction
        self.atr_baseline = atr_baseline
        self.recent_trades_window = recent_trades_window
    
    def calculate_kelly_criterion(self, 
                                   win_rate: float, 
                                   avg_win: float, 
                                   avg_loss: float) -> float:
        """
        Calculate Kelly Criterion for optimal position sizing
        
        Kelly % = (W * R - L) / R
        where:
        - W = win rate (probability of winning)
        - L = loss rate (1 - W)
        - R = win/loss ratio (avg_win / avg_loss)
        
        Args:
            win_rate: Win rate as decimal (0.60 = 60%)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)
            
        Returns:
            Kelly percentage (0-1), adjusted by kelly_fraction for safety
        """
        if avg_loss <= 0 or avg_win <= 0:
            logger.warning("Invalid avg_win or avg_loss for Kelly calculation")
            return self.base_risk_pct
        
        # Calculate win/loss ratio
        win_loss_ratio = avg_win / avg_loss
        
        # Kelly formula
        loss_rate = 1 - win_rate
        kelly_pct = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
        
        # Apply Kelly fraction (Quarter Kelly for safety)
        adjusted_kelly = kelly_pct * self.kelly_fraction
        
        # Ensure within bounds
        adjusted_kelly = max(0, min(adjusted_kelly, self.max_risk_pct))
        
        logger.debug(f"Kelly Criterion: {kelly_pct:.4f} | Adjusted (Quarter Kelly): {adjusted_kelly:.4f}")
        
        return adjusted_kelly
    
    def calculate_drawdown_factor(self, recent_trades: List[Dict]) -> float:
        """
        Calculate risk reduction factor based on recent drawdown
        
        During losing streaks, reduce position size to preserve capital
        
        Args:
            recent_trades: List of recent trade dictionaries with 'pnl' key
            
        Returns:
            Drawdown factor (0.0 to 1.0), where 1.0 = no adjustment
        """
        if not recent_trades:
            return 1.0
        
        # Calculate cumulative PnL and drawdown
        pnls = [trade.get('pnl', 0) for trade in recent_trades]
        cumulative_pnl = np.cumsum(pnls)
        
        # Calculate running max and drawdown
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = cumulative_pnl - running_max
        
        # Calculate max drawdown as percentage
        initial_balance = abs(pnls[0]) * 50  # Estimate based on first trade
        max_drawdown_pct = abs(np.min(drawdown)) / initial_balance if initial_balance > 0 else 0
        
        # Risk reduction based on drawdown
        if max_drawdown_pct < 0.05:  # Less than 5% drawdown
            factor = 1.0
        elif max_drawdown_pct < 0.10:  # 5-10% drawdown
            factor = 0.8
        elif max_drawdown_pct < self.max_drawdown_threshold:  # 10-15% drawdown
            factor = 0.5
        else:  # Greater than 15% drawdown
            factor = 0.25  # Severe risk reduction
            logger.warning(f"⚠️ SEVERE DRAWDOWN: {max_drawdown_pct:.2%} - Reducing position size to 25%")
        
        logger.debug(f"Drawdown: {max_drawdown_pct:.2%} | Risk factor: {factor:.2f}")
        
        return factor
    
    def calculate_volatility_factor(self, current_atr: float, baseline_atr: Optional[float] = None) -> float:
        """
        Calculate risk adjustment based on current volatility vs baseline
        
        High volatility = reduce position size
        Low volatility = increase position size
        
        Args:
            current_atr: Current Average True Range
            baseline_atr: Baseline ATR (typical/average ATR)
            
        Returns:
            Volatility factor (0.5 to 1.5)
        """
        if baseline_atr is None:
            baseline_atr = self.atr_baseline
        
        if baseline_atr is None or baseline_atr == 0 or current_atr == 0:
            return 1.0  # No adjustment if no baseline
        
        # Volatility ratio
        vol_ratio = current_atr / baseline_atr
        
        # Inverse relationship: higher volatility = lower position size
        if vol_ratio < 0.7:  # Very low volatility
            factor = 1.2  # Increase size slightly
        elif vol_ratio < 1.3:  # Normal volatility
            factor = 1.0  # No adjustment
        elif vol_ratio < 2.0:  # High volatility
            factor = 0.7  # Reduce size
        else:  # Extreme volatility
            factor = 0.5  # Severe reduction
            logger.warning(f"⚠️ EXTREME VOLATILITY: ATR {vol_ratio:.2f}x baseline - Reducing size to 50%")
        
        logger.debug(f"ATR Ratio: {vol_ratio:.2f} | Vol factor: {factor:.2f}")
        
        return factor
    
    def calculate_consecutive_loss_factor(self, recent_trades: List[Dict]) -> float:
        """
        Reduce risk after consecutive losses to prevent revenge trading
        
        Args:
            recent_trades: List of recent trades
            
        Returns:
            Loss streak factor (0.5 to 1.0)
        """
        if not recent_trades:
            return 1.0
        
        # Count consecutive losses
        consecutive_losses = 0
        for trade in reversed(recent_trades):
            if trade.get('pnl', 0) < 0:
                consecutive_losses += 1
            else:
                break
        
        # Risk reduction based on streak
        if consecutive_losses == 0:
            factor = 1.0
        elif consecutive_losses <= 2:
            factor = 0.9
        elif consecutive_losses <= 4:
            factor = 0.7
            logger.warning(f"⚠️ {consecutive_losses} consecutive losses - Reducing size to 70%")
        else:
            factor = 0.5
            logger.warning(f"⚠️ {consecutive_losses} consecutive losses - Reducing size to 50%")
        
        return factor
    
    def calculate_regime_factor(self, regime: str) -> float:
        """
        Adjust risk based on market regime
        
        Args:
            regime: Market regime from MarketRegimeDetector
            
        Returns:
            Regime factor (0.0 to 1.5)
        """
        regime_factors = {
            'TRENDING_UP': 1.2,      # Favorable conditions
            'TRENDING_DOWN': 1.2,    # Favorable conditions
            'RANGING': 0.7,          # Moderate conditions
            'VOLATILE': 0.4,         # Dangerous conditions
            'CHOPPY': 0.0,           # Do not trade
            'UNKNOWN': 0.8,          # Conservative
        }
        
        factor = regime_factors.get(regime, 0.8)
        
        if factor < 0.5:
            logger.warning(f"⚠️ Unfavorable regime: {regime} - Reducing risk significantly")
        
        return factor
    
    def calculate_optimal_position_size(self,
                                       capital: float,
                                       entry_price: float,
                                       stop_loss: float,
                                       recent_trades: List[Dict],
                                       current_atr: Optional[float] = None,
                                       market_regime: Optional[str] = None,
                                       win_rate: Optional[float] = None,
                                       avg_win: Optional[float] = None,
                                       avg_loss: Optional[float] = None) -> Dict:
        """
        Calculate optimal position size using multiple risk factors
        
        Args:
            capital: Current capital
            entry_price: Planned entry price
            stop_loss: Stop loss price
            recent_trades: List of recent trades for performance analysis
            current_atr: Current ATR for volatility adjustment
            market_regime: Current market regime
            win_rate: Historical win rate (for Kelly)
            avg_win: Average winning trade (for Kelly)
            avg_loss: Average losing trade (for Kelly)
            
        Returns:
            Dictionary with position size details and risk factors
        """
        # Calculate base risk
        if win_rate and avg_win and avg_loss:
            # Use Kelly Criterion if performance data available
            kelly_risk_pct = self.calculate_kelly_criterion(win_rate, avg_win, avg_loss)
            base_risk_pct = kelly_risk_pct
        else:
            # Use default base risk
            base_risk_pct = self.base_risk_pct
        
        # Calculate adjustment factors
        drawdown_factor = self.calculate_drawdown_factor(recent_trades[-self.recent_trades_window:] if recent_trades else [])
        loss_streak_factor = self.calculate_consecutive_loss_factor(recent_trades[-10:] if recent_trades else [])
        
        volatility_factor = 1.0
        if current_atr:
            volatility_factor = self.calculate_volatility_factor(current_atr)
        
        regime_factor = 1.0
        if market_regime:
            regime_factor = self.calculate_regime_factor(market_regime)
        
        # Combined risk percentage
        adjusted_risk_pct = (base_risk_pct * 
                            drawdown_factor * 
                            loss_streak_factor * 
                            volatility_factor * 
                            regime_factor)
        
        # Ensure within bounds
        adjusted_risk_pct = max(0, min(adjusted_risk_pct, self.max_risk_pct))
        
        # Calculate position size
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            logger.error("Invalid stop loss - zero risk per share")
            return {
                'position_size': 0,
                'contracts': 0,
                'risk_amount': 0,
                'risk_pct': 0,
                'error': 'Invalid stop loss'
            }
        
        risk_amount = capital * adjusted_risk_pct
        position_size = risk_amount / risk_per_share
        
        # Calculate number of contracts (for futures/options)
        contracts = int(position_size / 100) if position_size >= 100 else position_size / 100
        
        result = {
            'position_size': round(position_size, 2),
            'contracts': round(contracts, 4),
            'risk_amount': round(risk_amount, 2),
            'risk_pct': round(adjusted_risk_pct * 100, 3),
            'base_risk_pct': round(base_risk_pct * 100, 3),
            'factors': {
                'drawdown': round(drawdown_factor, 3),
                'loss_streak': round(loss_streak_factor, 3),
                'volatility': round(volatility_factor, 3),
                'regime': round(regime_factor, 3),
            },
            'kelly_criterion_used': bool(win_rate and avg_win and avg_loss)
        }
        
        logger.info(f"💰 Position Sizing: ${risk_amount:.2f} risk ({adjusted_risk_pct*100:.2f}%) = {contracts:.4f} contracts")
        logger.debug(f"   Factors: DD={drawdown_factor:.2f} | Streak={loss_streak_factor:.2f} | Vol={volatility_factor:.2f} | Regime={regime_factor:.2f}")
        
        return result
    
    def can_take_trade(self,
                       current_open_trades: List[Dict],
                       new_trade_risk_pct: float,
                       capital: float) -> Tuple[bool, str]:
        """
        Check if new trade is allowed based on portfolio risk limits
        
        Args:
            current_open_trades: List of currently open trades
            new_trade_risk_pct: Risk percentage of new trade
            capital: Current capital
            
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        # Calculate current total risk
        total_risk_pct = sum(trade.get('risk_pct', 0) for trade in current_open_trades)
        
        # Check if adding new trade exceeds max total risk
        if total_risk_pct + new_trade_risk_pct > self.max_total_risk_pct * 100:
            return False, f"⚠️ Max portfolio risk ({self.max_total_risk_pct*100:.1f}%) would be exceeded. Current: {total_risk_pct:.1f}%"
        
        # Check max open trades (optional, can be configured)
        max_open_trades = 5
        if len(current_open_trades) >= max_open_trades:
            return False, f"⚠️ Maximum {max_open_trades} open trades reached"
        
        return True, "✓ Trade allowed"


if __name__ == '__main__':
    # Test advanced risk manager
    print("\n🧪 Testing Advanced Risk Manager\n")
    
    manager = AdvancedRiskManager(
        base_risk_pct=0.01,
        kelly_fraction=0.25,
        atr_baseline=50.0
    )
    
    # Simulate trade history
    recent_trades = [
        {'pnl': 100},
        {'pnl': -50},
        {'pnl': 150},
        {'pnl': -60},
        {'pnl': -70},  # Start of losing streak
        {'pnl': -80},
        {'pnl': -40},
    ]
    
    # Test position sizing
    print("="*60)
    print("TEST 1: Normal Conditions")
    print("="*60)
    result = manager.calculate_optimal_position_size(
        capital=10000,
        entry_price=2000,
        stop_loss=1980,
        recent_trades=recent_trades[:4],  # Before losing streak
        current_atr=45.0,
        market_regime='TRENDING_UP',
        win_rate=0.60,
        avg_win=100,
        avg_loss=50
    )
    
    print(f"\nPosition Size: {result['position_size']:.2f}")
    print(f"Contracts: {result['contracts']:.4f}")
    print(f"Risk Amount: ${result['risk_amount']:.2f}")
    print(f"Risk %: {result['risk_pct']:.3f}%")
    print(f"Kelly Used: {result['kelly_criterion_used']}")
    print(f"Factors: {result['factors']}")
    
    # Test with losing streak
    print("\n" + "="*60)
    print("TEST 2: After Losing Streak + High Volatility")
    print("="*60)
    result2 = manager.calculate_optimal_position_size(
        capital=9000,  # Lost 1000
        entry_price=2000,
        stop_loss=1980,
        recent_trades=recent_trades,  # Includes losing streak
        current_atr=95.0,  # High volatility (2x baseline)
        market_regime='VOLATILE',
        win_rate=0.55,
        avg_win=90,
        avg_loss=60
    )
    
    print(f"\nPosition Size: {result2['position_size']:.2f}")
    print(f"Contracts: {result2['contracts']:.4f}")
    print(f"Risk Amount: ${result2['risk_amount']:.2f}")
    print(f"Risk %: {result2['risk_pct']:.3f}%")
    print(f"Factors: {result2['factors']}")
    
    # Test portfolio risk check
    print("\n" + "="*60)
    print("TEST 3: Portfolio Risk Limits")
    print("="*60)
    
    open_trades = [
        {'risk_pct': 2.5},
        {'risk_pct': 2.0},
        {'risk_pct': 1.5},
    ]
    
    can_trade, reason = manager.can_take_trade(open_trades, 3.0, 10000)
    print(f"Can take trade with 3% risk? {can_trade}")
    print(f"Reason: {reason}")
    
    can_trade2, reason2 = manager.can_take_trade(open_trades, 5.0, 10000)
    print(f"\nCan take trade with 5% risk? {can_trade2}")
    print(f"Reason: {reason2}")
    
    print("\n✅ Risk Manager Tests Complete\n")
