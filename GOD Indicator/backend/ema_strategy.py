"""EMA crossover strategy with practical trading presets and risk controls."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _StylePreset:
    """Container describing popular EMA combinations."""

    fast: int
    slow: int
    description: str


class EMA30Strategy:
    """Exponential moving-average crossover strategy.

    The strategy plots two EMAs (fast and slow). A bullish signal is issued when the
    fast EMA closes above the slow EMA (golden cross) and a bearish signal when it
    drops back below (death cross). Optional confirmation via RSI and volume attempts
    to reduce whipsaws in sideways markets. Basic risk guidance is provided through
    ATR-based stop-loss and configurable risk/reward targeting.
    """

    STYLE_PRESETS: Dict[str, _StylePreset] = {
        "scalp": _StylePreset(9, 21, "Intraday momentum"),
        "intraday": _StylePreset(9, 21, "Intraday momentum"),
        "swing": _StylePreset(20, 50, "Swing trading trend"),
        "position": _StylePreset(50, 200, "Long-term trend"),
        "long_term": _StylePreset(50, 200, "Long-term trend"),
    }

    def __init__(
        self,
        fast_period: int = 9,
        slow_period: int = 21,
        *,
        style: Optional[str] = None,
        confirm_with_rsi: bool = True,
        confirm_with_volume: bool = True,
        confirm_with_trend: bool = True,
        rsi_period: int = 14,
        rsi_buy_threshold: float = 45.0,
        rsi_sell_threshold: float = 55.0,
        volume_lookback: int = 20,
        atr_period: int = 14,
        stop_lookback: int = 10,
        atr_stop_multiplier: float = 1.5,
        risk_reward: float = 2.0,
    ) -> None:
        if style:
            preset = self._resolve_style(style)
            fast_period, slow_period = preset.fast, preset.slow
            logger.info(
                "EMA30Strategy using '%s' preset (%s EMA / %s EMA) - %s",
                style,
                fast_period,
                slow_period,
                preset.description,
            )

        if fast_period >= slow_period:
            raise ValueError("fast_period must be smaller than slow_period for a crossover strategy")

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.confirm_with_rsi = confirm_with_rsi
        self.confirm_with_volume = confirm_with_volume
        self.confirm_with_trend = confirm_with_trend
        self.rsi_period = rsi_period
        self.rsi_buy_threshold = rsi_buy_threshold
        self.rsi_sell_threshold = rsi_sell_threshold
        self.volume_lookback = volume_lookback
        self.atr_period = atr_period
        self.stop_lookback = stop_lookback
        self.atr_stop_multiplier = atr_stop_multiplier
        self.risk_reward = risk_reward
        self.name = f"EMA{self.fast_period}_{self.slow_period}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return EMA crossover signals for the supplied OHLCV data."""

        if df is None or df.empty:
            return pd.DataFrame()

        # Use a defensive copy to avoid mutating caller data.
        data = df.copy()
        data = data.dropna(subset=["Close"]).sort_index()

        if len(data) < self.slow_period + 2:
            logger.warning("Not enough observations (%s) for slow EMA %s", len(data), self.slow_period)
            return pd.DataFrame()

        if "Volume" not in data.columns:
            data["Volume"] = 0.0

        self._compute_core_indicators(data)
        self._compute_risk_metrics(data)
        self._apply_cross_logic(data)
        self._apply_confirmations(data)
        self._calculate_signal_strength(data)
        self._plan_trade_levels(data)

        output_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "EMA_Fast",
            "EMA_Slow",
            "Trend",
            "Signal",
            "Signal_Strength",
            "Crossover",
            "RSI",
            "Volume_Ratio",
            "ATR",
            "Stop_Loss",
            "Take_Profit",
            "Risk_Per_Share",
        ]

        present = [col for col in output_columns if col in data.columns]
        return data[present]

    # ------------------------------------------------------------------
    # Indicator calculation helpers
    # ------------------------------------------------------------------
    def _compute_core_indicators(self, data: pd.DataFrame) -> None:
        data["EMA_Fast"] = data["Close"].ewm(span=self.fast_period, adjust=False).mean()
        data["EMA_Slow"] = data["Close"].ewm(span=self.slow_period, adjust=False).mean()
        data["Trend"] = np.where(data["EMA_Fast"] > data["EMA_Slow"], 1, -1)
        data["EMA_Distance"] = (data["EMA_Fast"] - data["EMA_Slow"]) / data["EMA_Slow"].replace(0, np.nan)
        data["Return_5d"] = data["Close"].pct_change(5)

        if self.confirm_with_rsi:
            data["RSI"] = self._compute_rsi(data["Close"], self.rsi_period)
        else:
            data["RSI"] = np.nan

        if self.confirm_with_volume:
            vol_ma = data["Volume"].rolling(self.volume_lookback, min_periods=1).mean()
            data["Volume_Ratio"] = data["Volume"] / vol_ma.replace(0, np.nan)
        else:
            data["Volume_Ratio"] = np.nan

    def _compute_risk_metrics(self, data: pd.DataFrame) -> None:
        high_low = data["High"] - data["Low"]
        high_close = (data["High"] - data["Close"].shift(1)).abs()
        low_close = (data["Low"] - data["Close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data["ATR"] = true_range.rolling(self.atr_period, min_periods=1).mean()
        data["Swing_Low"] = data["Low"].rolling(self.stop_lookback, min_periods=1).min()
        data["Swing_High"] = data["High"].rolling(self.stop_lookback, min_periods=1).max()

    # ------------------------------------------------------------------
    # Signal logic and confirmation
    # ------------------------------------------------------------------
    def _apply_cross_logic(self, data: pd.DataFrame) -> None:
        fast_above = data["EMA_Fast"] > data["EMA_Slow"]
        fast_above_prev = fast_above.shift(1)

        cross_up = fast_above & (~fast_above_prev)
        cross_down = (~fast_above) & fast_above_prev

        data["Signal"] = 0
        data.loc[cross_up, "Signal"] = 1
        data.loc[cross_down, "Signal"] = -1

        data["Crossover"] = "Hold"
        data.loc[cross_up, "Crossover"] = "Golden"
        data.loc[cross_down, "Crossover"] = "Death"

    def _apply_confirmations(self, data: pd.DataFrame) -> None:
        if not (self.confirm_with_rsi or self.confirm_with_volume or self.confirm_with_trend):
            return

        buy_mask = data["Signal"] == 1
        sell_mask = data["Signal"] == -1

        if self.confirm_with_trend:
            buy_mask &= data["Trend"] == 1
            sell_mask &= data["Trend"] == -1

        if self.confirm_with_rsi:
            buy_mask &= data["RSI"] >= self.rsi_buy_threshold
            sell_mask &= data["RSI"] <= self.rsi_sell_threshold

        if self.confirm_with_volume:
            volume_ok = data["Volume_Ratio"].fillna(0) >= 1.0
            buy_mask &= volume_ok
            sell_mask &= volume_ok

        filtered_signal = np.zeros(len(data), dtype=int)
        filtered_signal[buy_mask.to_numpy()] = 1
        filtered_signal[sell_mask.to_numpy()] = -1
        data["Signal"] = filtered_signal

    # ------------------------------------------------------------------
    # Strength and trade management
    # ------------------------------------------------------------------
    def _calculate_signal_strength(self, data: pd.DataFrame) -> None:
        distance_score = np.clip(data["EMA_Distance"].fillna(0) * 100, -3.0, 3.0)
        trend_score = np.where(data["Trend"] == 1, 0.75, -0.75)
        momentum_score = np.clip(data["Return_5d"].fillna(0) * 100 / 4, -2.0, 2.0)

        if self.confirm_with_rsi:
            rsi_scaled = ((data["RSI"] - 50) / 10).replace([np.inf, -np.inf], 0).fillna(0)
            rsi_score = np.clip(rsi_scaled, -2.0, 2.0)
        else:
            rsi_score = 0

        if self.confirm_with_volume:
            volume_score = np.clip((data["Volume_Ratio"].fillna(1.0) - 1.0) * 1.5, -1.0, 1.0)
        else:
            volume_score = 0

        base_strength = 5.0
        strength = base_strength + distance_score + trend_score + momentum_score + rsi_score + volume_score
        data["Signal_Strength"] = np.clip(strength, 0.0, 10.0)

        inactive = data["Signal"] == 0
        data.loc[inactive, "Signal_Strength"] = 0.0

    def _plan_trade_levels(self, data: pd.DataFrame) -> None:
        data["Stop_Loss"] = np.nan
        data["Take_Profit"] = np.nan
        data["Risk_Per_Share"] = np.nan

        if self.risk_reward <= 0:
            return

        atr_buffer = data["ATR"] * self.atr_stop_multiplier

        buy_mask = data["Signal"] == 1
        sell_mask = data["Signal"] == -1

        buy_stop = np.minimum(data["Swing_Low"], data["Close"] - atr_buffer)
        sell_stop = np.maximum(data["Swing_High"], data["Close"] + atr_buffer)

        data.loc[buy_mask, "Stop_Loss"] = buy_stop[buy_mask]
        data.loc[sell_mask, "Stop_Loss"] = sell_stop[sell_mask]

        buy_risk = (data["Close"] - data["Stop_Loss"]).abs()
        sell_risk = (data["Stop_Loss"] - data["Close"]).abs()

        risk = buy_risk.where(buy_mask, sell_risk)
        data.loc[buy_mask | sell_mask, "Risk_Per_Share"] = risk[buy_mask | sell_mask]

        data.loc[buy_mask, "Take_Profit"] = data.loc[buy_mask, "Close"] + (risk[buy_mask] * self.risk_reward)
        data.loc[sell_mask, "Take_Profit"] = data.loc[sell_mask, "Close"] - (risk[sell_mask] * self.risk_reward)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _resolve_style(self, style: str) -> _StylePreset:
        key = style.strip().lower()
        if key not in self.STYLE_PRESETS:
            raise ValueError(f"Unknown style preset '{style}'. Available: {', '.join(self.STYLE_PRESETS)}")
        return self.STYLE_PRESETS[key]

    @staticmethod
    def _compute_rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)

        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(method="bfill").fillna(50)


__all__ = ["EMA30Strategy"]
