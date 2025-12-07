"""
Technical Indicators - Professional-grade indicator calculations
Includes SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ADX, and more
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Collection of professional technical indicators for strategy implementation
    All indicators add columns to the DataFrame without modifying original data
    """
    
    @staticmethod
    def sma(df: pd.DataFrame, column: str = 'Close', period: int = 20, 
            name: str = None) -> pd.DataFrame:
        """
        Simple Moving Average
        
        Args:
            df: DataFrame with OHLCV data
            column: Column to calculate SMA on (default: Close)
            period: Period for SMA
            name: Custom column name
        
        Returns:
            DataFrame with SMA added
        """
        col_name = name or f'SMA_{period}'
        df[col_name] = df[column].rolling(window=period).mean()
        return df
    
    @staticmethod
    def ema(df: pd.DataFrame, column: str = 'Close', period: int = 20,
            name: str = None) -> pd.DataFrame:
        """
        Exponential Moving Average
        
        Args:
            df: DataFrame with OHLCV data
            column: Column to calculate EMA on
            period: Period for EMA
            name: Custom column name
        
        Returns:
            DataFrame with EMA added
        """
        col_name = name or f'EMA_{period}'
        df[col_name] = df[column].ewm(span=period, adjust=False).mean()
        return df
    
    @staticmethod
    def wma(df: pd.DataFrame, column: str = 'Close', period: int = 30,
            name: str = None) -> pd.DataFrame:
        """Weighted Moving Average with more weight on recent candles."""
        col_name = name or f'WMA_{period}'
        weights = np.arange(1, period + 1)
        df[col_name] = df[column].rolling(window=period).apply(
            lambda values: np.dot(values, weights) / weights.sum(),
            raw=True
        )
        return df

    @staticmethod
    def rsi(df: pd.DataFrame, column: str = 'Close', period: int = 14,
            name: str = None) -> pd.DataFrame:
        """
        Relative Strength Index (0-100)
        RSI > 70: Overbought
        RSI < 30: Oversold
        
        Args:
            df: DataFrame with OHLCV data
            column: Column to calculate RSI on
            period: Period for RSI
            name: Custom column name
        
        Returns:
            DataFrame with RSI added
        """
        col_name = name or f'RSI_{period}'
        
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        df[col_name] = 100 - (100 / (1 + rs))
        
        return df
    
    @staticmethod
    def macd(df: pd.DataFrame, column: str = 'Close', fast: int = 12, 
             slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        MACD (Moving Average Convergence Divergence)
        
        Returns 3 columns:
        - MACD_Line: 12-period EMA - 26-period EMA
        - Signal_Line: 9-period EMA of MACD
        - MACD_Histogram: MACD - Signal
        
        Args:
            df: DataFrame with OHLCV data
            column: Column to calculate MACD on
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
        
        Returns:
            DataFrame with MACD columns added
        """
        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()
        
        df['MACD_Line'] = ema_fast - ema_slow
        df['Signal_Line'] = df['MACD_Line'].ewm(span=signal, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD_Line'] - df['Signal_Line']
        
        return df
    
    @staticmethod
    def bollinger_bands(df: pd.DataFrame, column: str = 'Close', period: int = 20,
                       std_dev: float = 2.0) -> pd.DataFrame:
        """
        Bollinger Bands
        
        Returns 3 columns:
        - BB_Upper: Upper band
        - BB_Middle: Moving average (middle band)
        - BB_Lower: Lower band
        - BB_Width: Bandwidth (Upper - Lower)
        - BB_Position: (Close - Lower) / (Upper - Lower)  [0-1 scale]
        
        Args:
            df: DataFrame with OHLCV data
            column: Column to calculate BB on
            period: Period for moving average
            std_dev: Number of standard deviations
        
        Returns:
            DataFrame with Bollinger Bands added
        """
        sma = df[column].rolling(window=period).mean()
        std = df[column].rolling(window=period).std()
        
        df['BB_Upper'] = sma + (std * std_dev)
        df['BB_Middle'] = sma
        df['BB_Lower'] = sma - (std * std_dev)
        df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
        
        # BB Position (0 = lower band, 1 = upper band)
        df['BB_Position'] = (df[column] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        df['BB_Position'] = df['BB_Position'].clip(0, 1)
        
        return df
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14, name: str = None) -> pd.DataFrame:
        """
        Average True Range (volatility indicator)
        
        Args:
            df: DataFrame with OHLCV data
            period: Period for ATR
            name: Custom column name
        
        Returns:
            DataFrame with ATR added
        """
        col_name = name or f'ATR_{period}'
        
        # True Range
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        df[col_name] = true_range.rolling(period).mean()
        
        return df
    
    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Average Directional Index (trend strength)
        ADX > 25: Strong trend
        ADX < 20: Weak trend
        
        Args:
            df: DataFrame with OHLCV data
            period: Period for ADX
        
        Returns:
            DataFrame with ADX, +DI, -DI added
        """
        # Calculate True Range
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        tr = ranges.max(axis=1)
        atr = tr.rolling(period).mean()
        
        # Positive and Negative Directional Indicators
        pos_dm = df['High'].diff()
        neg_dm = -df['Low'].diff()
        
        pos_dm[pos_dm < 0] = 0
        neg_dm[neg_dm < 0] = 0
        
        pos_di = 100 * (pos_dm.rolling(period).mean() / atr)
        neg_di = 100 * (neg_dm.rolling(period).mean() / atr)
        
        di_diff = abs(pos_di - neg_di)
        di_sum = pos_di + neg_di
        
        dx = 100 * (di_diff / di_sum)
        adx = dx.rolling(period).mean()
        
        df['+DI'] = pos_di
        df['-DI'] = neg_di
        df['ADX'] = adx
        
        return df
    
    @staticmethod
    def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """
        Stochastic Oscillator (0-100)
        %K > 80: Overbought
        %K < 20: Oversold
        
        Args:
            df: DataFrame with OHLCV data
            k_period: Period for %K calculation
            d_period: Period for %D (signal line)
        
        Returns:
            DataFrame with Stoch_%K and Stoch_%D added
        """
        low_min = df['Low'].rolling(window=k_period).min()
        high_max = df['High'].rolling(window=k_period).max()
        
        df['Stoch_%K'] = 100 * ((df['Close'] - low_min) / (high_max - low_min))
        df['Stoch_%D'] = df['Stoch_%K'].rolling(window=d_period).mean()
        
        return df
    
    @staticmethod
    def roc(df: pd.DataFrame, column: str = 'Close', period: int = 12,
            name: str = None) -> pd.DataFrame:
        """
        Rate of Change (momentum)
        
        Args:
            df: DataFrame with OHLCV data
            column: Column to calculate ROC on
            period: Period for ROC
            name: Custom column name
        
        Returns:
            DataFrame with ROC added
        """
        col_name = name or f'ROC_{period}'
        df[col_name] = ((df[column] - df[column].shift(period)) / df[column].shift(period)) * 100
        return df
    
    @staticmethod
    def obv(df: pd.DataFrame, name: str = None) -> pd.DataFrame:
        """
        On-Balance Volume (volume momentum)
        
        Args:
            df: DataFrame with OHLCV data
            name: Custom column name
        
        Returns:
            DataFrame with OBV added
        """
        col_name = name or 'OBV'
        
        obv = [0]
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i - 1]:
                obv.append(obv[-1] + df['Volume'].iloc[i])
            elif df['Close'].iloc[i] < df['Close'].iloc[i - 1]:
                obv.append(obv[-1] - df['Volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        df[col_name] = obv
        return df
    
    @staticmethod
    def calculate_indicators(df: pd.DataFrame, indicators_config: Dict) -> pd.DataFrame:
        """
        Calculate multiple indicators based on configuration
        
        Args:
            df: DataFrame with OHLCV data
            indicators_config: Dict with indicator names and parameters
                Example: {
                    'SMA_20': {'type': 'sma', 'period': 20},
                    'RSI_14': {'type': 'rsi', 'period': 14},
                    'MACD': {'type': 'macd'},
                    'BB_20': {'type': 'bollinger_bands', 'period': 20}
                }
        
        Returns:
            DataFrame with all indicators added
        """
        df = df.copy()
        
        for ind_name, config in indicators_config.items():
            ind_type = config.get('type')
            
            try:
                if ind_type == 'sma':
                    df = TechnicalIndicators.sma(
                        df, 
                        column=config.get('column', 'Close'),
                        period=config.get('period', 20),
                        name=ind_name
                    )
                
                elif ind_type == 'ema':
                    df = TechnicalIndicators.ema(
                        df,
                        column=config.get('column', 'Close'),
                        period=config.get('period', 20),
                        name=ind_name
                    )
                
                elif ind_type == 'rsi':
                    df = TechnicalIndicators.rsi(
                        df,
                        column=config.get('column', 'Close'),
                        period=config.get('period', 14),
                        name=ind_name
                    )
                
                elif ind_type == 'macd':
                    df = TechnicalIndicators.macd(
                        df,
                        column=config.get('column', 'Close'),
                        fast=config.get('fast', 12),
                        slow=config.get('slow', 26),
                        signal=config.get('signal', 9)
                    )
                
                elif ind_type == 'bollinger_bands':
                    df = TechnicalIndicators.bollinger_bands(
                        df,
                        column=config.get('column', 'Close'),
                        period=config.get('period', 20),
                        std_dev=config.get('std_dev', 2.0)
                    )
                
                elif ind_type == 'atr':
                    df = TechnicalIndicators.atr(
                        df,
                        period=config.get('period', 14),
                        name=ind_name
                    )
                
                elif ind_type == 'adx':
                    df = TechnicalIndicators.adx(
                        df,
                        period=config.get('period', 14)
                    )
                
                elif ind_type == 'stochastic':
                    df = TechnicalIndicators.stochastic(
                        df,
                        k_period=config.get('k_period', 14),
                        d_period=config.get('d_period', 3)
                    )
                
                elif ind_type == 'roc':
                    df = TechnicalIndicators.roc(
                        df,
                        column=config.get('column', 'Close'),
                        period=config.get('period', 12),
                        name=ind_name
                    )
                
                elif ind_type == 'obv':
                    df = TechnicalIndicators.obv(
                        df,
                        name=ind_name
                    )
                
                logger.info(f"✓ Added {ind_name}")
            
            except Exception as e:
                logger.error(f"Error calculating {ind_name}: {e}")
        
        return df


# Quick access functions
def add_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Quick SMA"""
    return TechnicalIndicators.sma(df, period=period)

def add_ema(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Quick EMA"""
    return TechnicalIndicators.ema(df, period=period)

def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Quick RSI"""
    return TechnicalIndicators.rsi(df, period=period)

def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    """Quick MACD"""
    return TechnicalIndicators.macd(df)

def add_bollinger_bands(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Quick Bollinger Bands"""
    return TechnicalIndicators.bollinger_bands(df, period=period)

def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Quick ATR"""
    return TechnicalIndicators.atr(df, period=period)

def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Quick ADX"""
    return TechnicalIndicators.adx(df, period=period)

def add_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
    """Quick Stochastic"""
    return TechnicalIndicators.stochastic(df, k_period, d_period)
