"""
Correlation Manager - Prevent over-exposure to correlated assets
Analyzes correlation between instruments to avoid taking same bet multiple times
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrelationManager:
    """
    Manage correlation between trading instruments
    
    Purpose:
    - Calculate correlation between instruments
    - Prevent over-exposure to highly correlated assets
    - Limit total correlated risk
    
    Example: XAUUSD, XAUEUR, XAUGBP are all gold = highly correlated
    Trading all 3 = 3x leverage on single bet, not 3 independent bets
    """
    
    def __init__(self,
                 data_fetcher,
                 correlation_window: int = 60,  # Days for correlation calculation
                 high_correlation_threshold: float = 0.7,  # Correlation >= 0.7 = highly correlated
                 max_correlated_positions: int = 2,  # Max positions in correlated group
                 max_correlated_risk_pct: float = 0.05):  # Max 5% total risk in correlated group
        """
        Initialize correlation manager
        
        Args:
            data_fetcher: Data fetcher instance
            correlation_window: Days of data for correlation calculation
            high_correlation_threshold: Threshold for high correlation (0.7 = 70%)
            max_correlated_positions: Maximum positions in correlated group
            max_correlated_risk_pct: Maximum total risk in correlated group
        """
        self.data_fetcher = data_fetcher
        self.correlation_window = correlation_window
        self.high_corr_threshold = high_correlation_threshold
        self.max_correlated_positions = max_correlated_positions
        self.max_correlated_risk_pct = max_correlated_risk_pct
        
        # Predefined correlation groups (known relationships)
        self.correlation_groups = {
            'gold': ['GC=F', 'GLD', 'XAUUSD', 'XAUEUR', 'XAUGBP'],
            'indian_indices': ['^NSEI', '^NSEBANK'],
            'us_indices': ['^GSPC', '^DJI', '^IXIC'],
            'oil': ['CL=F', 'USO', 'BZ=F'],
            'crypto': ['BTC-USD', 'ETH-USD'],
        }
        
        # Cache for correlation calculations
        self.correlation_cache = {}
        self.cache_timestamp = {}
    
    def calculate_correlation(self, symbol1: str, symbol2: str, 
                             period: str = '3mo', interval: str = '1d') -> float:
        """
        Calculate correlation between two symbols
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            period: Historical period
            interval: Data interval
            
        Returns:
            Correlation coefficient (-1 to 1)
            1 = perfect positive correlation
            -1 = perfect negative correlation
            0 = no correlation
        """
        # Check cache
        cache_key = f"{symbol1}_{symbol2}_{period}_{interval}"
        cache_time = self.cache_timestamp.get(cache_key)
        
        if cache_time and (datetime.now() - cache_time).seconds < 3600:  # 1 hour cache
            return self.correlation_cache.get(cache_key, 0.0)
        
        try:
            # Fetch data for both symbols
            df1 = self.data_fetcher.fetch_historical_data(symbol1, period=period, interval=interval)
            df2 = self.data_fetcher.fetch_historical_data(symbol2, period=period, interval=interval)
            
            if df1 is None or df2 is None or len(df1) < 20 or len(df2) < 20:
                logger.warning(f"Insufficient data for correlation: {symbol1} / {symbol2}")
                return 0.0
            
            # Align data by date
            df1 = df1[['Close']].rename(columns={'Close': symbol1})
            df2 = df2[['Close']].rename(columns={'Close': symbol2})
            
            merged = pd.merge(df1, df2, left_index=True, right_index=True, how='inner')
            
            if len(merged) < 20:
                logger.warning(f"Insufficient overlapping data: {symbol1} / {symbol2}")
                return 0.0
            
            # Calculate correlation on returns (not prices)
            returns1 = merged[symbol1].pct_change().dropna()
            returns2 = merged[symbol2].pct_change().dropna()
            
            correlation = returns1.corr(returns2)
            
            # Cache result
            self.correlation_cache[cache_key] = correlation
            self.cache_timestamp[cache_key] = datetime.now()
            
            logger.debug(f"Correlation {symbol1} / {symbol2}: {correlation:.3f}")
            
            return correlation
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0
    
    def build_correlation_matrix(self, symbols: List[str]) -> pd.DataFrame:
        """
        Build correlation matrix for multiple symbols
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            DataFrame with correlation matrix
        """
        n = len(symbols)
        corr_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    corr_matrix[i, j] = 1.0
                elif i < j:
                    corr = self.calculate_correlation(symbols[i], symbols[j])
                    corr_matrix[i, j] = corr
                    corr_matrix[j, i] = corr  # Symmetric
        
        df_corr = pd.DataFrame(corr_matrix, index=symbols, columns=symbols)
        
        return df_corr
    
    def find_correlated_groups(self, symbols: List[str]) -> Dict[str, List[str]]:
        """
        Find groups of highly correlated symbols
        
        Args:
            symbols: List of symbols to analyze
            
        Returns:
            Dictionary of {group_name: [symbols]}
        """
        corr_matrix = self.build_correlation_matrix(symbols)
        
        groups = {}
        assigned = set()
        
        for i, sym1 in enumerate(symbols):
            if sym1 in assigned:
                continue
            
            # Find all symbols highly correlated with sym1
            group = [sym1]
            
            for j, sym2 in enumerate(symbols):
                if i != j and sym2 not in assigned:
                    corr = corr_matrix.iloc[i, j]
                    
                    if abs(corr) >= self.high_corr_threshold:
                        group.append(sym2)
                        assigned.add(sym2)
            
            if len(group) > 1:
                groups[f"Group_{len(groups)+1}"] = group
                assigned.add(sym1)
        
        # Add ungrouped symbols as individual groups
        for sym in symbols:
            if sym not in assigned:
                groups[f"Independent_{sym}"] = [sym]
        
        return groups
    
    def get_symbol_group(self, symbol: str) -> Optional[str]:
        """Get predefined correlation group for a symbol"""
        for group_name, symbols in self.correlation_groups.items():
            if symbol in symbols:
                return group_name
        return None
    
    def check_correlation_limit(self,
                                new_symbol: str,
                                new_direction: int,
                                new_risk_pct: float,
                                open_positions: List[Dict]) -> Tuple[bool, str]:
        """
        Check if new position violates correlation limits
        
        Args:
            new_symbol: Symbol for new trade
            new_direction: Direction (1=BUY, -1=SELL)
            new_risk_pct: Risk percentage of new trade
            open_positions: List of currently open positions
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        if not open_positions:
            return True, "✓ No open positions"
        
        # Find correlation group for new symbol
        new_group = self.get_symbol_group(new_symbol)
        
        # Find correlated open positions
        correlated_positions = []
        
        for pos in open_positions:
            pos_symbol = pos.get('symbol', '')
            pos_direction = pos.get('direction', 0)
            pos_risk = pos.get('risk_pct', 0)
            
            # Check if in same predefined group
            pos_group = self.get_symbol_group(pos_symbol)
            
            if new_group and pos_group == new_group:
                # Same group - check direction
                if pos_direction == new_direction:
                    correlated_positions.append(pos)
            else:
                # Calculate correlation dynamically
                corr = self.calculate_correlation(new_symbol, pos_symbol)
                
                if abs(corr) >= self.high_corr_threshold:
                    # Highly correlated
                    if (corr > 0 and pos_direction == new_direction) or \
                       (corr < 0 and pos_direction != new_direction):
                        correlated_positions.append(pos)
        
        if not correlated_positions:
            return True, "✓ No correlated positions"
        
        # Check position count limit
        if len(correlated_positions) >= self.max_correlated_positions:
            symbols = [p['symbol'] for p in correlated_positions]
            return False, (f"⚠️ Max {self.max_correlated_positions} correlated positions reached. "
                          f"Open: {symbols}")
        
        # Check total risk limit
        total_correlated_risk = sum(p.get('risk_pct', 0) for p in correlated_positions)
        total_with_new = total_correlated_risk + new_risk_pct
        
        max_risk_pct = self.max_correlated_risk_pct * 100
        
        if total_with_new > max_risk_pct:
            return False, (f"⚠️ Correlated risk limit ({max_risk_pct:.1f}%) would be exceeded. "
                          f"Current: {total_correlated_risk:.1f}%, New: {new_risk_pct:.1f}%")
        
        return True, f"✓ Allowed ({len(correlated_positions)} correlated positions, {total_with_new:.1f}% total risk)"
    
    def get_correlation_report(self, symbols: List[str]) -> str:
        """Generate correlation report for symbols"""
        report = f"\n{'='*70}\n"
        report += "CORRELATION ANALYSIS REPORT\n"
        report += f"{'='*70}\n\n"
        
        # Build correlation matrix
        corr_matrix = self.build_correlation_matrix(symbols)
        
        report += "Correlation Matrix:\n"
        report += str(corr_matrix.round(2)) + "\n\n"
        
        # Find highly correlated pairs
        report += f"Highly Correlated Pairs (>= {self.high_corr_threshold}):\n"
        report += "-" * 70 + "\n"
        
        high_corr_pairs = []
        
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i < j:
                    corr = corr_matrix.iloc[i, j]
                    if abs(corr) >= self.high_corr_threshold:
                        high_corr_pairs.append((sym1, sym2, corr))
        
        if high_corr_pairs:
            for sym1, sym2, corr in sorted(high_corr_pairs, key=lambda x: abs(x[2]), reverse=True):
                report += f"  {sym1:15} <-> {sym2:15}  Correlation: {corr:+.3f}\n"
        else:
            report += "  No highly correlated pairs found\n"
        
        report += "\n" + "="*70 + "\n"
        
        return report


if __name__ == '__main__':
    # Test correlation manager
    print("\n🧪 Testing Correlation Manager\n")
    
    from data_fetch_yfinance import YFinanceDataFetcher
    
    fetcher = YFinanceDataFetcher()
    
    manager = CorrelationManager(
        data_fetcher=fetcher,
        high_correlation_threshold=0.7,
        max_correlated_positions=2,
        max_correlated_risk_pct=0.05
    )
    
    # Test gold pairs correlation
    print("="*70)
    print("TEST 1: Gold Instruments Correlation")
    print("="*70)
    
    gold_symbols = ['GC=F', 'GLD']
    
    report = manager.get_correlation_report(gold_symbols)
    print(report)
    
    # Test Indian indices
    print("\n" + "="*70)
    print("TEST 2: Indian Indices Correlation")
    print("="*70)
    
    indian_symbols = ['^NSEI', '^NSEBANK']
    
    report2 = manager.get_correlation_report(indian_symbols)
    print(report2)
    
    # Test position limits
    print("\n" + "="*70)
    print("TEST 3: Correlation Position Limits")
    print("="*70)
    
    # Simulate open positions
    open_positions = [
        {'symbol': 'GC=F', 'direction': 1, 'risk_pct': 2.0},  # Long gold futures
    ]
    
    # Try to add another gold position
    allowed, reason = manager.check_correlation_limit(
        new_symbol='GLD',
        new_direction=1,  # Also long
        new_risk_pct=2.0,
        open_positions=open_positions
    )
    
    print(f"\nCan add GLD long position? {allowed}")
    print(f"Reason: {reason}")
    
    # Try to add opposite direction
    allowed2, reason2 = manager.check_correlation_limit(
        new_symbol='GLD',
        new_direction=-1,  # Short
        new_risk_pct=2.0,
        open_positions=open_positions
    )
    
    print(f"\nCan add GLD short position? {allowed2}")
    print(f"Reason: {reason2}")
    
    # Try to exceed risk limit
    open_positions2 = [
        {'symbol': 'GC=F', 'direction': 1, 'risk_pct': 3.0},
        {'symbol': 'GLD', 'direction': 1, 'risk_pct': 2.5},
    ]
    
    allowed3, reason3 = manager.check_correlation_limit(
        new_symbol='^NSEI',  # Different group
        new_direction=1,
        new_risk_pct=2.0,
        open_positions=open_positions2
    )
    
    print(f"\nCan add ^NSEI position (different group)? {allowed3}")
    print(f"Reason: {reason3}")
    
    print("\n✅ Correlation Manager Tests Complete\n")
