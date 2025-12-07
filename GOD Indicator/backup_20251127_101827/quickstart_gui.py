#!/usr/bin/env python3
"""
GUI Application Quick Start
Minimal validation and setup for first-time users
"""

import sys
from pathlib import Path
import json
import subprocess

def print_header(text):
    """Print formatted header."""
    print("\n" + "="*50)
    print(f"  {text}")
    print("="*50 + "\n")

def check_dependencies():
    """Check if required dependencies are installed."""
    print_header("Checking Dependencies")
    
    dependencies = {
        'PyQt5': 'GUI Framework',
        'yfinance': 'Market Data',
        'pandas': 'Data Processing',
        'telegram': 'Alerts',
    }
    
    missing = []
    for dep, desc in dependencies.items():
        try:
            __import__(dep.lower())
            print(f"✓ {dep:<15} ({desc})")
        except ImportError:
            print(f"❌ {dep:<15} ({desc}) - MISSING")
            missing.append(dep)
    
    if missing:
        print(f"\n⚠ Missing dependencies: {', '.join(missing)}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        return False
    
    return True

def check_configuration():
    """Check if configuration exists."""
    print_header("Checking Configuration")
    
    config_file = Path.home() / '.gold_trading_config.json'
    
    if not config_file.exists():
        print("❌ No configuration found")
        print(f"   Location: {config_file}")
        print("\n   Configuration will be created when you:")
        print("   1. Run the GUI application")
        print("   2. Enter Telegram Bot Token (REQUIRED)")
        print("   3. Enter Telegram Chat ID (REQUIRED)")
        print("   4. Click 'Save Config'")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        telegram_token = config.get('telegram_bot_token', '').strip()
        telegram_chat = config.get('telegram_chat_id', '').strip()
        
        print(f"✓ Configuration file found")
        print(f"  Location: {config_file}")
        print(f"  Telegram Token: {'✓ Set' if telegram_token else '❌ Missing'}")
        print(f"  Telegram Chat ID: {'✓ Set' if telegram_chat else '❌ Missing'}")
        
        if telegram_token and telegram_chat:
            print("\n✓ Configuration is complete and ready")
            return True
        else:
            print("\n⚠ Configuration incomplete - re-open GUI and update")
            return False
            
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        return False

def check_data_connectivity():
    """Check connection to data source."""
    print_header("Checking Data Connectivity")
    
    try:
        import yfinance
        print("Testing Yahoo Finance connection...")
        
        # Try to fetch 1 day of data for XAUUSD
        data = yfinance.download('GC=F', period='1d', progress=False)
        
        if len(data) > 0:
            print(f"✓ Connected to Yahoo Finance")
            print(f"  Latest XAUUSD price: ${data['Close'].iloc[-1]:.2f}")
            return True
        else:
            print("❌ No data received from Yahoo Finance")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("   Make sure you have internet connection")
        return False

def run_application():
    """Run the GUI application."""
    print_header("Running GUI Application")
    
    app_path = Path(__file__).parent / 'main.py'
    
    if not app_path.exists():
        print(f"❌ Application file not found: {app_path}")
        return False
    
    print("Starting GUI application...")
    print("(You can close this terminal, the app will stay open)\n")
    
    try:
        # Run with PYTHONUNBUFFERED to see output
        env = {'PYTHONUNBUFFERED': '1'}
        subprocess.Popen([sys.executable, str(app_path)], env=env)
        return True
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        return False

def main():
    """Main quick start workflow."""
    print_header("Gold Trading Signal System - GUI Quick Start")
    
    print("This guide will help you set up and run the application.\n")
    
    steps = [
        ("Dependencies", check_dependencies),
        ("Configuration", check_configuration),
        ("Data Connectivity", check_data_connectivity),
    ]
    
    results = []
    for step_name, step_func in steps:
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"❌ Error in {step_name}: {e}")
            results.append((step_name, False))
    
    # Summary
    print_header("Startup Summary")
    
    for step_name, result in results:
        status = "✓" if result else "❌"
        print(f"{status} {step_name}")
    
    critical_passed = results[0][1]  # Dependencies
    
    if not critical_passed:
        print("\n❌ Cannot proceed - install missing dependencies first:")
        print("   pip install -r requirements.txt")
        return 1
    
    # Launch app
    print("\n" + "="*50)
    print("Launching GUI Application...")
    print("="*50 + "\n")
    
    if run_application():
        print("✓ Application launched successfully!")
        print("\nFirst-Time Setup Checklist:")
        print("  1. Enter Telegram Bot Token (required)")
        print("  2. Enter Telegram Chat ID (required)")
        print("  3. Click 'Validate Config' to verify")
        print("  4. Adjust Strategy Filters if needed")
        print("  5. Click 'Save Config' to persist")
        print("  6. Click 'Run Backtest' to test with real data")
        print("\n✓ Enjoy trading!")
        return 0
    else:
        print("❌ Failed to launch application")
        return 1

if __name__ == '__main__':
    sys.exit(main())
