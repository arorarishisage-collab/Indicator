"""
Multi-Timeframe Analyzer - Confirm signals across multiple timeframes
Daily trend filter + 4H confirmation + 1H entry = Higher probability trades
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiTimeframeSignal:
    """Represents a signal confirmed across multiple timeframes"""
    
    def __init__(self, symbol: str, direction: int, strength: float, timeframes: Dict):
        self.symbol = symbol
        self.direction = direction  # 1 = BUY, -1 = SELL, 0 = NO SIGNAL
        self.strength = strength  # 0-10
        self.timeframes = timeframes  # {timeframe: signal_data}
        self.timestamp = datetime.now()
    
    def __repr__(self):
        return f"MTF Signal({self.symbol}, {self.direction}, strength={self.strength:.1f})"


class MultiTimeframeAnalyzer:
    """
    Analyze multiple timeframes to confirm trade signals
    
    Trading Rules:
    1. Daily timeframe sets the trend (only trade WITH the daily trend)
    2. 4H timeframe confirms the trend continuation
    3. 1H timeframe provides precise entry points
    4. ALL timeframes must agree for high-confidence signal
    """
    
    def __init__(self,
                 data_fetcher,
                 strategy_class,
                 timeframes: Optional[List[str]] = None,
                 require_all_aligned: bool = True):
        """
        Initialize multi-timeframe analyzer
        
        Args:
            data_fetcher: Data fetcher instance (YFinanceDataFetcher)
            strategy_class: Strategy class to apply (ICTStrategy or EMA30Strategy)
            timeframes: List of timeframes to analyze (default: ['1d', '4h', '1h'])
            require_all_aligned: If True, all timeframes must agree
        """
        self.data_fetcher = data_fetcher
        self.strategy_class = strategy_class
        self.timeframes = timeframes or ['1d', '4h', '1h']
        self.require_all_aligned = require_all_aligned
        
        # Timeframe hierarchy (largest to smallest)
        self.timeframe_hierarchy = {
            '1d': 3,
            '4h': 2,
            '1h': 1,
            '15m': 0,
            '5m': -1
        }
    
    def get_trend_direction(self, df: pd.DataFrame) -> Tuple[int, float]:
        """
        Determine trend direction from price action
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (direction: int, strength: float)
            direction: 1 = uptrend, -1 = downtrend, 0 = no trend
            strength: 0-10 (confidence in trend)
        """
        if len(df) < 50:
            return 0, 0.0
        
        # Calculate moving averages
        df = df.copy()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # Get latest values
        close = df['Close'].iloc[-1]
        sma_20 = df['SMA_20'].iloc[-1]
        sma_50 = df['SMA_50'].iloc[-1]
        
        # Calculate recent returns
        returns_10 = (close / df['Close'].iloc[-10] - 1) * 100
        returns_20 = (close / df['Close'].iloc[-20] - 1) * 100
        
        # Trend determination
        bullish_signals = 0
        bearish_signals = 0
        
        # Price above/below SMAs
        if close > sma_20:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if close > sma_50:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # SMA alignment
        if sma_20 > sma_50:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Recent performance
        if returns_10 > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if returns_20 > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # Determine direction and strength
        total_signals = bullish_signals + bearish_signals
        
        if bullish_signals >= 4:
            direction = 1
            strength = (bullish_signals / total_signals) * 10
        elif bearish_signals >= 4:
            direction = -1
            strength = (bearish_signals / total_signals) * 10
        else:
            direction = 0
            strength = 0.0
        
        return direction, strength
    
    def analyze_timeframe(self, symbol: str, timeframe: str, period: str) -> Dict:
        """
        Analyze a single timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe interval ('1d', '4h', '1h')
            period: Historical period to fetch ('1y', '6mo', '3mo')
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Fetch data
            df = self.data_fetcher.fetch_historical_data(
                symbol=symbol,
                period=period,
                interval=timeframe
            )
            
            if df is None or len(df) < 50:
                logger.warning(f"Insufficient data for {symbol} {timeframe}")
                return {
                    'timeframe': timeframe,
                    'signal': 0,
                    'strength': 0,
                    'trend_direction': 0,
                    'trend_strength': 0,
                    'error': 'Insufficient data'
                }
            
            # Get trend direction
            trend_direction, trend_strength = self.get_trend_direction(df)
            
            # Generate strategy signals
            strategy = self.strategy_class()
            df_signals = strategy.generate_signals(df.copy())
            
            # Get latest signal
            latest = df_signals.iloc[-1]
            signal = latest.get('Signal', 0)
            signal_strength = latest.get('Signal_Strength', 0)
            
            result = {
                'timeframe': timeframe,
                'signal': signal,
                'strength': signal_strength,
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'price': float(latest['Close']),
                'entry_price': float(latest.get('EntryPrice', latest['Close'])),
                'stop_loss': float(latest.get('StopLoss', 0)),
                'take_profit': float(latest.get('TakeProfit', 0)),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.debug(f"{timeframe}: Signal={signal}, Strength={signal_strength:.1f}, Trend={trend_direction}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} {timeframe}: {e}")
            return {
                'timeframe': timeframe,
                'signal': 0,
                'strength': 0,
                'trend_direction': 0,
                'trend_strength': 0,
                'error': str(e)
            }
    
    def analyze_multi_timeframe(self, symbol: str, verbose: bool = True) -> MultiTimeframeSignal:
        """
        Analyze all configured timeframes and generate multi-timeframe signal
        
        Args:
            symbol: Trading symbol
            verbose: Print detailed analysis
            
        Returns:
            MultiTimeframeSignal object
        """
        if verbose:
            logger.info(f"\n{'='*70}")
            logger.info(f"MULTI-TIMEFRAME ANALYSIS: {symbol}")
            logger.info(f"{'='*70}")
        
        # Period mapping for each timeframe
        period_map = {
            '1d': '1y',
            '4h': '6mo',
            '1h': '3mo',
            '15m': '1mo',
            '5m': '5d'
        }
        
        # Analyze each timeframe
        results = {}
        for tf in self.timeframes:
            period = period_map.get(tf, '1y')
            result = self.analyze_timeframe(symbol, tf, period)
            results[tf] = result
            
            if verbose:
                logger.info(f"\n  {tf.upper():4} | Signal: {result['signal']:+2} | "
                          f"Strength: {result['strength']:4.1f} | "
                          f"Trend: {result['trend_direction']:+2} ({result['trend_strength']:.1f})")
        
        # Determine final signal
        final_signal = self._compute_final_signal(results, verbose)
        
        if verbose:
            logger.info(f"\n{'='*70}")
            logger.info(f"FINAL SIGNAL: {final_signal.direction} (Strength: {final_signal.strength:.1f}/10)")
            logger.info(f"{'='*70}\n")
        
        return final_signal
    
    def _compute_final_signal(self, results: Dict, verbose: bool = False) -> MultiTimeframeSignal:
        """
        Compute final signal from multi-timeframe analysis
        
        Trading Logic:
        1. Daily must show clear trend (score >= 7)
        2. 4H must confirm daily trend
        3. 1H provides entry signal
        4. If require_all_aligned=True, all must agree
        """
        symbol = "UNKNOWN"
        
        # Extract signals by timeframe
        daily = results.get('1d', {})
        four_hour = results.get('4h', {})
        one_hour = results.get('1h', {})
        
        # Check daily trend (highest timeframe)
        daily_trend = daily.get('trend_direction', 0)
        daily_strength = daily.get('trend_strength', 0)
        
        if verbose:
            logger.info(f"\n  📊 Daily Trend: {daily_trend} (Strength: {daily_strength:.1f})")
        
        # If no clear daily trend, reduce confidence
        if abs(daily_trend) == 0 or daily_strength < 5:
            if verbose:
                logger.warning("  ⚠️ No clear daily trend - signal confidence reduced")
            
            # Still check for short-term alignment
            if self.require_all_aligned:
                return MultiTimeframeSignal(symbol, 0, 0.0, results)
        
        # Check 4H confirmation
        four_hour_signal = four_hour.get('signal', 0)
        four_hour_trend = four_hour.get('trend_direction', 0)
        
        # Check 1H entry
        one_hour_signal = one_hour.get('signal', 0)
        one_hour_strength = one_hour.get('strength', 0)
        
        # Alignment check
        signals = [daily_trend, four_hour_signal, one_hour_signal]
        signals = [s for s in signals if s != 0]  # Remove neutral signals
        
        if len(signals) == 0:
            return MultiTimeframeSignal(symbol, 0, 0.0, results)
        
        # Check if all agree
        if len(set(signals)) == 1:
            # Perfect alignment
            final_direction = signals[0]
            
            # Calculate combined strength
            strengths = [
                daily_strength,
                four_hour.get('strength', 0),
                one_hour_strength
            ]
            
            # Weighted average (daily has more weight)
            weights = [0.4, 0.3, 0.3]
            combined_strength = sum(s * w for s, w in zip(strengths, weights))
            
            if verbose:
                logger.info(f"  ✅ PERFECT ALIGNMENT - All timeframes agree ({final_direction})")
            
            return MultiTimeframeSignal(symbol, final_direction, combined_strength, results)
        
        elif self.require_all_aligned:
            # Not all aligned and strict mode
            if verbose:
                logger.warning(f"  ⚠️ CONFLICTING SIGNALS - Timeframes disagree: {signals}")
            
            return MultiTimeframeSignal(symbol, 0, 0.0, results)
        
        else:
            # Majority vote
            bullish_count = sum(1 for s in signals if s == 1)
            bearish_count = sum(1 for s in signals if s == -1)
            
            if bullish_count > bearish_count:
                final_direction = 1
                confidence = (bullish_count / len(signals)) * 10
            elif bearish_count > bullish_count:
                final_direction = -1
                confidence = (bearish_count / len(signals)) * 10
            else:
                final_direction = 0
                confidence = 0.0
            
            if verbose:
                logger.info(f"  ⚖️ MAJORITY VOTE - Direction: {final_direction}, Confidence: {confidence:.1f}")
            
            return MultiTimeframeSignal(symbol, final_direction, confidence, results)
    
    def get_trading_recommendation(self, mtf_signal: MultiTimeframeSignal) -> Tuple[bool, str]:
        """
        Get trading recommendation based on multi-timeframe signal
        
        Args:
            mtf_signal: MultiTimeframeSignal object
            
        Returns:
            Tuple of (should_trade: bool, reason: str)
        """
        if mtf_signal.direction == 0:
            return False, "⚠️ No clear direction across timeframes"
        
        if mtf_signal.strength < 5.0:
            return False, f"⚠️ Signal strength too low: {mtf_signal.strength:.1f}/10 (need >= 5.0)"
        
        # Check daily trend alignment
        daily = mtf_signal.timeframes.get('1d', {})
        daily_trend = daily.get('trend_direction', 0)
        
        if daily_trend != 0 and daily_trend != mtf_signal.direction:
            return False, f"⚠️ Trading against daily trend ({daily_trend} vs {mtf_signal.direction})"
        
        # All checks passed
        direction_str = "BUY" if mtf_signal.direction == 1 else "SELL"
        return True, f"✅ {direction_str} signal confirmed across timeframes (Strength: {mtf_signal.strength:.1f}/10)"


if __name__ == '__main__':
    # Test multi-timeframe analyzer
    print("\n🧪 Testing Multi-Timeframe Analyzer\n")
    
    from data_fetch_yfinance import YFinanceDataFetcher
    from ict_strategy import ICTStrategy
    
    fetcher = YFinanceDataFetcher()
    
    # Test on gold
    print("="*70)
    print("TESTING ON GOLD (GC=F) with ICT Strategy")
    print("="*70)
    
    analyzer = MultiTimeframeAnalyzer(
        data_fetcher=fetcher,
        strategy_class=ICTStrategy,
        timeframes=['1d', '4h', '1h'],
        require_all_aligned=True
    )
    
    mtf_signal = analyzer.analyze_multi_timeframe('GC=F', verbose=True)
    
    should_trade, reason = analyzer.get_trading_recommendation(mtf_signal)
    print(f"\n🎯 RECOMMENDATION:")
    print(f"   Should Trade: {should_trade}")
    print(f"   Reason: {reason}\n")
    
    # Display detailed signal info
    print(f"📋 SIGNAL DETAILS:")
    print(f"   Direction: {'BUY' if mtf_signal.direction == 1 else 'SELL' if mtf_signal.direction == -1 else 'NEUTRAL'}")
    print(f"   Strength: {mtf_signal.strength:.2f}/10")
    print(f"   Timestamp: {mtf_signal.timestamp}")
    
    print("\n" + "="*70)
    print("TIMEFRAME BREAKDOWN:")
    print("="*70)
    for tf, data in mtf_signal.timeframes.items():
        print(f"\n{tf.upper()}:")
        print(f"  Signal: {data.get('signal', 0)}")
        print(f"  Strength: {data.get('strength', 0):.1f}")
        print(f"  Trend: {data.get('trend_direction', 0)} ({data.get('trend_strength', 0):.1f})")
        print(f"  Price: ${data.get('price', 0):.2f}")
