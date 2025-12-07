"""
RL feedback logging utilities.
Collects paper-trade outcomes so that reinforcement learning can use
real execution results as an experience dataset.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def _to_builtin(value: Any) -> Any:
    """Convert numpy/pandas types to builtin Python types for serialization."""
    if isinstance(value, (float, int, str, bool)) or value is None:
        return value
    if isinstance(value, (datetime, )):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, (list, tuple, set)):
        return [_to_builtin(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_builtin(v) for k, v in value.items()}
    return str(value)


def _sanitize_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not context:
        return {}
    return {str(key): _to_builtin(value) for key, value in context.items()}


@dataclass
class RLExperienceLogger:
    base_dir: Path = Path("reports/rl_feedback")
    csv_filename: str = "experiences.csv"
    jsonl_filename: str = "experiences.jsonl"

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.base_dir / self.csv_filename
        self.jsonl_path = self.base_dir / self.jsonl_filename

        if not self.csv_path.exists():
            header = (
                "logged_at,trade_id,symbol,strategy,direction,entry_time,exit_time,"
                "holding_minutes,entry_price,exit_price,pnl,pnl_percent,win,"
                "signal_strength,risk_percent,timeframe,regime,rl_confidence,rl_reason,"
                "stop_loss,take_profit,context_json"
            )
            self.csv_path.write_text(header + "\n", encoding="utf-8")

    def log_trade(
        self,
        trade,
        trade_meta: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a single trade outcome to CSV and JSONL."""
        sanitized_context = _sanitize_context(context)

        entry_time = getattr(trade, "entry_time", None)
        exit_time = getattr(trade, "exit_time", None)
        holding_minutes = None
        if entry_time and exit_time:
            holding_minutes = (exit_time - entry_time).total_seconds() / 60.0

        record = {
            "logged_at": datetime.utcnow().isoformat(),
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "strategy": trade.strategy,
            "direction": "BUY" if trade.direction == 1 else "SELL",
            "entry_time": entry_time.isoformat() if entry_time else None,
            "exit_time": exit_time.isoformat() if exit_time else None,
            "holding_minutes": holding_minutes,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "pnl": trade.pnl,
            "pnl_percent": trade.pnl_percent,
            "win": trade.win,
            "signal_strength": trade.signal_strength,
            "risk_percent": trade_meta.get("risk_percent"),
            "timeframe": sanitized_context.get("timeframe"),
            "regime": sanitized_context.get("regime"),
            "rl_confidence": sanitized_context.get("rl_confidence"),
            "rl_reason": sanitized_context.get("rl_reason"),
            "stop_loss": trade_meta.get("stop_loss") or trade_meta.get("initial_stop_loss"),
            "take_profit": trade_meta.get("take_profit"),
            "context": sanitized_context,
        }

        self._append_jsonl(record)
        self._append_csv(record)

    def _append_jsonl(self, record: Dict[str, Any]) -> None:
        line = json.dumps(record, default=_to_builtin)
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _append_csv(self, record: Dict[str, Any]) -> None:
        context_json = json.dumps(record.get("context", {}), default=_to_builtin)
        csv_line = (
            f"{record['logged_at']},{record['trade_id']},{record['symbol']},"
            f"{record['strategy']},{record['direction']},{record['entry_time'] or ''},"
            f"{record['exit_time'] or ''},{record['holding_minutes'] or ''},"
            f"{record['entry_price']},{record['exit_price']},"
            f"{record['pnl']},{record['pnl_percent']},{record['win']},"
            f"{record['signal_strength']},{record['risk_percent'] or ''},"
            f"{record['timeframe'] or ''},{record['regime'] or ''},"
            f"{record['rl_confidence'] or ''},{record['rl_reason'] or ''},"
            f"{record['stop_loss'] or ''},{record['take_profit'] or ''},"
            f"""{context_json}"""
        )
        with self.csv_path.open("a", encoding="utf-8") as handle:
            handle.write(csv_line + "\n")

    def export_dataframe(self) -> pd.DataFrame:
        """Load the JSONL log as a DataFrame for analysis."""
        if not self.jsonl_path.exists():
            return pd.DataFrame()

        rows = [json.loads(line) for line in self.jsonl_path.read_text(encoding="utf-8").splitlines() if line]
        return pd.DataFrame(rows)
