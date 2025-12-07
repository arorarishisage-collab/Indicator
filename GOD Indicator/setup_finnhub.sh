#!/bin/bash
# Install Finnhub dependencies and test

echo "================================================"
echo "📦 Installing Finnhub Dependencies"
echo "================================================"
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Install finnhub-python
echo "Installing finnhub-python..."
pip3 install finnhub-python websocket-client requests

echo ""
echo "================================================"
echo "✅ Installation Complete!"
echo "================================================"
echo ""

# Run test
echo "Running Finnhub integration test..."
echo ""
python3 test_finnhub.py

echo ""
echo "================================================"
echo "📚 Documentation"
echo "================================================"
echo ""
echo "File Locations:"
echo "  • Backend: backend/finnhub_data_fetcher.py"
echo "  • GUI Integration: app/beginner_mode_gui.py (updated)"
echo "  • Test Script: test_finnhub.py"
echo ""
echo "Features:"
echo "  ✅ NSE/BSE Indian stocks"
echo "  ✅ US stocks (NASDAQ, NYSE)"
echo "  ✅ Gold, Silver, Commodities"
echo "  ✅ Forex (EUR/USD, GBP/USD, etc.)"
echo "  ✅ Real-time quotes"
echo "  ✅ WebSocket streaming"
echo ""
echo "Try the GUI:"
echo "  python3 app/beginner_mode_gui.py"
echo ""
