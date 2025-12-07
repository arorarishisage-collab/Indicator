#!/bin/bash
# Quick Setup for New Features
# Installs dependencies for news sentiment and Zerodha integration

echo "🚀 GOD Indicator - Installing New Features"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Install new dependencies
echo "📦 Installing new packages..."
echo ""

# News & Sentiment
echo "1️⃣ Installing news sentiment analysis..."
pip3 install textblob feedparser --quiet
python3 -m textblob.download_corpora --quiet

# Zerodha Kite
echo "2️⃣ Installing Zerodha Kite Connect..."
pip3 install kiteconnect --quiet

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 What's New:"
echo ""
echo "1. 📰 NEWS SENTIMENT ANALYSIS"
echo "   - Analyzes financial news for stocks"
echo "   - Shows sentiment (positive/negative/neutral)"
echo "   - Integrated into beginner mode GUI"
echo ""
echo "2. 🔒 ZERODHA KITE CONNECT (Paper Trading Only)"
echo "   - Real-time data from Zerodha"
echo "   - Historical OHLC data"
echo "   - Live quote streaming"
echo "   - CANNOT place live orders (safety locked)"
echo ""
echo "3. 🎯 BEGINNER MODE GUI"
echo "   - Simplified interface for non-technical users"
echo "   - One-click stock analysis"
echo "   - Plain English recommendations"
echo "   - Paper trading simulator"
echo ""
echo "🚀 Launch Options:"
echo ""
echo "Beginner Mode (Simple):"
echo "  python3 app/beginner_mode_gui.py"
echo ""
echo "Advanced Mode (Full Features):"
echo "  python3 app/enhanced_gui.py"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Try the beginner mode GUI first"
echo "2. Get NewsAPI key (optional): https://newsapi.org"
echo "3. Get Zerodha API credentials (when ready)"
echo "4. Read SIMPLIFICATION_PLAN.md for details"
echo ""
