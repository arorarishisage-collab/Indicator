"""
Comprehensive ICT (Inner Circle Trader) Strategy Implementation
Covers: Order blocks, Liquidity voids, Smart money concepts, Supply/Demand zones, Fair value gaps
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ICTStrategy:
    """
    ICT Strategy based on Smart Money concepts:
    1. Order Blocks - Areas where institutions accumulated/distributed
    2. Liquidity Voids - Gaps in price action where liquidity was swept
    3. Fair Value Gaps - Imbalances in price (fast moving candles)
    4. Supply/Demand Zones - Key levels of institutional trading
    5. Break of Structure (BoS) - Change in directional bias
    """
    
    def __init__(self, lookback_period=200, fvg_threshold=0.0005, ob_threshold=2,
                 confluence_weights=None, min_bull_score=4.0, min_bear_score=4.0,
                 strength_divisor=1.5):
        """
        Initialize ICT Strategy
        
        Args:
            lookback_period (int): Period for zone calculation
            fvg_threshold (float): Fair Value Gap threshold (% of price)
            ob_threshold (int): Order Block confirmation candles
        """
        self.lookback_period = lookback_period
        self.fvg_threshold = fvg_threshold
        self.ob_threshold = ob_threshold
        self.confluence_weights = confluence_weights or {
            'order_block': 2.0,
            'fvg': 1.5,
            'demand_zone': 1.5,
            'supply_zone': 1.5,
            'bos': 2.5,
            'liquidity_void': 1.0,
            'htf_trend': 1.0,
        }
        self.min_bull_score = min_bull_score
        self.min_bear_score = min_bear_score
        self.strength_divisor = strength_divisor
        self.name = 'ICTStrategy'
    
    def identify_order_blocks(self, df, lookback=50):
        """
        Identify Order Blocks (accumulation/distribution zones)
        Order Block = Strong impulsive candle followed by retracement
        
        Args:
            df (pd.DataFrame): OHLCV data
            lookback (int): Period to look back
            
        Returns:
            pd.DataFrame: DataFrame with order block markers
        """
        df = df.copy()
        df['OB_BULLISH'] = False
        df['OB_BEARISH'] = False
        
        for i in range(lookback, len(df) - 1):
            if i <= 0:
                continue

            idx = df.index[i]
            idx_prev = df.index[i - 1]
            idx_next = df.index[i + 1] if i + 1 < len(df) else None

            # Helper to read either MultiIndex or flat column
            def _get(col_name: str, row_idx):
                if (col_name, 'GC=F') in df.columns:
                    return float(df.loc[row_idx, (col_name, 'GC=F')])
                return float(df.loc[row_idx, col_name])

            close_i = _get('Close', idx)
            open_i = _get('Open', idx)
            close_prev = _get('Close', idx_prev)
            open_prev = _get('Open', idx_prev)

            # Bullish Order Block
            body_range = close_i - open_i
            prev_body = close_prev - open_prev
            is_strong_bull = (body_range > 0) and (body_range > prev_body * 1.5)

            if is_strong_bull and idx_next is not None:
                close_next = _get('Close', idx_next)
                if close_next < close_i:
                    print(f"DEBUG OB_BULLISH assignment: i={i}, value=True")
                    df.loc[idx, 'OB_BULLISH'] = True
                    print(f"DEBUG OB_BUY_LEVEL assignment: i={i}, value={_get('Low', idx)}")
                    df.loc[idx, 'OB_BUY_LEVEL'] = _get('Low', idx)

            # Bearish Order Block
            body_range = open_i - close_i
            prev_body = open_prev - close_prev
            is_strong_bear = (body_range > 0) and (body_range > prev_body * 1.5)

            if is_strong_bear and idx_next is not None:
                close_next = _get('Close', idx_next)
                if close_next > close_i:
                    print(f"DEBUG OB_BEARISH assignment: i={i}, value=True")
                    df.loc[idx, 'OB_BEARISH'] = True
                    print(f"DEBUG OB_SELL_LEVEL assignment: i={i}, value={_get('High', idx)}")
                    df.loc[idx, 'OB_SELL_LEVEL'] = _get('High', idx)
        
        return df
    
    def identify_fair_value_gaps(self, df):
        """
        Identify Fair Value Gaps (FVG) - Imbalances in price movement
        
        FVG occurs when:
        - Bullish FVG: High of candle 1 < Low of candle 3 (gap up with candle 2 in between)
        - Bearish FVG: Low of candle 1 > High of candle 3 (gap down with candle 2 in between)
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with FVG markers
        """
        df = df.copy()
        df['FVG_BULLISH'] = False
        df['FVG_BEARISH'] = False
        df['FVG_LEVEL'] = np.nan
        
        for i in range(2, len(df)):
            # Bullish FVG: fast move up leaving imbalance
            if df.iloc[i]['Low'] > df.iloc[i-2]['High']:
                df.loc[df.index[i], 'FVG_BULLISH'] = True
                df.loc[df.index[i], 'FVG_LEVEL'] = (df.iloc[i-2]['High'] + df.iloc[i]['Low']) / 2
            
            # Bearish FVG: fast move down leaving imbalance
            if df.iloc[i]['High'] < df.iloc[i-2]['Low']:
                df.loc[df.index[i], 'FVG_BEARISH'] = True
                df.loc[df.index[i], 'FVG_LEVEL'] = (df.iloc[i-2]['Low'] + df.iloc[i]['High']) / 2
        
        return df
    
    def identify_liquidity_voids(self, df, lookback=100):
        """
        Identify Liquidity Voids - Areas where price likely swept liquidity
        Often appears as wicks that don't have much trading activity
        
        Args:
            df (pd.DataFrame): OHLCV data
            lookback (int): Period to look back
            
        Returns:
            pd.DataFrame: DataFrame with liquidity void markers
        """
        df = df.copy()
        df['LIQUIDITY_VOID'] = False
        df['VOID_LEVEL'] = np.nan
        
        # Find recent highs and lows (last N periods)
        if len(df) >= lookback:
            recent_high = df['High'].iloc[-lookback:].max()
            recent_low = df['Low'].iloc[-lookback:].min()
            
            # Long wicks without volume indicate liquidity voids
            for i in range(len(df)):
                wick_range = (df.iloc[i]['High'] - df.iloc[i]['Low']) / df.iloc[i]['Close']
                body_range = abs(df.iloc[i]['Close'] - df.iloc[i]['Open']) / df.iloc[i]['Close']
                volume_ratio = df.iloc[i]['Volume'] / df['Volume'].mean()
                
                # High wick, low body, low volume = liquidity void
                if (wick_range > body_range * 2) and (volume_ratio < 1):
                    df.loc[df.index[i], 'LIQUIDITY_VOID'] = True
                    df.loc[df.index[i], 'VOID_LEVEL'] = df.iloc[i]['High'] if df.iloc[i]['High'] > df.iloc[i]['Close'] else df.iloc[i]['Low']
        
        return df
    
    def identify_supply_demand_zones(self, df, window=20):
        """
        Identify Supply (Resistance) and Demand (Support) Zones
        Based on where price has rejected multiple times
        
        Args:
            df (pd.DataFrame): OHLCV data
            window (int): Period for zone identification
            
        Returns:
            pd.DataFrame: DataFrame with supply/demand zones
        """
        df = df.copy()
        df['DEMAND_ZONE'] = False
        df['SUPPLY_ZONE'] = False
        df['ZONE_LEVEL'] = np.nan
        df['ZONE_STRENGTH'] = 0
        
        for i in range(window, len(df)):
            window_data = df.iloc[i-window:i]
            
            # Find local support (demand zone)
            if i > 0:
                local_low = window_data['Low'].min()
                local_high = window_data['High'].max()
                
                # If price is near low and bounces multiple times
                reversals = 0
                for j in range(len(window_data) - 1):
                    low_val = float(window_data.at[window_data.index[j], 'Low'])
                    close_j_plus_1 = float(window_data.at[window_data.index[j+1], 'Close'])
                    open_j = float(window_data.at[window_data.index[j], 'Open'])
                    if low_val < local_low * 1.01 and close_j_plus_1 > open_j:
                        reversals += 1
                
                if reversals >= 2:
                    df.loc[df.index[i], 'DEMAND_ZONE'] = True
                    df.loc[df.index[i], 'ZONE_LEVEL'] = local_low
                    df.loc[df.index[i], 'ZONE_STRENGTH'] = reversals
                
                # Find local resistance (supply zone)
                reversals = 0
                for j in range(len(window_data) - 1):
                    high_val = float(window_data.at[window_data.index[j], 'High'])
                    close_j_plus_1 = float(window_data.at[window_data.index[j+1], 'Close'])
                    open_j = float(window_data.at[window_data.index[j], 'Open'])
                    if high_val > local_high * 0.99 and close_j_plus_1 < open_j:
                        reversals += 1
                
                if reversals >= 2:
                    df.loc[df.index[i], 'SUPPLY_ZONE'] = True
                    df.loc[df.index[i], 'ZONE_LEVEL'] = local_high
                    df.loc[df.index[i], 'ZONE_STRENGTH'] = reversals
        
        return df
    
    def identify_break_of_structure(self, df, window=5):
        """
        Identify Break of Structure (BoS) - Change in directional bias
        Bullish BoS: Price breaks above previous resistance
        Bearish BoS: Price breaks below previous support
        
        Args:
            df (pd.DataFrame): OHLCV data
            window (int): Period for structure
            
        Returns:
            pd.DataFrame: DataFrame with BoS markers
        """
        df = df.copy()
        df['BOS_BULLISH'] = False
        df['BOS_BEARISH'] = False
        df['STRUCTURE_LEVEL'] = np.nan
        
        for i in range(window + 1, len(df)):
            # Get previous swing high and low
            prev_window = df.iloc[i-window:i]
            prev_high = prev_window['High'].max()
            prev_low = prev_window['Low'].min()
            
            current = df.iloc[i]
            
            # Bullish BoS: Close above previous high with volume
            if current['Close'] > prev_high:
                df.loc[df.index[i], 'BOS_BULLISH'] = True
                df.loc[df.index[i], 'STRUCTURE_LEVEL'] = prev_high
            
            # Bearish BoS: Close below previous low with volume
            if current['Close'] < prev_low:
                df.loc[df.index[i], 'BOS_BEARISH'] = True
                df.loc[df.index[i], 'STRUCTURE_LEVEL'] = prev_low
        
        return df
    
    def generate_signals(self, df):
        """
        Generate trading signals based on all ICT concepts
        
        Args:
            df (pd.DataFrame): OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with signals
        """
        df = df.copy()
        
        logger.info("Generating ICT signals...")
        
        # Identify all ICT elements
        df = self.identify_order_blocks(df)
        print('DEBUG after identify_order_blocks:', df.columns, df.shape)
        df = self.identify_fair_value_gaps(df)
        print('DEBUG after identify_fair_value_gaps:', df.columns, df.shape)
        df = self.identify_liquidity_voids(df)
        print('DEBUG after identify_liquidity_voids:', df.columns, df.shape)
        df = self.identify_supply_demand_zones(df)
        print('DEBUG after identify_supply_demand_zones:', df.columns, df.shape)
        df = self.identify_break_of_structure(df)
        print('DEBUG after identify_break_of_structure:', df.columns, df.shape)
        
        # Generate signals
        df['Signal'] = 0  # 0=hold, 1=buy, -1=sell
        df['Signal_Strength'] = 0.0  # 0-10 confidence score

        print("DEBUG: DataFrame column types and shapes:")
        for col in df.columns:
            print(f"  {col}: type={type(df[col])}, shape={getattr(df[col], 'shape', 'N/A')}, sample={df[col].head(3).to_list()}")

        for i in range(1, min(len(df), 10)):
            buy_score = 0.0
            sell_score = 0.0

            row = df.iloc[i]
            row_prev = df.iloc[i-1]

            print(f"DEBUG i={i} types: Close={type(row['Close'])}, OB_BULLISH={type(row.get('OB_BULLISH', None))}, FVG_BULLISH={type(row.get('FVG_BULLISH', None))}, DEMAND_ZONE={type(row.get('DEMAND_ZONE', None))}, BOS_BULLISH={type(row.get('BOS_BULLISH', None))}, LIQUIDITY_VOID={type(row.get('LIQUIDITY_VOID', None))}")
            print(f"DEBUG i={i} values: Close={row['Close']}, OB_BULLISH={row.get('OB_BULLISH', None)}, FVG_BULLISH={row.get('FVG_BULLISH', None)}, DEMAND_ZONE={row.get('DEMAND_ZONE', None)}, BOS_BULLISH={row.get('BOS_BULLISH', None)}, LIQUIDITY_VOID={row.get('LIQUIDITY_VOID', None)}")

            close_i = float(row['Close'])
            close_prev = float(row_prev['Close'])
            low_i = float(row['Low'])
            high_i = float(row['High'])

            def to_bool(val):
                # Handles scalar, numpy, pandas types
                if isinstance(val, (np.generic, np.bool_)):
                    return bool(val)
                if hasattr(val, 'item'):
                    return bool(val.item())
                return bool(val)

            ob_bull = to_bool(row['OB_BULLISH']) if 'OB_BULLISH' in df.columns else False
            fvg_bull = to_bool(row['FVG_BULLISH']) if 'FVG_BULLISH' in df.columns else False
            demand_zone = to_bool(row['DEMAND_ZONE']) if 'DEMAND_ZONE' in df.columns else False
            bos_bull = to_bool(row['BOS_BULLISH']) if 'BOS_BULLISH' in df.columns else False
            liq_void = to_bool(row['LIQUIDITY_VOID']) if 'LIQUIDITY_VOID' in df.columns else False

            ob_bear = to_bool(row['OB_BEARISH']) if 'OB_BEARISH' in df.columns else False
            fvg_bear = to_bool(row['FVG_BEARISH']) if 'FVG_BEARISH' in df.columns else False
            supply_zone = to_bool(row['SUPPLY_ZONE']) if 'SUPPLY_ZONE' in df.columns else False
            bos_bear = to_bool(row['BOS_BEARISH']) if 'BOS_BEARISH' in df.columns else False

            # Bullish signals
            weights = self.confluence_weights

            if ob_bull:
                buy_score += weights.get('order_block', 2.0)
            if fvg_bull:
                buy_score += weights.get('fvg', 1.5)
            if demand_zone and (close_i > close_prev):
                buy_score += weights.get('demand_zone', 1.5)
            if bos_bull:
                buy_score += weights.get('bos', 2.5)
            if liq_void and (close_prev < low_i):
                buy_score += weights.get('liquidity_void', 1.0)

            # Bearish signals
            if ob_bear:
                sell_score += weights.get('order_block', 2.0)
            if fvg_bear:
                sell_score += weights.get('fvg', 1.5)
            if supply_zone and (close_i < close_prev):
                sell_score += weights.get('supply_zone', 1.5)
            if bos_bear:
                sell_score += weights.get('bos', 2.5)
            if liq_void and (close_prev > high_i):
                sell_score += weights.get('liquidity_void', 1.0)

            # Determine signal
            if buy_score > sell_score and buy_score >= self.min_bull_score:
                df.loc[df.index[i], 'Signal'] = 1
                df.loc[df.index[i], 'Signal_Strength'] = min(buy_score / self.strength_divisor, 10)
            elif sell_score > buy_score and sell_score >= self.min_bear_score:
                df.loc[df.index[i], 'Signal'] = -1
                df.loc[df.index[i], 'Signal_Strength'] = min(sell_score / self.strength_divisor, 10)
        
        logger.info(f"✓ Generated {(df['Signal'] != 0).sum()} signals")
        
        return df


if __name__ == '__main__':
    # Test the strategy
    from data_fetch_yfinance import YFinanceDataFetcher
    
    print("\n🚀 Testing ICT Strategy\n")
    
    fetcher = YFinanceDataFetcher()
    df = fetcher.fetch_historical_data('XAUUSD', period='1y', interval='1d')
    
    strategy = ICTStrategy()
    df_signals = strategy.generate_signals(df)
    
    # Display results
    print(f"\nSignals Generated:")
    print(f"  Buy signals:  {(df_signals['Signal'] == 1).sum()}")
    print(f"  Sell signals: {(df_signals['Signal'] == -1).sum()}")
    
    print(f"\nLast 10 rows with signals:")
    print(df_signals[['Close', 'Signal', 'Signal_Strength', 'OB_BULLISH', 'OB_BEARISH', 'FVG_BULLISH', 'FVG_BEARISH', 'BOS_BULLISH', 'BOS_BEARISH']].tail(10))
