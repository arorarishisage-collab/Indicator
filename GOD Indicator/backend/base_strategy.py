"""
Abstract base strategy class for the Gold Trading Signal System.
Allows users to implement custom strategies and combine multiple strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np


@dataclass
class Signal:
    """Represents a trading signal"""
    timestamp: pd.Timestamp
    signal_type: int  # -1: Sell, 0: Hold, 1: Buy
    price: float
    confidence: float  # 0-1
    strategy_name: str
    details: Dict = None


@dataclass
class TradeResult:
    """Represents a completed trade"""
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    quantity: float
    direction: int  # 1: Long, -1: Short
    pnl: float
    pnl_percent: float
    strategy_name: str


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    To create a custom strategy:
    1. Inherit from BaseStrategy
    2. Implement required methods
    3. Register in StrategyFactory
    
    Example:
    --------
    class MyStrategy(BaseStrategy):
        def __init__(self):
            super().__init__("MyStrategy", "Custom strategy description")
        
        def validate_inputs(self, df: pd.DataFrame) -> bool:
            return all(col in df.columns for col in ['Open', 'High', 'Low', 'Close'])
        
        def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
            df['Signal'] = 0
            # Your strategy logic here
            return df
    """
    
    def __init__(self, name: str, description: str, parameters: Dict = None):
        """
        Initialize strategy
        
        Args:
            name: Strategy name (unique identifier)
            description: Human-readable description
            parameters: Dict of strategy parameters with defaults
        """
        self.name = name
        self.description = description
        self.parameters = parameters or {}
        self.signals: List[Signal] = []
        
    @abstractmethod
    def validate_inputs(self, df: pd.DataFrame) -> bool:
        """
        Validate that input DataFrame has required columns.
        
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals.
        
        Args:
            df: OHLCV DataFrame with columns: Open, High, Low, Close, Volume
            
        Returns:
            DataFrame with 'Signal' column (-1/0/1) and optional 'Confidence' column
        """
        pass
    
    def get_parameters(self) -> Dict:
        """Get current strategy parameters"""
        return self.parameters.copy()
    
    def set_parameters(self, params: Dict) -> None:
        """
        Update strategy parameters
        
        Args:
            params: Dict of parameter names and values
        """
        for key, value in params.items():
            if key in self.parameters:
                self.parameters[key] = value
            else:
                raise ValueError(f"Unknown parameter: {key}")
    
    def get_info(self) -> Dict:
        """Get strategy information"""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters,
            'signal_count': len(self.signals)
        }


class CombinedStrategy(BaseStrategy):
    """
    Combines multiple strategies using weighted voting or confluence.
    
    Example:
    --------
    combined = CombinedStrategy([strategy1, strategy2], weights=[0.6, 0.4])
    df = combined.generate_signals(df)
    """
    
    def __init__(self, strategies: List[BaseStrategy], 
                 weights: List[float] = None,
                 confluence_mode: str = 'weighted'):
        """
        Initialize combined strategy
        
        Args:
            strategies: List of BaseStrategy instances
            weights: Weights for each strategy (must sum to 1.0)
            confluence_mode: 'weighted', 'majority', or 'unanimous'
        """
        names = "_".join([s.name for s in strategies])
        super().__init__(f"Combined_{names}", "Combined strategy")
        
        self.strategies = strategies
        self.confluence_mode = confluence_mode
        
        if weights is None:
            weights = [1.0 / len(strategies)] * len(strategies)
        
        if len(weights) != len(strategies):
            raise ValueError("Number of weights must match number of strategies")
        
        if not np.isclose(sum(weights), 1.0):
            raise ValueError("Weights must sum to 1.0")
        
        self.weights = weights
    
    def validate_inputs(self, df: pd.DataFrame) -> bool:
        """Validate all sub-strategies"""
        return all(s.validate_inputs(df) for s in self.strategies)
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate combined signals from all strategies
        
        Confluence modes:
        - 'weighted': Weighted vote of all strategies
        - 'majority': Signal if majority agrees
        - 'unanimous': Signal only if all agree
        """
        if not self.validate_inputs(df):
            raise ValueError("Input validation failed")
        
        # Generate signals from all strategies
        dfs = []
        for strategy in self.strategies:
            result = strategy.generate_signals(df.copy())
            dfs.append(result['Signal'].values)
        
        signals = np.array(dfs)  # Shape: (num_strategies, num_bars)
        
        if self.confluence_mode == 'weighted':
            # Weighted average of signals
            combined = np.average(signals, axis=0, weights=self.weights)
            # Convert to -1, 0, 1
            df['Signal'] = np.sign(combined).astype(int)
        
        elif self.confluence_mode == 'majority':
            # Majority vote
            positive = (signals > 0).sum(axis=0)
            negative = (signals < 0).sum(axis=0)
            df['Signal'] = np.where(positive > negative, 1, 
                                   np.where(negative > positive, -1, 0))
        
        elif self.confluence_mode == 'unanimous':
            # All must agree
            df['Signal'] = np.where(
                (signals > 0).all(axis=0), 1,
                np.where((signals < 0).all(axis=0), -1, 0)
            )
        
        else:
            raise ValueError(f"Unknown confluence mode: {self.confluence_mode}")
        
        return df


class StrategyFactory:
    """
    Factory for registering and retrieving strategies.
    Allows dynamic strategy registration and discovery.
    """
    
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, strategy_class: type) -> None:
        """Register a strategy class"""
        name = strategy_class.__name__
        cls._registry[name] = strategy_class
    
    @classmethod
    def create(cls, strategy_name: str, **kwargs) -> BaseStrategy:
        """Create a strategy instance by name"""
        if strategy_name not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown strategy: {strategy_name}. Available: {available}")
        
        strategy_class = cls._registry[strategy_name]
        return strategy_class(**kwargs)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """List all registered strategies"""
        return list(cls._registry.keys())

    @classmethod
    def load_plugins(cls, folder_path: str) -> None:
        """
        Dynamically load strategy plugins from a folder.

        The folder should contain Python modules that define classes
        inheriting from BaseStrategy and register themselves, or the
        loader will register any found subclasses automatically.

        Args:
            folder_path: Path to folder containing strategy plugin .py files
        """
        import importlib.util
        import inspect
        from pathlib import Path

        p = Path(folder_path)
        if not p.exists() or not p.is_dir():
            return

        for py in p.glob('*.py'):
            try:
                spec = importlib.util.spec_from_file_location(py.stem, str(py))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)

                    # Register any BaseStrategy subclasses found
                    for name, obj in inspect.getmembers(mod, inspect.isclass):
                        try:
                            if issubclass(obj, BaseStrategy) and obj is not BaseStrategy and obj is not CombinedStrategy:
                                cls.register(obj)
                        except Exception:
                            continue
            except Exception:
                # Skip modules that fail to import
                continue
    
    @classmethod
    def get_info(cls, strategy_name: str) -> Dict:
        """Get info about a registered strategy"""
        if strategy_name not in cls._registry:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy_class = cls._registry[strategy_name]
        return {
            'name': strategy_name,
            'class': strategy_class.__name__,
            'doc': strategy_class.__doc__
        }
