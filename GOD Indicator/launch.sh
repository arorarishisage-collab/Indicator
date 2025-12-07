#!/bin/bash
# GOD Indicator - Quick Launch Script

echo "🚀 Launching GOD Indicator Trading System..."
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found"
    echo "   Run setup_production.sh first"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

echo "✅ Python 3 found"
echo ""

# Launch menu
echo "=================================================="
echo "   GOD Indicator - Launch Menu"
echo "=================================================="
echo ""
echo "Choose an option:"
echo ""
echo "1) Beginner Mode GUI (Simple Interface)"
echo "2) Enhanced GUI (Advanced Features)"
echo "3) Run Tests"
echo "4) Setup/Update System"
echo "5) Exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Launching Beginner Mode..."
        python3 app/beginner_mode_gui.py
        ;;
    2)
        echo ""
        echo "🚀 Launching Enhanced GUI..."
        python3 app/enhanced_gui.py
        ;;
    3)
        echo ""
        echo "🧪 Running tests..."
        python3 tests/run_all_tests.py
        ;;
    4)
        echo ""
        echo "🔧 Running setup..."
        ./setup_production.sh
        ;;
    5)
        echo ""
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Invalid choice"
        exit 1
        ;;
esac
