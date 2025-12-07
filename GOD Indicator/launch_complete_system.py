#!/usr/bin/env python3
"""
Complete System Launcher - Starts GUI + Live Scheduler Together
"""

import subprocess
import sys
import time
from pathlib import Path
import signal
import os

def main():
    """Launch both GUI and scheduler in parallel."""
    
    print("=" * 60)
    print("🚀 GOLD TRADING SYSTEM - COMPLETE LAUNCHER")
    print("=" * 60)
    print()
    print("This will start:")
    print("  1. Live Scheduler (background) - Generates trading signals")
    print("  2. Enhanced GUI (foreground) - Monitor & backtest")
    print()
    print("Press Ctrl+C to stop both processes")
    print("=" * 60)
    print()
    
    # Get the current directory
    base_dir = Path(__file__).parent
    
    # Start scheduler in background
    print("🔄 Starting live scheduler...")
    scheduler_script = base_dir / "backend" / "live_scheduler.py"
    
    if not scheduler_script.exists():
        print(f"❌ Error: {scheduler_script} not found!")
        sys.exit(1)
    
    scheduler_process = subprocess.Popen(
        [sys.executable, str(scheduler_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    print(f"✓ Scheduler started (PID: {scheduler_process.pid})")
    time.sleep(2)  # Give scheduler time to initialize
    
    # Start GUI in foreground
    print("🖥️  Starting enhanced GUI...")
    gui_script = base_dir / "launch_enhanced.py"
    
    if not gui_script.exists():
        print(f"❌ Error: {gui_script} not found!")
        scheduler_process.terminate()
        sys.exit(1)
    
    try:
        # Run GUI - this blocks until GUI is closed
        gui_process = subprocess.Popen(
            [sys.executable, str(gui_script)],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        print(f"✓ GUI started (PID: {gui_process.pid})")
        print()
        print("=" * 60)
        print("✅ SYSTEM RUNNING")
        print("=" * 60)
        print()
        print("📡 Scheduler: Generating live signals in background")
        print("🖥️  GUI: Check 'Live Signals' tab for real-time updates")
        print()
        print("Press Ctrl+C or close the GUI to stop everything")
        print()
        
        # Wait for GUI to finish
        gui_process.wait()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Shutting down...")
    finally:
        # Clean up both processes
        print("🛑 Stopping scheduler...")
        scheduler_process.terminate()
        try:
            scheduler_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            scheduler_process.kill()
        
        if 'gui_process' in locals():
            try:
                gui_process.terminate()
                gui_process.wait(timeout=5)
            except:
                pass
        
        print("✓ All processes stopped")
        print("👋 Goodbye!")


if __name__ == '__main__':
    main()
