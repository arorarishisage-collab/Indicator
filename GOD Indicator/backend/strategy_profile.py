"""Strategy profile loader for standardized backtest/live configs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any


@dataclass
class StrategyProfile:
    """Represents a reusable combination of data source + strategy params."""

    name: str
    data_source: Dict[str, Any]
    strategy: Dict[str, Any]
    filters: Dict[str, Any] = field(default_factory=dict)
    live: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, profile_name: str, base_dir: str = 'config/strategy_profiles') -> 'StrategyProfile':
        path = Path(base_dir)
        if path.is_dir():
            profile_path = path / f"{profile_name}.json"
        else:
            profile_path = Path(profile_name)

        if not profile_path.exists():
            raise FileNotFoundError(f"Strategy profile not found: {profile_path}")

        with open(profile_path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)

        data.setdefault('name', profile_path.stem)
        data.setdefault('filters', {})
        data.setdefault('live', {})
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'data_source': self.data_source,
            'strategy': self.strategy,
            'filters': self.filters,
            'live': self.live,
        }


def list_profiles(base_dir: str = 'config/strategy_profiles') -> Dict[str, Path]:
    base = Path(base_dir)
    if not base.exists():
        return {}
    return {p.stem: p for p in base.glob('*.json')}
