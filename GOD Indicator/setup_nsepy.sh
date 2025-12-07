#!/bin/bash

echo "=================================="
echo "🚀 Installing nsepy for NSE/BSE data"
echo "=================================="

# Install nsepy
pip3 install nsepy --user

echo ""
echo "✅ Installation complete!"
echo ""
echo "Testing nsepy..."
python3 -c "from nsepy import get_history; from datetime import datetime, timedelta; df = get_history(symbol='RELIANCE', start=datetime.now()-timedelta(days=7), end=datetime.now()); print(f'✅ nsepy works! Got {len(df)} candles for RELIANCE')"

echo ""
echo "=================================="
echo "✅ nsepy is ready!"
echo "=================================="
echo ""
echo "Now testing unified data fetcher..."
cd backend && python3 unified_data_fetcher.py
