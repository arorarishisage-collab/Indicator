#!/bin/bash
# Stop GOD Indicator Trading System

echo "🛑 Stopping GOD Indicator Trading System..."

# Check if PID files exist
if [ -f logs/gui.pid ]; then
    GUI_PID=$(cat logs/gui.pid)
    if kill -0 $GUI_PID 2>/dev/null; then
        kill $GUI_PID
        echo "   ✓ GUI stopped (PID: $GUI_PID)"
    else
        echo "   ⊝ GUI not running"
    fi
    rm logs/gui.pid
else
    # Fallback: kill by process name
    pkill -f 'enhanced_gui.py' && echo "   ✓ GUI stopped" || echo "   ⊝ GUI not running"
fi

if [ -f logs/scheduler.pid ]; then
    SCHEDULER_PID=$(cat logs/scheduler.pid)
    if kill -0 $SCHEDULER_PID 2>/dev/null; then
        kill $SCHEDULER_PID
        echo "   ✓ Scheduler stopped (PID: $SCHEDULER_PID)"
    else
        echo "   ⊝ Scheduler not running"
    fi
    rm logs/scheduler.pid
else
    # Fallback: kill by process name
    pkill -f 'live_scheduler.py' && echo "   ✓ Scheduler stopped" || echo "   ⊝ Scheduler not running"
fi

echo ""
echo "✅ System stopped"
