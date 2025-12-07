#!/bin/bash
# GOD Indicator - Production Setup Script
# Installs all dependencies and prepares the system for trading

echo "=================================================="
echo "   GOD Indicator - Production Setup"
echo "=================================================="
echo ""

# Check Python version
echo "🔍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python version: $PYTHON_VERSION"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "❌ ERROR: Python 3.8+ required"
    exit 1
fi
echo "✅ Python version OK"
echo ""

# Create virtual environment (optional but recommended)
echo "🔨 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "⚠️  Virtual environment already exists"
fi

echo "💡 To activate: source venv/bin/activate"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
echo "   This may take 2-3 minutes..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ All dependencies installed"
else
    echo "❌ ERROR: Failed to install dependencies"
    exit 1
fi
echo ""

# Create .env file if it doesn't exist
echo "🔐 Setting up API keys..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# NewsData.io API (Free tier: 200 calls/day)
# Get your key from: https://newsdata.io
NEWSDATA_API_KEY=pub_351be3c902b4478180538c1f6c2c33d3

# Finnhub API (Free tier: 60 calls/min)
# Get your key from: https://finnhub.io
FINNHUB_API_KEY=d4jv009r01qgcb0voap0d4jv009r01qgcb0voapg

# Zerodha Kite Connect (Optional - ₹2,000/month)
# Get your keys from: https://kite.trade
ZERODHA_API_KEY=your_api_key_here
ZERODHA_API_SECRET=your_api_secret_here
EOF
    echo "✅ Created .env file with default keys"
    echo "⚠️  IMPORTANT: Edit .env to add your Zerodha credentials (if using)"
else
    echo "⚠️  .env file already exists (not overwriting)"
fi
echo ""

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data reports models logs
echo "✅ Directories created"
echo ""

# Run tests
echo "🧪 Running tests to verify installation..."
python3 tests/run_all_tests.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "   ✅ SETUP COMPLETE!"
    echo "=================================================="
    echo ""
    echo "🚀 Quick Start:"
    echo "   1. Edit .env file with your API keys (optional)"
    echo "   2. Run: python3 app/beginner_mode_gui.py"
    echo ""
    echo "📖 Documentation:"
    echo "   • README_PRODUCTION.md - Complete user guide"
    echo "   • VCP_STRATEGY_GUIDE.md - Strategy details"
    echo "   • PRODUCTION_READINESS_AUDIT.md - System status"
    echo ""
    echo "⚠️  REMINDER: This is PAPER TRADING mode by default"
    echo "   No real money is at risk. Perfect for testing!"
    echo ""
    echo "=================================================="
else
    echo ""
    echo "⚠️  Tests failed. Please check error messages above."
    echo "   The system may still work, but some features might be missing."
    echo ""
fi
