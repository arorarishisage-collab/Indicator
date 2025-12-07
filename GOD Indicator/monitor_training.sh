#!/bin/bash
# Training Monitor - Check M2 GPU training progress

echo "🔍 M2 GPU Training Monitor"
echo "================================"
echo ""

# Check if training is running
PID=$(pgrep -f "train_intelligent_brain.py")
if [ -z "$PID" ]; then
    echo "❌ Training not running"
    echo ""
    echo "Start with: nohup python3 train_intelligent_brain.py > training_m2_full.log 2>&1 &"
    exit 1
fi

echo "✅ Training running (PID: $PID)"
echo ""

# Show process stats
echo "📊 Resource Usage:"
ps aux | grep $PID | grep -v grep | awk '{printf "   CPU: %s%% | Memory: %s MB\n", $3, $6/1024}'
echo ""

# Show M2 GPU usage (if available)
if command -v powermetrics &> /dev/null; then
    echo "🎮 M2 GPU Usage:"
    sudo powermetrics --samplers gpu_power -i 1000 -n 1 2>/dev/null | grep -A 5 "GPU" | head -6
    echo ""
fi

# Count saved models
MODEL_COUNT=$(ls -1 models/rl_brain/*.pth 2>/dev/null | wc -l | xargs)
echo "💾 Models Saved: $MODEL_COUNT / 12"
echo ""

# Show last 20 lines of log
echo "📝 Recent Log (last 20 lines):"
echo "--------------------------------"
tail -20 training_m2_full.log
echo ""
echo "================================"
echo "Full log: tail -f training_m2_full.log"
