#!/usr/bin/env python3
"""
🚀 ONE COMMAND TO RULE THEM ALL
Launches complete production trading system
"""

import sys
import subprocess
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Launch production dashboard."""
    print("\n" + "=" * 80)
    print("🚀 LAUNCHING COMPLETE TRADING SYSTEM")
    print("=" * 80)
    print("✓ Auto-starting 3 strategies (EMA/ICT/VCP)")
    print("✓ Live monitoring dashboard")
    print("✓ Paper trading mode (safe)")
    print("=" * 80 + "\n")
    
    # Launch production dashboard
    subprocess.run([sys.executable, "launch_production.py"])


if __name__ == "__main__":
    main()
