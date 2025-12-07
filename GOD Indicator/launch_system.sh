#!/bin/bash
# Launch GOD Indicator - Complete Trading System
# Runs GUI and Live Scheduler simultaneously

echo "🚀 Launching GOD Indicator Trading System..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.9+"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Launch GUI in background
echo "📊 Starting GUI..."
python3 app/enhanced_gui.py > logs/gui.log 2>&1 &
GUI_PID=$!
echo "   GUI running (PID: $GUI_PID)"

# Wait a moment for GUI to initialize
sleep 2

# Launch Live Scheduler in background
echo "⚙️  Starting Live Scheduler..."
python3 backend/live_scheduler.py > logs/scheduler.log 2>&1 &
SCHEDULER_PID=$!
echo "   Scheduler running (PID: $SCHEDULER_PID)"

echo ""
echo "✅ System launched successfully!"
echo ""
echo "📋 Process IDs:"
echo "   GUI: $GUI_PID"
echo "   Scheduler: $SCHEDULER_PID"
echo ""
echo "📝 Logs:"
echo "   GUI: logs/gui.log"
echo "   Scheduler: logs/scheduler.log"
echo ""
echo "To stop the system:"
echo "   kill $GUI_PID $SCHEDULER_PID"
echo ""
echo "Or use: pkill -f 'enhanced_gui.py' && pkill -f 'live_scheduler.py'"
echo ""

# Save PIDs to file for easy stopping
echo "$GUI_PID" > logs/gui.pid
echo "$SCHEDULER_PID" > logs/scheduler.pid

# Wait for user to press Ctrl+C
trap "echo ''; echo '🛑 Stopping system...'; kill $GUI_PID $SCHEDULER_PID 2>/dev/null; echo '✅ System stopped'; exit 0" INT

echo "Press Ctrl+C to stop both processes..."
wait
