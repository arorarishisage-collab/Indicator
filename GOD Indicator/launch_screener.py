#!/usr/bin/env python3
"""
Quick Launch - Professional Stock Screener
"""

import subprocess
import sys

print("\n" + "="*60)
print("🎯 GOD Indicator - Professional Stock Screener")
print("="*60)
print("\n🚀 Launching professional screener GUI...")
print("   Find stocks that match YOUR strategy automatically!\n")

# Launch the new professional screener
subprocess.run([sys.executable, "app/professional_screener_gui.py"])
