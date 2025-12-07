#!/usr/bin/env python3
"""
Quick launcher for Enhanced GUI
Ensures dependencies and launches the enhanced interface
"""

import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check and install required dependencies"""
    try:
        import PySide6
        return True
    except ImportError:
        print("⚠️  PySide6 not installed")
        response = input("Install PySide6 now? (y/n): ")
        if response.lower() == 'y':
            print("Installing PySide6...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PySide6'])
            return True
        return False

def main():
    print("🚀 Gold Trading System - Enhanced GUI Launcher")
    print("=" * 50)
    
    if not check_dependencies():
        print("\n❌ PySide6 required. Install with:")
        print("   pip install PySide6")
        sys.exit(1)
    
    print("\n✨ Launching Enhanced GUI with:")
    print("   • Multi-Pair Support (XAUUSD, XAUEUR, XAUGBP)")
    print("   • CSV Upload Capability")
    print("   • Live Signal Dashboard")
    print("   • Enhanced Discord Alerts")
    print()
    
    # Import and launch
    sys.path.insert(0, str(Path(__file__).parent))
    from app.enhanced_gui import main as gui_main
    gui_main()

if __name__ == '__main__':
    main()
