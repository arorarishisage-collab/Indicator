# 🎯 GET STARTED - Complete Setup Guide

## What You Need to Know

Your system has TWO Python environments:

1. **System Python** (`/usr/bin/python3`) - What you've been using ❌
   - Missing `schedule` module
   - Limited packages

2. **Virtual Environment Python** (`.venv/bin/python`) - What you should use ✅
   - Has ALL packages installed
   - Isolated and safe
   - Includes `schedule` module

**Solution**: Use the virtual environment Python

---

## ⚡ Super Quick Start (Copy & Paste)

### One-Time Setup (5 minutes)
```bash
# Go to project
cd /Users/rishi/GOD\ Indicator

# Activate virtual environment
source .venv/bin/activate

# Install/verify all packages
pip install -r requirements.txt

# Test it works
pip install -r requirements.txt
```

You should see:
```
✅ All modules import successfully!
```

### Then: Run Tests
```bash
# Full system test (takes 3 minutes)
python test_system.py

# See working examples
python backend/example_integration.py

# Start 24/7 trading
python -c "from backend.live_scheduler import LiveTradingScheduler; ..."
```

---

## 📋 The Key Command

**Remember this ONE command** - it fixes everything:

```bash
source /Users/rishi/GOD\ Indicator/.venv/bin/activate
```

After running this:
- `python` will use virtual environment Python
- All packages (including `schedule`) will be available
- All your scripts will work

---

## 📱 Shortcut: Use These Aliases

### Setup (do this ONCE):
```bash
# Add these lines to your terminal and press Enter
echo 'export PATH="/Users/rishi/GOD Indicator/.venv/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Then use normally:
```bash
python verify_imports.py   # Works! Uses venv Python
python test_system.py      # Works!
```

---

## 🚀 Full Workflow

### Session 1: Initial Setup
```bash
cd /Users/rishi/GOD\ Indicator
source .venv/bin/activate          # Activate venv
pip install -r requirements.txt    # Install packages (if needed)
python verify_imports.py           # Test it works
```

### Session 2+: Regular Use
```bash
cd /Users/rishi/GOD\ Indicator
source .venv/bin/activate          # Always activate first!
python test_system.py              # Your scripts work now
```

---

## ❓ FAQs

**Q: Why do I need to activate the venv every time?**
A: Virtual environments only apply to the current terminal session. When you open a new terminal, you're back to system Python.

**Q: How do I know if venv is active?**
A: Look at your prompt:
- `(.venv) rishi@...` ← Active ✅
- `rishi@...` ← Not active ❌

**Q: Can I make it activate automatically?**
A: Yes! Add this to `~/.zshrc`:
```bash
cd /Users/rishi/GOD\ Indicator
source .venv/bin/activate
```
Then it activates when you open a new terminal.

**Q: What if I still get errors?**
A: Reinstall packages:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Q: Can I use VS Code?**
A: Yes! Select the Python interpreter:
- Command+Shift+P
- Type "Python: Select Interpreter"
- Choose `.venv/bin/python`

---

## ✅ Verification Checklist

Run these commands (after activating venv):

```bash
# 1. Check Python path
python --version
# Should show: Python 3.9.6

# 2. Check schedule is available
python -c "import schedule; print('✅ schedule installed')"

# 3. Check all modules
python verify_imports.py
# Should show all ✅

# 4. Run full test
python test_system.py
# Should complete without errors
```

---

## 🎯 Your Next Steps

### Right Now (5 minutes):
```bash
cd /Users/rishi/GOD\ Indicator
source .venv/bin/activate
python verify_imports.py
```

### This Session (20 minutes):
```bash
python test_system.py              # Full test
python backend/example_integration.py  # See examples
```

### Today (1 hour):
```bash
# Read quick reference
cat QUICK_REFERENCE.md

# Start 24/7 trading
python -c "
from backend.live_scheduler import LiveTradingScheduler
from backend.ema_strategy import EMA30Strategy
from backend.ict_strategy import ICTStrategy
from backend.data_fetch_yfinance import YFinanceDataFetcher

scheduler = LiveTradingScheduler(
    symbols=['XAUUSD', 'BTC'],
    data_fetcher_class=YFinanceDataFetcher,
    strategy_classes={
        'EMA30Strategy': EMA30Strategy,
        'ICTStrategy': ICTStrategy,
    }
)
scheduler.start()
"
```

---

## 📚 Related Documentation

- `VENV_SETUP.md` - Detailed virtual environment guide
- `SOLUTION.md` - Technical explanation
- `QUICK_REFERENCE.md` - Quick reference card
- `setup_aliases.sh` - Optional aliases setup

---

## 🔧 Troubleshooting Commands

If something goes wrong, run these:

```bash
# 1. Check if venv exists
ls -la /Users/rishi/GOD\ Indicator/.venv/bin/python

# 2. Verify venv activation
echo $VIRTUAL_ENV
# Should show: /Users/rishi/GOD Indicator/.venv

# 3. List installed packages
pip list | grep schedule

# 4. Reinstall everything
pip install -r requirements.txt

# 5. Full reset (if needed)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## ✨ Summary

**Problem**: Wrong Python was being used
**Solution**: Activate virtual environment with one command:
```bash
source /Users/rishi/GOD\ Indicator/.venv/bin/activate
```

**Result**: All packages (including `schedule`) become available

**Time to fix**: < 2 minutes

---

**You're ready! Start with:**
```bash
cd /Users/rishi/GOD\ Indicator && source .venv/bin/activate && python verify_imports.py
```

Then run `python test_system.py` to see your system in action! 🚀
