"""Utilities for consuming RL feedback logs and deriving training signals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

DATA_DIR = Path("reports/rl_feedback")
JSONL_FILE = DATA_DIR / "experiences.jsonl"


def load_feedback_dataframe() -> pd.DataFrame:
    """Return the experience log as a DataFrame (empty if none available)."""
    if not JSONL_FILE.exists():
        return pd.DataFrame()

    records = []
    with JSONL_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(records)


def summarise_feedback(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute aggregate statistics required for reward shaping."""
    if df.empty:
        return {
            "n_trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "direction_bias": {},
            "loss_penalty": 0.0,
        }

    work_df = df.copy()

    for col in ("pnl_percent", "pnl", "signal_strength", "risk_percent"):
        if col in work_df.columns:
            work_df[col] = pd.to_numeric(work_df[col], errors="coerce")

    wins = work_df[work_df["win"] == True]
    losses = work_df[work_df["win"] == False]

    avg_win = wins["pnl_percent"].mean() if not wins.empty else 0.0
    avg_loss = losses["pnl_percent"].mean() if not losses.empty else 0.0

    win_rate = float((work_df["win"] == True).mean()) if "win" in work_df else 0.0

    direction_bias = {}
    if "direction" in work_df.columns:
        grouped = work_df.groupby("direction")
        baseline = win_rate if win_rate else 0.5
        for direction, sub_df in grouped:
            direction_win_rate = float((sub_df["win"] == True).mean()) if not sub_df.empty else baseline
            direction_bias[direction] = direction_win_rate - baseline

    loss_penalty = abs(avg_loss) / 100 if avg_loss else 0.0

    return {
        "n_trades": int(len(work_df)),
        "win_rate": float(win_rate),
        "avg_win": float(avg_win or 0.0),
        "avg_loss": float(avg_loss or 0.0),
        "direction_bias": direction_bias,
        "loss_penalty": float(loss_penalty),
    }


def action_bias_from_stats(stats: Dict[str, Any], scale: float = 0.05) -> Dict[int, float]:
    """Map BUY/SELL bias to PPO action space indices."""
    bias_map: Dict[int, float] = {}
    direction_bias = stats.get("direction_bias", {}) or {}

    buy_bias = direction_bias.get("BUY", 0.0)
    sell_bias = direction_bias.get("SELL", 0.0)

    bias_map[1] = max(-scale, min(scale, buy_bias * scale))
    bias_map[2] = max(-scale, min(scale, sell_bias * scale))

    return bias_map


def win_rate_target_from_stats(stats: Dict[str, Any]) -> float:
    """Derive a dynamic win-rate target for reward shaping."""
    base = stats.get("win_rate", 0.5)
    return max(0.4, min(0.75, base))


def loss_penalty_from_stats(stats: Dict[str, Any], max_penalty: float = 0.05) -> float:
    penalty = stats.get("loss_penalty", 0.0)
    return max(0.0, min(max_penalty, penalty))
