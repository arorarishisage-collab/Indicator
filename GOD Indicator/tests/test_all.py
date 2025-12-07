"""
Unit Tests for Gold Trading Signal System
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    import pytest
except ImportError:
    pytest = None

try:
    from data_fetch import DataFetcher, load_demo_data
    from zone_detector import ZoneDetector, Zone, OrderBlock, FairValueGap
    from signal_generator import SignalGenerator, SignalType
    from backtester import SimpleBacktester
except ImportError as e:
    raise ImportError(f"Backend modules not found. Make sure backend files exist: {e}")


class TestDataFetcher:
    """Test data fetching module."""
    
    def test_load_demo_data(self):
        """Test loading demo data."""
        df = load_demo_data()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'Close' in df.columns
        assert 'High' in df.columns
        assert 'Low' in df.columns
        assert 'Open' in df.columns
        assert 'Volume' in df.columns
    
    def test_validate_data(self):
        """Test data validation."""
        df = load_demo_data()
        
        fetcher = DataFetcher()
        is_valid = fetcher.validate_data(df)
        
        assert is_valid is True
    
    def test_add_technical_indicators(self):
        """Test indicator calculation."""
        df = load_demo_data()
        fetcher = DataFetcher()
        df = fetcher.add_technical_indicators(df)
        
        assert 'EMA_30' in df.columns
        assert 'EMA_200' in df.columns
        assert 'ATR' in df.columns
        assert 'RSI' in df.columns
        assert not df['EMA_30'].isna().all()


class TestZoneDetector:
    """Test zone detection module."""
    
    def setup_method(self):
        """Setup for each test."""
        self.df = load_demo_data()
        self.df = self.df.tail(200)
        self.detector = ZoneDetector(lookback=20)
    
    def test_detect_swings(self):
        """Test swing detection."""
        highs, lows = self.detector.detect_swings(self.df)
        
        assert isinstance(highs, list)
        assert isinstance(lows, list)
        assert len(highs) > 0
        assert len(lows) > 0
    
    def test_detect_supply_demand_zones(self):
        """Test zone detection."""
        highs, lows = self.detector.detect_swings(self.df)
        zones = self.detector.detect_supply_demand_zones(self.df, highs, lows)
        
        assert isinstance(zones, list)
        assert len(zones) > 0
        
        # Check zone properties
        for zone in zones[:5]:
            assert isinstance(zone, Zone)
            assert zone.zone_type in ['supply', 'demand']
            assert zone.top > zone.bottom
    
    def test_detect_order_blocks(self):
        """Test order block detection."""
        obs = self.detector.detect_order_blocks(self.df)
        
        assert isinstance(obs, list)
        
        # Check OB properties
        for ob in obs[:5]:
            assert isinstance(ob, OrderBlock)
            assert ob.ob_type in ['bullish', 'bearish']
            assert ob.high >= ob.low
    
    def test_detect_fair_value_gaps(self):
        """Test FVG detection."""
        fvgs = self.detector.detect_fair_value_gaps(self.df)
        
        assert isinstance(fvgs, list)
        
        # Check FVG properties
        for fvg in fvgs[:5]:
            assert isinstance(fvg, FairValueGap)
            assert fvg.fvg_type in ['bullish', 'bearish']
            assert fvg.gap_top >= fvg.gap_bottom
    
    def test_detect_support_resistance(self):
        """Test support/resistance detection."""
        srl = self.detector.detect_support_resistance(self.df)
        
        assert 'support' in srl
        assert 'resistance' in srl
        assert isinstance(srl['support'], list)
        assert isinstance(srl['resistance'], list)


class TestSignalGenerator:
    """Test signal generation module."""
    
    def setup_method(self):
        """Setup for each test."""
        self.df = load_demo_data()
        self.df = self.df.tail(200)
        
        fetcher = DataFetcher()
        self.df = fetcher.add_technical_indicators(self.df)
        
        detector = ZoneDetector()
        self.swing_highs, self.swing_lows = detector.detect_swings(self.df)
        self.zones = detector.detect_supply_demand_zones(self.df, self.swing_highs, self.swing_lows)
        self.zones = detector.update_zone_mitigation(self.zones, self.df)
        
        self.obs = detector.detect_order_blocks(self.df)
        self.fvgs = detector.detect_fair_value_gaps(self.df)
        self.srl = detector.detect_support_resistance(self.df)
    
    def test_generate_signals(self):
        """Test signal generation."""
        generator = SignalGenerator()
        df_signals = generator.generate_signals(
            self.df,
            self.zones,
            self.obs,
            self.fvgs,
            self.srl
        )
        
        assert 'Signal' in df_signals.columns
        assert 'EntryPrice' in df_signals.columns
        assert 'StopLoss' in df_signals.columns
        assert 'TakeProfit' in df_signals.columns
        
        # Check signal values
        signals = df_signals['Signal'].unique()
        assert 0 in signals or len(signals) == 0  # No signal or some signals
    
    def test_signal_risk_reward(self):
        """Test risk/reward calculation."""
        generator = SignalGenerator(min_risk_reward=1.5)
        df_signals = generator.generate_signals(
            self.df,
            self.zones,
            self.obs,
            self.fvgs,
            self.srl
        )
        
        # Check R/R for signals
        signals_df = df_signals[df_signals['Signal'] != 0]
        
        for idx, row in signals_df.iterrows():
            entry = row['EntryPrice']
            sl = row['StopLoss']
            tp = row['TakeProfit']
            
            if not pd.isna(entry) and not pd.isna(sl) and not pd.isna(tp):
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                rr = reward / risk if risk > 0 else 0
                
                assert rr >= generator.min_risk_reward


class TestBacktester:
    """Test backtesting module."""
    
    def setup_method(self):
        """Setup for each test."""
        # Generate signals
        df = load_demo_data()
        df = df.tail(300)
        
        fetcher = DataFetcher()
        df = fetcher.add_technical_indicators(df)
        
        detector = ZoneDetector()
        swing_highs, swing_lows = detector.detect_swings(df)
        zones = detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
        zones = detector.update_zone_mitigation(zones, df)
        
        obs = detector.detect_order_blocks(df)
        fvgs = detector.detect_fair_value_gaps(df)
        srl = detector.detect_support_resistance(df)
        
        generator = SignalGenerator()
        self.df = generator.generate_signals(df, zones, obs, fvgs, srl)
    
    def test_run_backtest(self):
        """Test backtest execution."""
        backtester = SimpleBacktester(initial_capital=10000)
        results = backtester.run_backtest(self.df)
        
        assert 'total_trades' in results
        assert 'win_rate' in results
        assert 'profit_factor' in results
        assert 'max_drawdown_pct' in results
        
        # Basic sanity checks
        assert results['total_trades'] >= 0
        assert 0 <= results['win_rate'] <= 100
        assert results['profit_factor'] >= 0
        assert -100 <= results['max_drawdown_pct'] <= 0
    
    def test_backtest_metrics(self):
        """Test backtest metric calculation."""
        backtester = SimpleBacktester(initial_capital=10000)
        results = backtester.run_backtest(self.df)
        
        if results['total_trades'] > 0:
            # Win rate should be reasonable
            assert results['win_rate'] >= 0
            
            # If there are trades, should have both profit and loss metrics
            if results['winning_trades'] > 0:
                assert results['avg_win'] > 0
            
            if results['losing_trades'] > 0:
                assert results['avg_loss'] < 0


class TestIntegration:
    """Integration tests for full workflow."""
    
    def test_full_workflow(self):
        """Test complete workflow from data to backtest."""
        # Load data
        df = load_demo_data()
        df = df.tail(200)
        
        # Add indicators
        fetcher = DataFetcher()
        df = fetcher.add_technical_indicators(df)
        
        # Detect zones
        detector = ZoneDetector()
        swing_highs, swing_lows = detector.detect_swings(df)
        zones = detector.detect_supply_demand_zones(df, swing_highs, swing_lows)
        zones = detector.update_zone_mitigation(zones, df)
        
        obs = detector.detect_order_blocks(df)
        fvgs = detector.detect_fair_value_gaps(df)
        srl = detector.detect_support_resistance(df)
        
        # Generate signals
        generator = SignalGenerator()
        df = generator.generate_signals(df, zones, obs, fvgs, srl)
        
        # Run backtest
        backtester = SimpleBacktester()
        results = backtester.run_backtest(df)
        
        # Verify results
        assert results['total_trades'] >= 0
        assert results['win_rate'] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
