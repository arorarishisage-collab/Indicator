"""
Market Regime Detector - Identifies market conditions to filter trades
Detects: TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, CHOPPY
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketRegime:
    """Market regime classification"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    CHOPPY = "CHOPPY"
    UNKNOWN = "UNKNOWN"


class MarketRegimeDetector:
    """
    Detects market regime using multiple technical indicators:
    - ADX (Average Directional Index) for trend strength
    - ATR (Average True Range) for volatility
    - Price action for trend direction
    - Efficiency Ratio for choppiness
    """
    
    def __init__(self, 
                 adx_period: int = 14,
                 adx_trending_threshold: float = 25.0,
                 adx_strong_trending_threshold: float = 40.0,
                 atr_period: int = 14,
                 atr_percentile_threshold: float = 70.0,
                 efficiency_period: int = 20,
                 efficiency_choppy_threshold: float = 0.3):
        """
        Initialize regime detector
        
        Args:
            adx_period: Period for ADX calculation
            adx_trending_threshold: ADX above this = trending market (default 25)
            adx_strong_trending_threshold: ADX above this = strong trend (default 40)
            atr_period: Period for ATR calculation
            atr_percentile_threshold: ATR percentile for high volatility (default 70%)
            efficiency_period: Period for efficiency ratio
            efficiency_choppy_threshold: Efficiency below this = choppy market
        """
        self.adx_period = adx_period
        self.adx_trending = adx_trending_threshold
        self.adx_strong_trending = adx_strong_trending_threshold
        self.atr_period = atr_period
        self.atr_percentile = atr_percentile_threshold
        self.efficiency_period = efficiency_period
        self.efficiency_choppy = efficiency_choppy_threshold
    
    def calculate_adx(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Average Directional Index (ADX)
        Measures trend strength (0-100, higher = stronger trend)
        """
        df = df.copy()
        
        # Calculate True Range
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        up_move = df['High'] - df['High'].shift()
        down_move = df['Low'].shift() - df['Low']
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smooth with Wilder's smoothing (exponential moving average)
        atr = tr.ewm(span=self.adx_period, adjust=False).mean()
        plus_di = 100 * pd.Series(plus_dm).ewm(span=self.adx_period, adjust=False).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).ewm(span=self.adx_period, adjust=False).mean() / atr
        
        # Calculate ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=self.adx_period, adjust=False).mean()
        
        df['ADX'] = adx
        df['PLUS_DI'] = plus_di
        df['MINUS_DI'] = minus_di
        
        return df
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Average True Range (ATR) - measures volatility"""
        df = df.copy()
        
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()
        
        df['ATR'] = atr
        df['ATR_Percent'] = (atr / df['Close']) * 100
        
        return df
    
    def calculate_efficiency_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Efficiency Ratio (Kaufman's Adaptive MA)
        Measures price movement efficiency
        High ER = efficient trending move
        Low ER = choppy, inefficient price action
        """
        df = df.copy()
        
        # Net price change over period
        net_change = np.abs(df['Close'] - df['Close'].shift(self.efficiency_period))
        
        # Sum of absolute bar-to-bar changes
        bar_changes = np.abs(df['Close'] - df['Close'].shift())
        sum_changes = bar_changes.rolling(window=self.efficiency_period).sum()
        
        # Efficiency Ratio = net change / sum of changes
        er = net_change / sum_changes
        er = er.fillna(0)
        
        df['Efficiency_Ratio'] = er
        
        return df
    
    def calculate_trend_direction(self, df: pd.DataFrame, period: int = 50) -> pd.DataFrame:
        """Calculate trend direction using moving averages"""
        df = df.copy()
        
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # Trend score: +1 for bullish, -1 for bearish indicators
        trend_score = 0
        
        # Price above/below SMAs
        if len(df) > 20:
            if df['Close'].iloc[-1] > df['SMA_20'].iloc[-1]:
                trend_score += 1
            else:
                trend_score -= 1
        
        if len(df) > 50:
            if df['Close'].iloc[-1] > df['SMA_50'].iloc[-1]:
                trend_score += 1
            else:
                trend_score -= 1
        
        if len(df) > 200:
            if df['Close'].iloc[-1] > df['SMA_200'].iloc[-1]:
                trend_score += 1
            else:
                trend_score -= 1
        
        # SMA alignment
        if len(df) > 50:
            if df['SMA_20'].iloc[-1] > df['SMA_50'].iloc[-1]:
                trend_score += 1
            else:
                trend_score -= 1
        
        df['Trend_Score'] = trend_score
        
        return df
    
    def detect_regime(self, df: pd.DataFrame, verbose: bool = False) -> Tuple[str, Dict]:
        """
        Detect current market regime
        
        Args:
            df: DataFrame with OHLCV data
            verbose: Print detailed analysis
            
        Returns:
            Tuple of (regime_name, metrics_dict)
        """
        if len(df) < max(self.adx_period, self.atr_period, self.efficiency_period, 200):
            return MarketRegime.UNKNOWN, {'error': 'Insufficient data'}
        
        # Calculate indicators
        df = self.calculate_adx(df)
        df = self.calculate_atr(df)
        df = self.calculate_efficiency_ratio(df)
        df = self.calculate_trend_direction(df)
        
        # Get latest values
        latest = df.iloc[-1]
        adx = latest['ADX']
        plus_di = latest['PLUS_DI']
        minus_di = latest['MINUS_DI']
        atr_pct = latest['ATR_Percent']
        efficiency = latest['Efficiency_Ratio']
        trend_score = latest['Trend_Score']
        
        # Calculate ATR percentile (last 100 bars)
        atr_percentile = (df['ATR'].iloc[-100:] < latest['ATR']).sum() / 100 * 100
        
        metrics = {
            'adx': round(adx, 2),
            'plus_di': round(plus_di, 2),
            'minus_di': round(minus_di, 2),
            'atr_percent': round(atr_pct, 4),
            'atr_percentile': round(atr_percentile, 2),
            'efficiency_ratio': round(efficiency, 3),
            'trend_score': int(trend_score),
            'price': round(latest['Close'], 2)
        }
        
        # Regime detection logic
        regime = MarketRegime.UNKNOWN
        
        # 1. Check for CHOPPY market (low efficiency, low ADX)
        if efficiency < self.efficiency_choppy and adx < self.adx_trending:
            regime = MarketRegime.CHOPPY
        
        # 2. Check for HIGH VOLATILITY
        elif atr_percentile > self.atr_percentile:
            regime = MarketRegime.VOLATILE
        
        # 3. Check for RANGING market (low ADX, moderate efficiency)
        elif adx < self.adx_trending:
            regime = MarketRegime.RANGING
        
        # 4. Check for TRENDING markets (high ADX)
        elif adx >= self.adx_trending:
            # Determine trend direction
            if plus_di > minus_di and trend_score >= 2:
                regime = MarketRegime.TRENDING_UP
            elif minus_di > plus_di and trend_score <= -2:
                regime = MarketRegime.TRENDING_DOWN
            else:
                # ADX high but direction unclear = ranging/transitioning
                regime = MarketRegime.RANGING
        
        metrics['regime'] = regime
        
        if verbose:
            logger.info(f"\n{'='*60}")
            logger.info(f"MARKET REGIME ANALYSIS")
            logger.info(f"{'='*60}")
            logger.info(f"  Regime:           {regime}")
            logger.info(f"  ADX:              {adx:.2f} (Trending if > {self.adx_trending})")
            logger.info(f"  +DI / -DI:        {plus_di:.2f} / {minus_di:.2f}")
            logger.info(f"  ATR %:            {atr_pct:.4f}%")
            logger.info(f"  ATR Percentile:   {atr_percentile:.1f}% (High vol if > {self.atr_percentile}%)")
            logger.info(f"  Efficiency:       {efficiency:.3f} (Choppy if < {self.efficiency_choppy})")
            logger.info(f"  Trend Score:      {trend_score}/4")
            logger.info(f"{'='*60}\n")
        
        return regime, metrics
    
    def should_trade(self, regime: str, strategy_type: str = 'trend_following') -> Tuple[bool, str]:
        """
        Determine if trading is recommended in current regime
        
        Args:
            regime: Current market regime
            strategy_type: 'trend_following', 'mean_reversion', or 'both'
            
        Returns:
            Tuple of (should_trade, reason)
        """
        if strategy_type == 'trend_following':
            # ICT and EMA30 are trend-following strategies
            if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                return True, f"✓ Trend-following optimal in {regime}"
            elif regime == MarketRegime.RANGING:
                return False, "⚠ Ranging market - trend strategies generate false signals"
            elif regime == MarketRegime.CHOPPY:
                return False, "⚠ Choppy market - high risk of whipsaws"
            elif regime == MarketRegime.VOLATILE:
                return False, "⚠ High volatility - stop losses likely to be hit"
            else:
                return False, f"⚠ Unknown regime - insufficient data"
        
        elif strategy_type == 'mean_reversion':
            if regime == MarketRegime.RANGING:
                return True, "✓ Mean reversion optimal in ranging market"
            elif regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                return False, f"⚠ Strong trend - mean reversion risky in {regime}"
            else:
                return False, f"⚠ {regime} - not suitable for mean reversion"
        
        else:  # both
            if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, MarketRegime.RANGING]:
                return True, f"✓ {regime} - tradeable with appropriate strategy"
            else:
                return False, f"⚠ {regime} - avoid trading"
    
    def get_regime_trading_advice(self, regime: str, metrics: Dict) -> str:
        """Get detailed trading advice for current regime"""
        advice = f"\n🎯 REGIME: {regime}\n\n"
        
        if regime == MarketRegime.TRENDING_UP:
            advice += "📈 STRONG UPTREND - Best Conditions\n"
            advice += "  ✓ Use ICT Strategy (order blocks, FVG)\n"
            advice += "  ✓ Use EMA30 Strategy (9 EMA above 30 WMA)\n"
            advice += "  ✓ Look for pullbacks to support levels\n"
            advice += "  ✓ Trail stops aggressively\n"
            advice += "  ⚠ Avoid counter-trend shorts\n"
        
        elif regime == MarketRegime.TRENDING_DOWN:
            advice += "📉 STRONG DOWNTREND - Best Conditions\n"
            advice += "  ✓ Use ICT Strategy (bearish order blocks)\n"
            advice += "  ✓ Use EMA30 Strategy (9 EMA below 30 WMA)\n"
            advice += "  ✓ Look for rallies to resistance levels\n"
            advice += "  ✓ Trail stops aggressively\n"
            advice += "  ⚠ Avoid counter-trend longs\n"
        
        elif regime == MarketRegime.RANGING:
            advice += "↔️ RANGING MARKET - Moderate Conditions\n"
            advice += "  ⚠ Trend strategies may generate false signals\n"
            advice += "  ✓ Trade support/resistance bounces\n"
            advice += "  ✓ Use tighter stops\n"
            advice += "  ✓ Take profits quickly\n"
            advice += "  ⚠ Reduce position size by 50%\n"
        
        elif regime == MarketRegime.VOLATILE:
            advice += "⚡ HIGH VOLATILITY - Dangerous Conditions\n"
            advice += "  ⚠ REDUCE POSITION SIZE by 50-75%\n"
            advice += "  ⚠ Use wider stops (2x ATR instead of 1.5x)\n"
            advice += "  ⚠ Avoid trading if possible\n"
            advice += "  ✓ Wait for volatility to normalize\n"
            advice += f"  📊 ATR at {metrics.get('atr_percentile', 0):.0f}th percentile\n"
        
        elif regime == MarketRegime.CHOPPY:
            advice += "🌊 CHOPPY MARKET - Avoid Trading\n"
            advice += "  ❌ NO CLEAR DIRECTION\n"
            advice += "  ❌ High risk of whipsaws\n"
            advice += "  ❌ Stop losses will be hit repeatedly\n"
            advice += "  ✓ STAY OUT - preserve capital\n"
            advice += f"  📊 Efficiency Ratio: {metrics.get('efficiency_ratio', 0):.3f} (very low)\n"
        
        else:
            advice += "❓ UNKNOWN - Insufficient Data\n"
            advice += "  ⚠ Wait for more data\n"
        
        return advice


if __name__ == '__main__':
    # Test regime detector
    print("\n🧪 Testing Market Regime Detector\n")
    
    from data_fetch_yfinance import YFinanceDataFetcher
    
    fetcher = YFinanceDataFetcher()
    
    # Test on gold
    print("="*60)
    print("TESTING ON GOLD (GC=F)")
    print("="*60)
    df_gold = fetcher.fetch_historical_data('GC=F', period='1y', interval='1d')
    
    detector = MarketRegimeDetector()
    regime, metrics = detector.detect_regime(df_gold, verbose=True)
    
    should_trade, reason = detector.should_trade(regime, strategy_type='trend_following')
    print(f"Should Trade: {should_trade}")
    print(f"Reason: {reason}\n")
    
    advice = detector.get_regime_trading_advice(regime, metrics)
    print(advice)
    
    # Test on Nifty
    print("\n" + "="*60)
    print("TESTING ON NIFTY 50 (^NSEI)")
    print("="*60)
    df_nifty = fetcher.fetch_historical_data('^NSEI', period='1y', interval='1d')
    
    regime_nifty, metrics_nifty = detector.detect_regime(df_nifty, verbose=True)
    should_trade_nifty, reason_nifty = detector.should_trade(regime_nifty, strategy_type='trend_following')
    print(f"Should Trade: {should_trade_nifty}")
    print(f"Reason: {reason_nifty}\n")
    
    advice_nifty = detector.get_regime_trading_advice(regime_nifty, metrics_nifty)
    print(advice_nifty)
