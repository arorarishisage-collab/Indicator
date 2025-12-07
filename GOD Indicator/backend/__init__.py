"""
Gold Trading Signal System - Backend Package
"""

__version__ = "1.0.0"
__author__ = "Trading Bot Team"

from .data_fetch import DataFetcher, load_demo_data
from .zone_detector import ZoneDetector, Zone, OrderBlock, FairValueGap
from .signal_generator import SignalGenerator, SignalType
from .backtester import SimpleBacktester

__all__ = [
    'DataFetcher',
    'load_demo_data',
    'ZoneDetector',
    'Zone',
    'OrderBlock',
    'FairValueGap',
    'SignalGenerator',
    'SignalType',
    'SimpleBacktester'
]
