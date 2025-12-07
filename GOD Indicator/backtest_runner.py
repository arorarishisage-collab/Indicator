#!/usr/bin/env python3
"""Command-line backtest runner driven by strategy profiles."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pandas as pd

from backend.data_manager import DataManager
from backend.strategy_profile import StrategyProfile, list_profiles
from backend.professional_backtester import ProfessionalBacktester, BacktestConfig
from backend.performance_metrics import PerformanceAnalyzer
from backend.ema_strategy import EMA30Strategy
from backend.ict_strategy import ICTStrategy

STRATEGY_MAP = {
    'EMA30Strategy': EMA30Strategy,
    'ICTStrategy': ICTStrategy,
}


def parse_kwargs(pairs: list[str]) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {}
    for item in pairs:
        if '=' not in item:
            raise ValueError(f"Invalid --param '{item}'. Use key=value format.")
        key, value = item.split('=', 1)
        parsed[key.strip()] = coerce_value(value.strip())
    return parsed


def coerce_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {'true', 'false'}:
        return lowered == 'true'
    try:
        if '.' in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def apply_overrides(profile: StrategyProfile, args: argparse.Namespace) -> StrategyProfile:
    # Data overrides
    if args.csv:
        profile.data_source = {
            'type': 'csv',
            'path': args.csv,
            'datetime_column': args.datetime_column,
            'resample_to': args.resample_to,
            'timezone': args.timezone,
        }
    else:
        if args.symbol:
            profile.data_source['symbol'] = args.symbol
        if args.interval:
            profile.data_source['interval'] = args.interval
        if args.period:
            profile.data_source['period'] = args.period
        if args.start_date:
            profile.data_source['start_date'] = args.start_date
        if args.end_date:
            profile.data_source['end_date'] = args.end_date

    # Strategy class override
    if args.strategy:
        profile.strategy['class'] = args.strategy

    # Strategy params override
    if args.param:
        overrides = parse_kwargs(args.param)
        profile.strategy.setdefault('params', {}).update(overrides)

    return profile


def instantiate_strategy(profile: StrategyProfile):
    strategy_class_name = profile.strategy.get('class')
    params = profile.strategy.get('params', {})

    if strategy_class_name not in STRATEGY_MAP:
        raise ValueError(
            f"Unsupported strategy '{strategy_class_name}'. Available: {', '.join(STRATEGY_MAP)}"
        )

    strategy_class = STRATEGY_MAP[strategy_class_name]
    return strategy_class(**params)


def ensure_output_dir(base_dir: Path, profile_name: str) -> Path:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = base_dir / profile_name / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def export_outputs(backtester: ProfessionalBacktester, result, metrics: Dict[str, Any], signals: pd.DataFrame, output_dir: Path, args):
    metrics_path = output_dir / 'metrics.json'
    trades_path = output_dir / 'trades.csv'
    equity_path = output_dir / 'equity_curve.csv'
    signals_path = output_dir / 'signals.csv'

    with open(metrics_path, 'w', encoding='utf-8') as handle:
        json.dump(metrics, handle, indent=2, default=str)

    trades_df = backtester.get_trades_dataframe()
    trades_df.to_csv(trades_path, index=False)

    equity_df = backtester.get_equity_dataframe()
    equity_df.to_csv(equity_path, index=False)

    if args.export_signals:
        signals.to_csv(args.export_signals, index=False)
    else:
        signals.to_csv(signals_path, index=False)

    analyzer = PerformanceAnalyzer(initial_capital=result.initial_capital)
    analyzer.export_to_json(result, output_dir / 'performance_summary.json')


def run_backtest(args: argparse.Namespace):
    if args.list_profiles:
        available = list_profiles()
        if not available:
            print('No profiles found. Add files under config/strategy_profiles/.')
            return
        print('Available profiles:')
        for name, path in available.items():
            print(f"  - {name}: {path}")
        return

    if args.profile_file:
        profile = StrategyProfile.load(args.profile_file, base_dir='')
    else:
        profile = StrategyProfile.load(args.profile)

    profile = apply_overrides(profile, args)

    data_manager = DataManager()
    df = data_manager.load_source(profile.data_source)

    valid, message = data_manager.validate_data(df)
    if not valid:
        raise ValueError(f"Data validation failed: {message}")

    strategy = instantiate_strategy(profile)
    df_signals = strategy.generate_signals(df.copy())

    signal_series = df_signals['Signal']

    backtest_config = BacktestConfig(initial_capital=args.initial_capital)
    backtester = ProfessionalBacktester(backtest_config)
    result = backtester.backtest(df_signals, signal_series)

    analyzer = PerformanceAnalyzer(initial_capital=args.initial_capital)
    metrics = analyzer.analyze(result)

    print('\n=== BACKTEST SUMMARY ===')
    print(f"Profile: {profile.name}")
    print(f"Strategy: {profile.strategy.get('class')}")
    print(f"Data rows: {len(df_signals)}")
    print(f"Signals: {(signal_series != 0).sum()} (BUY: {(signal_series == 1).sum()}, SELL: {(signal_series == -1).sum()})")
    print(f"Final capital: {metrics.get('final_capital', result.final_capital):,.2f}")
    print(f"Total return %: {result.total_return_percent:.2f}")
    print(f"Win rate: {result.win_rate:.2f}%  | Profit factor: {result.profit_factor:.2f}")

    output_dir = ensure_output_dir(Path(args.output_dir), profile.name)
    export_outputs(backtester, result, metrics, df_signals, output_dir, args)
    print(f"\nArtifacts saved to: {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run backtests using strategy profiles.')
    parser.add_argument('--profile', default='gold_ema30', help='Profile name under config/strategy_profiles')
    parser.add_argument('--profile-file', help='Path to a specific profile JSON file')
    parser.add_argument('--list-profiles', action='store_true', help='List available strategy profiles and exit')

    data_group = parser.add_argument_group('data overrides')
    data_group.add_argument('--csv', help='Use CSV file instead of profile source')
    data_group.add_argument('--datetime-column', help='Datetime column name for CSV uploads')
    data_group.add_argument('--timezone', help='Timezone name for CSV timestamps (e.g., Asia/Kolkata)')
    data_group.add_argument('--resample-to', help='Resample CSV data to timeframe (e.g., 1H, 15T)')
    data_group.add_argument('--symbol', help='Override symbol/ticker')
    data_group.add_argument('--interval', help='Override timeframe/interval (yfinance notation)')
    data_group.add_argument('--period', help='Override lookback period (e.g., 1y, 6mo)')
    data_group.add_argument('--start-date', help='Override start date (YYYY-MM-DD)')
    data_group.add_argument('--end-date', help='Override end date (YYYY-MM-DD)')

    strat_group = parser.add_argument_group('strategy overrides')
    strat_group.add_argument('--strategy', help='Override strategy class name')
    strat_group.add_argument('--param', action='append', help='Strategy param override in key=value format', default=[])

    parser.add_argument('--initial-capital', type=float, default=100000, help='Initial capital for backtest')
    parser.add_argument('--output-dir', default='reports/backtests', help='Directory for output artifacts')
    parser.add_argument('--export-signals', help='Optional path to export full signal dataframe')

    return parser


if __name__ == '__main__':
    parser = build_parser()
    arguments = parser.parse_args()
    run_backtest(arguments)
