#!/usr/bin/env python3
"""
macOS App Setup Script (py2app Configuration)
Creates standalone .app bundle for distribution
"""

import sys
from pathlib import Path

try:
    from py2app.setup import setup
    
    setup(
        app=['main.py'],
        options={
            'py2app': {
                'argv_emulation': False,
                'packages': [
                    'backend',
                    'webhooks',
                    'app',
                    'PySide6',
                    'yfinance',
                    'pandas',
                    'numpy',
                    'fastapi',
                    'telegram',
                ],
                'includes': [
                    'backend.data_fetch',
                    'backend.zone_detector',
                    'backend.signal_generator',
                    'backend.backtester',
                    'backend.forward_tester',
                    'app.gui',
                    'app.config_manager',
                ],
                'resources': ['pinescript', 'data', 'config'],
                'plist': {
                    'CFBundleName': 'Gold Trading Signal System',
                    'CFBundleDisplayName': 'Gold Trading',
                    'CFBundleIdentifier': 'com.goldsignals.trading',
                    'CFBundleVersion': '1.0.0',
                    'CFBundleShortVersionString': '1.0.0',
                    'NSPrincipalClass': 'PySide6.QtWidgets.QApplication',
                    'NSHighResolutionCapable': True,
                },
                'semi_standalone': True,
                'arch': 'arm64',  # For Apple Silicon
            }
        },
    )

except ImportError:
    print("py2app not installed.")
    print("Install with: pip install py2app")
    print("\nNote: py2app is optional for development.")
    print("You can run the app directly with: python3 main.py")
    sys.exit(1)
