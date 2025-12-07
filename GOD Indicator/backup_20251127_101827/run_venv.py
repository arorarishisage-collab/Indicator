#!/usr/bin/env python3
"""
Activate virtual environment and run tests
Use this instead of running python directly
"""

import subprocess
import sys
import os
from pathlib import Path

# Get the project root
project_root = Path(__file__).parent
venv_python = project_root / '.venv' / 'bin' / 'python'

if not venv_python.exists():
    print("❌ Virtual environment not found!")
    print("")
    print("Please create it with:")
    print("  cd /Users/rishi/GOD\\ Indicator")
    print("  python3 -m venv .venv")
    print("  source .venv/bin/activate")
    print("  pip install -r requirements.txt")
    sys.exit(1)

print("🔧 Using virtual environment Python")
print(f"   Path: {venv_python}")
print("")

# Run verify_imports in the venv
print("Running import verification...")
print("")
result = subprocess.run([str(venv_python), str(project_root / 'verify_imports.py')])

if result.returncode == 0:
    print("")
    print("=" * 80)
    print("✅ All imports successful!")
    print("=" * 80)
    print("")
    print("You can now run:")
    print("  /Users/rishi/GOD\\ Indicator/.venv/bin/python test_system.py")
    print("  /Users/rishi/GOD\\ Indicator/.venv/bin/python backend/example_integration.py")
    print("")
    print("Or use this helper:")
    print("  python run_venv.py test_system.py")
    print("  python run_venv.py backend/example_integration.py")
else:
    print("")
    print("❌ Some imports failed")
    sys.exit(1)
