#!/usr/bin/env python3
"""Multi-strategy reinforcement-learning trainer for trading agents."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from backend.advanced_rl_trading_system import (
    TradingEnvironment,
    PPOAgent,
    TORCH_AVAILABLE,
)
from backend.data_fetch import DataFetcher
from backend.rl_feedback_dataset import (
    action_bias_from_stats,
    load_feedback_dataframe,
    loss_penalty_from_stats,
    summarise_feedback,
    win_rate_target_from_stats,
)

MIN_FEEDBACK_TRADES = 5
DEFAULT_MODEL_TEMPLATE = "models/rl/{slug}_{symbol}.pth"
DEFAULT_SUMMARY_TEMPLATE = "reports/rl_feedback/{slug}_{symbol}_training.json"


def strategy_slug(strategy_name: str) -> str:
    slug = strategy_name.replace("Strategy", "")
    slug = slug.replace(" ", "")
    return slug.lower()


_SYMBOL_SANITIZE_RE = re.compile(r"[^a-z0-9]+")


def symbol_slug(symbol: str) -> str:
    normalized = symbol.strip().lower()
    return _SYMBOL_SANITIZE_RE.sub("_", normalized).strip("_") or "symbol"


@dataclass(frozen=True)
class StrategyTrainingConfig:
    strategy_name: str
    symbols: Tuple[str, ...] = ("GC=F",)
    period: str = "2y"
    interval: str = "1h"
    lookback_window: int = 50
    episodes: int = 500
    min_feedback_signal: float = 0.0
    model_template: str = DEFAULT_MODEL_TEMPLATE
    summary_template: str = DEFAULT_SUMMARY_TEMPLATE

    def default_symbol(self) -> str:
        return self.symbols[0]

    def all_symbols(self) -> Tuple[str, ...]:
        return self.symbols

    def model_path(self, symbol: str) -> Path:
        slug = strategy_slug(self.strategy_name)
        return Path(
            self.model_template.format(
                slug=slug,
                strategy=self.strategy_name,
                symbol=symbol_slug(symbol),
            )
        )

    def summary_path(self, symbol: str) -> Path:
        slug = strategy_slug(self.strategy_name)
        return Path(
            self.summary_template.format(
                slug=slug,
                strategy=self.strategy_name,
                symbol=symbol_slug(symbol),
            )
        )


DEFAULT_STRATEGY_CONFIGS: Dict[str, StrategyTrainingConfig] = {
    "EMA30Strategy": StrategyTrainingConfig(
        strategy_name="EMA30Strategy",
        symbols=("GC=F", "SI=F", "HG=F"),
        period="2y",
        interval="1h",
        lookback_window=60,
        episodes=500,
        min_feedback_signal=6.0,
    ),
    "ICTStrategy": StrategyTrainingConfig(
        strategy_name="ICTStrategy",
        symbols=("GC=F", "CL=F"),
        period="2y",
        interval="1h",
        lookback_window=60,
        episodes=500,
        min_feedback_signal=7.0,
    ),
    "VCPStrategy": StrategyTrainingConfig(
        strategy_name="VCPStrategy",
        symbols=("GC=F", "GLD", "SLV", "RELIANCE.NS", "HDFCBANK.NS"),
        period="3y",
        interval="4h",
        lookback_window=80,
        episodes=400,
        min_feedback_signal=7.5,
    ),
}


def available_strategies() -> List[str]:
    return sorted(DEFAULT_STRATEGY_CONFIGS.keys())


def _get_config(strategy_name: str) -> StrategyTrainingConfig:
    try:
        return DEFAULT_STRATEGY_CONFIGS[strategy_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown strategy '{strategy_name}'. Available: {', '.join(available_strategies())}"
        ) from exc


def _fetch_training_data(symbol: str, period: str, interval: str, emit: Callable[[str], None]) -> pd.DataFrame:
    fetcher = DataFetcher()
    emit(f"Fetching {symbol} data (period={period}, interval={interval})...")
    df = fetcher.fetch_historical_data(symbol=symbol, period=period, interval=interval)
    if df is None or df.empty:
        raise RuntimeError(f"No data returned for {symbol} ({interval}, {period})")
    df = df.sort_index()
    df = df.dropna(subset=["Close"])
    if "Volume" not in df.columns:
        df["Volume"] = 0.0
    emit(f"Loaded {len(df)} candles spanning {df.index[0]} to {df.index[-1]}")
    return df


def _load_feedback(
    strategy_name: str,
    symbol: Optional[str],
    min_signal: Optional[float],
    emit: Callable[[str], None],
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df = load_feedback_dataframe()
    if df.empty:
        emit("No feedback dataset found; proceeding without reward shaping adjustments.")
        return df, summarise_feedback(df)

    mask = pd.Series(True, index=df.index)
    if "strategy" in df.columns:
        mask &= df["strategy"].astype(str) == strategy_name
    if symbol and "symbol" in df.columns:
        mask &= df["symbol"].astype(str) == symbol

    filtered = df[mask].copy()

    if min_signal is not None and not filtered.empty and "signal_strength" in filtered.columns:
        filtered["signal_strength"] = pd.to_numeric(filtered["signal_strength"], errors="coerce")
        filtered = filtered[filtered["signal_strength"] >= float(min_signal)]

    stats = summarise_feedback(filtered)
    emit(
        "Feedback trades available: "
        f"{stats['n_trades']} (win rate {stats['win_rate'] * 100:.1f}% | min_signal={min_signal})"
    )

    return filtered, stats


def _apply_feedback_to_environment(
    env: TradingEnvironment,
    stats: Dict[str, Any],
    emit: Callable[[str], None],
) -> bool:
    if not stats or stats.get("n_trades", 0) < MIN_FEEDBACK_TRADES:
        emit("Not enough feedback trades to adjust reward shaping (need >= 5).")
        return False

    env.configure_from_feedback(
        action_bias=action_bias_from_stats(stats),
        win_rate_target=win_rate_target_from_stats(stats),
        loss_penalty_scale=loss_penalty_from_stats(stats),
    )
    emit("Applied feedback-driven reward shaping parameters.")
    return True


def run_training(
    *,
    strategy_name: str,
    symbol: Optional[str] = None,
    episodes: Optional[int] = None,
    period: Optional[str] = None,
    interval: Optional[str] = None,
    lookback_window: Optional[int] = None,
    min_feedback_signal: Optional[float] = None,
    model_path: Optional[str] = None,
    summary_path: Optional[str] = None,
    verbose: bool = True,
    log: Optional[Callable[[str], None]] = None,
    show_tips: bool = True,
    save_summary: bool = True,
) -> Dict[str, Any]:
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch is required. Install with: pip install torch torchvision")

    config = _get_config(strategy_name)
    symbol = symbol or config.default_symbol()
    if not symbol:
        raise ValueError(f"No trading symbol defined for strategy {strategy_name}")
    episodes = episodes or config.episodes
    period = period or config.period
    interval = interval or config.interval
    lookback_window = lookback_window or config.lookback_window
    min_feedback_signal = (
        config.min_feedback_signal if min_feedback_signal is None else float(min_feedback_signal)
    )

    model_path = Path(model_path) if model_path else config.model_path(symbol)
    summary_path = Path(summary_path) if summary_path else config.summary_path(symbol)

    logger = log or print

    def emit(message: str = "") -> None:
        logger(message)

    emit("=" * 70)
    emit(f"🤖 Training RL agent for {strategy_name}")
    emit("=" * 70)
    emit(f"Symbol: {symbol} | Interval: {interval} | Period: {period} | Episodes: {episodes}")

    df = _fetch_training_data(symbol, period, interval, emit)

    _, feedback_stats = _load_feedback(strategy_name, symbol, min_feedback_signal, emit)

    env = TradingEnvironment(
        df=df,
        lookback_window=lookback_window,
    )

    _apply_feedback_to_environment(env, feedback_stats, emit)

    agent = PPOAgent(
        state_size=env._get_state_size(),
        action_size=env.get_action_space_size(),
        lr=0.0003,
        gamma=0.99,
        clip_epsilon=0.2,
    )

    emit("Starting PPO training...")
    metrics = agent.train(env=env, episodes=episodes, verbose=verbose)

    episode_rewards: List[float] = list(metrics.get("episode_rewards", [])) if isinstance(metrics, dict) else []
    final_avg_reward = None
    if episode_rewards:
        tail = episode_rewards[-10:] if len(episode_rewards) >= 10 else episode_rewards
        final_avg_reward = sum(tail) / len(tail)
        emit(f"Final average reward (last {len(tail)} episodes): {final_avg_reward:.2f}")
        emit(f"Best reward: {max(episode_rewards):.2f} | Worst reward: {min(episode_rewards):.2f}")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(str(model_path))
    emit(f"Saved model to {model_path}")

    result: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "strategy": strategy_name,
        "symbol": symbol,
        "period": period,
        "interval": interval,
        "episodes": episodes,
        "lookback_window": lookback_window,
        "model_path": str(model_path),
        "training_metrics": metrics,
        "episode_rewards": episode_rewards,
        "final_avg_reward": final_avg_reward,
        "feedback_stats": feedback_stats,
        "feedback_trades_used": feedback_stats.get("n_trades", 0),
        "min_feedback_signal": min_feedback_signal,
        "data_rows": int(len(df)),
    }

    if save_summary:
        summary_payload = {
            "timestamp": result["timestamp"],
            "strategy": strategy_name,
            "symbol": symbol,
            "episodes": episodes,
            "final_avg_reward": final_avg_reward,
            "best_reward": max(episode_rewards) if episode_rewards else None,
            "worst_reward": min(episode_rewards) if episode_rewards else None,
            "feedback_trades": feedback_stats.get("n_trades", 0),
            "win_rate": feedback_stats.get("win_rate"),
            "avg_win": feedback_stats.get("avg_win"),
            "avg_loss": feedback_stats.get("avg_loss"),
            "model_path": str(model_path),
        }
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        emit(f"Summary written to {summary_path}")

    if show_tips:
        emit("")
        emit("Next steps:")
        emit("  1. Load the model via live scheduler or enhanced GUI")
        emit("  2. Enable RL decisions and configure thresholds")
        emit("  3. Monitor feedback logs to keep reward shaping fresh")

    emit("=" * 70)
    emit("Training complete.")

    return result


def _train_many(
    strategy_names: Iterable[str],
    overrides: Dict[str, Any],
    verbose: bool,
    log: Callable[[str], None],
    show_tips: bool,
    save_summary: bool,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for name in strategy_names:
        try:
            config = _get_config(name)
            symbols: Sequence[str]
            override_symbols: Optional[Sequence[str]] = overrides.get("symbols")
            if override_symbols:
                symbols = override_symbols
            else:
                symbols = config.all_symbols()

            for sym in symbols:
                result = run_training(
                    strategy_name=name,
                    symbol=sym,
                    episodes=overrides.get("episodes"),
                    period=overrides.get("period"),
                    interval=overrides.get("interval"),
                    lookback_window=overrides.get("lookback_window"),
                    min_feedback_signal=overrides.get("min_feedback_signal"),
                    model_path=overrides.get("model_path"),
                    summary_path=overrides.get("summary_path"),
                    verbose=verbose,
                    log=log,
                    show_tips=show_tips,
                    save_summary=save_summary,
                )
                results.append(result)
        except Exception as exc:  # pragma: no cover - runtime safeguard
            log(f"❌ Training failed for {name}: {exc}")
            raise
    return results


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train PPO RL agents per strategy.")
    parser.add_argument("--strategy", "-s", action="append", help="Strategy to train (repeatable).")
    parser.add_argument("--all", action="store_true", help="Train all registered strategies.")
    parser.add_argument("--episodes", type=int, help="Override number of training episodes.")
    parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Override symbol(s) for data fetch. Repeat the flag for multiples.",
    )
    parser.add_argument("--period", type=str, help="Override data fetch period (e.g. 2y).")
    parser.add_argument("--interval", type=str, help="Override data fetch interval (e.g. 1h).")
    parser.add_argument("--lookback", type=int, dest="lookback_window", help="Override RL lookback window.")
    parser.add_argument(
        "--min-feedback-signal",
        type=float,
        dest="min_feedback_signal",
        help="Minimum signal strength to include feedback trades.",
    )
    parser.add_argument("--model-path", type=str, help="Explicit model save path (applies to single strategy).")
    parser.add_argument("--summary-path", type=str, help="Explicit summary path (single strategy).")
    parser.add_argument("--no-tips", action="store_true", help="Hide post-training tips in output.")
    parser.add_argument("--quiet", action="store_true", help="Disable verbose PPO logging.")
    parser.add_argument("--json", type=str, dest="json_output", help="Write results JSON to this file.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    strategies: List[str]
    if args.all:
        strategies = available_strategies()
    else:
        chosen = args.strategy or [available_strategies()[0]]
        strategies = []
        for name in chosen:
            if name not in DEFAULT_STRATEGY_CONFIGS:
                print(f"Unknown strategy '{name}'. Choices: {', '.join(available_strategies())}")
                return 1
            strategies.append(name)

    if len(strategies) != 1 and (args.model_path or args.summary_path):
        print("Options --model-path and --summary-path require a single strategy run.")
        return 1

    model_override = args.model_path if len(strategies) == 1 else None
    summary_override = args.summary_path if len(strategies) == 1 else None

    if model_override and args.symbols and len(args.symbols) > 1:
        print("--model-path with multiple symbols is ambiguous. Provide a single symbol override.")
        return 1
    if summary_override and args.symbols and len(args.symbols) > 1:
        print("--summary-path with multiple symbols is ambiguous. Provide a single symbol override.")
        return 1

    overrides: Dict[str, Any] = {
        "symbols": args.symbols,
        "episodes": args.episodes,
        "period": args.period,
        "interval": args.interval,
        "lookback_window": args.lookback_window,
        "min_feedback_signal": args.min_feedback_signal,
        "model_path": model_override,
        "summary_path": summary_override,
    }

    log = print
    verbose = not args.quiet
    show_tips = not args.no_tips

    results = _train_many(
        strategies,
        overrides,
        verbose=verbose,
        log=log,
        show_tips=show_tips,
        save_summary=True,
    )

    if args.json_output:
        output_path = Path(args.json_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Results written to {output_path}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Training interrupted by user")
        sys.exit(1)
