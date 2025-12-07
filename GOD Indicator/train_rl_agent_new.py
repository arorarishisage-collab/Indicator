#!/usr/bin/env python3
"""Compatibility stub retained to avoid import errors.

This file simply re-exports the main multi-strategy trainer. Prefer using
`train_rl_agent.py` directly. The stub remains so older scripts that import
`train_rl_agent_new` do not break unexpectedly.
"""

from __future__ import annotations

from train_rl_agent import main, run_training  # noqa: F401


if __name__ == "__main__":
    raise SystemExit(main())
