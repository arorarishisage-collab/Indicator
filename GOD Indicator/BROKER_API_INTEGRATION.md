# 🔌 Broker API Integration Guide - Grow/Zerodha

## Overview

Your GOD Indicator system will integrate with **Grow** or **Zerodha** broker APIs to:
- ✅ Fetch **historical data** for backtesting
- ✅ Fetch **live market data** for real-time signal generation
- ✅ **Send signals to Discord** (NO automatic trade execution)

**Important**: The system will **NOT** place trades automatically. You'll receive signals via Discord and place trades manually.

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   GOD Indicator System                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ├─→ Fetch Historical Data (Backtesting)
                          │   
                          ├─→ Fetch Live Data (Real-time)
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              Grow/Zerodha API Integration                    │
│  - WebSocket for live streaming                             │
│  - REST API for historical data                             │
│  - NO order placement                                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ├─→ Strategy Analysis
                          │   • EMA30
                          │   • ICT
                          │   • VCP (NEW)
                          │
                          ├─→ Signal Generation
                          │   • Buy/Sell signals
                          │   • Entry, SL, TP levels
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   Discord Webhook                           │
│  - Signal alerts sent automatically                          │
│  - User places trades manually                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 API Credentials Setup

### **Option 1: Zerodha Kite Connect**

1. **Create Kite Connect App**:
   - Go to https://developers.kite.trade/
   - Create app → Get API Key & Secret
   - Set redirect URL: `http://localhost:8080`

2. **Get Access Token** (Daily):
   ```python
   from kiteconnect import KiteConnect
   
   api_key = "your_api_key"
   api_secret = "your_api_secret"
   kite = KiteConnect(api_key=api_key)
   
   # Generate login URL
   login_url = kite.login_url()
   print(f"Login here: {login_url}")
   
   # After login, you'll get request_token from redirect URL
   request_token = "token_from_redirect"
   
   # Generate access token (valid for 1 day)
   data = kite.generate_session(request_token, api_secret=api_secret)
   access_token = data["access_token"]
   ```

3. **Save to Config**:
   ```yaml
   # config/broker.yaml
   broker: "zerodha"
   api_key: "your_api_key"
   api_secret: "your_api_secret"
   access_token: "your_access_token"  # Refresh daily
   ```

### **Option 2: Grow App API**

1. **Contact Grow Support**:
   - Email: support@groww.in
   - Request API access for algorithmic trading
   - Get API credentials

2. **Save to Config**:
   ```yaml
   # config/broker.yaml
   broker: "grow"
   api_key: "your_grow_api_key"
   api_secret: "your_grow_secret"
   ```

---

## 📊 Historical Data Fetching

### **Create Broker Data Fetcher**

```python
# backend/data_fetch_broker.py
"""
Broker API Data Fetcher (Grow/Zerodha)
Fetches both historical and live data
"""

from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import yaml


class BrokerDataFetcher:
    """Fetch data from Zerodha/Grow API."""
    
    def __init__(self, config_path: str = 'config/broker.yaml'):
        """Initialize with broker credentials."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.broker = self.config['broker']
        
        if self.broker == 'zerodha':
            self.kite = KiteConnect(api_key=self.config['api_key'])
            self.kite.set_access_token(self.config['access_token'])
        elif self.broker == 'grow':
            # Initialize Grow API client (when available)
            pass
    
    def fetch_historical_data(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
        interval: str = 'day'
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.
        
        Args:
            symbol: Trading symbol (e.g., 'SBIN', 'INFY')
            from_date: Start date
            to_date: End date
            interval: 'minute', '5minute', '15minute', '60minute', 'day'
            
        Returns:
            DataFrame with OHLCV data
        """
        if self.broker == 'zerodha':
            return self._fetch_zerodha_historical(symbol, from_date, to_date, interval)
        elif self.broker == 'grow':
            return self._fetch_grow_historical(symbol, from_date, to_date, interval)
    
    def _fetch_zerodha_historical(
        self, 
        symbol: str, 
        from_date: datetime, 
        to_date: datetime,
        interval: str
    ) -> pd.DataFrame:
        """Fetch from Zerodha Kite Connect."""
        # Get instrument token
        instruments = self.kite.instruments("NSE")
        instrument = next((i for i in instruments if i['tradingsymbol'] == symbol), None)
        
        if not instrument:
            raise ValueError(f"Symbol {symbol} not found")
        
        instrument_token = instrument['instrument_token']
        
        # Fetch historical data
        data = self.kite.historical_data(
            instrument_token=instrument_token,
            from_date=from_date,
            to_date=to_date,
            interval=interval
        )
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        
        df.set_index('Date', inplace=True)
        return df
    
    def _fetch_grow_historical(
        self, 
        symbol: str, 
        from_date: datetime, 
        to_date: datetime,
        interval: str
    ) -> pd.DataFrame:
        """Fetch from Grow API (implement when API available)."""
        # TODO: Implement Grow API integration
        raise NotImplementedError("Grow API integration pending")
    
    def fetch_live_price(self, symbol: str) -> dict:
        """
        Fetch current live price.
        
        Returns:
            dict with 'ltp' (last traded price), 'volume', etc.
        """
        if self.broker == 'zerodha':
            instruments = self.kite.instruments("NSE")
            instrument = next((i for i in instruments if i['tradingsymbol'] == symbol), None)
            
            if not instrument:
                raise ValueError(f"Symbol {symbol} not found")
            
            instrument_token = instrument['instrument_token']
            quote = self.kite.quote([f"NSE:{symbol}"])
            
            return {
                'symbol': symbol,
                'ltp': quote[f"NSE:{symbol}"]['last_price'],
                'volume': quote[f"NSE:{symbol}"]['volume'],
                'open': quote[f"NSE:{symbol}"]['ohlc']['open'],
                'high': quote[f"NSE:{symbol}"]['ohlc']['high'],
                'low': quote[f"NSE:{symbol}"]['ohlc']['low'],
                'close': quote[f"NSE:{symbol}"]['ohlc']['close'],
            }
        elif self.broker == 'grow':
            # TODO: Implement Grow API
            raise NotImplementedError("Grow API integration pending")


# Example usage
if __name__ == "__main__":
    fetcher = BrokerDataFetcher()
    
    # Fetch 1 year of daily data
    from_date = datetime.now() - timedelta(days=365)
    to_date = datetime.now()
    
    df = fetcher.fetch_historical_data(
        symbol='SBIN',
        from_date=from_date,
        to_date=to_date,
        interval='day'
    )
    
    print(f"Fetched {len(df)} bars for SBIN")
    print(df.tail())
    
    # Fetch live price
    live = fetcher.fetch_live_price('SBIN')
    print(f"\nLive price: ₹{live['ltp']}")
```

---

## 🔴 Live Data Streaming

### **WebSocket Integration**

```python
# backend/live_data_stream.py
"""
Live market data streaming from broker
"""

from kiteconnect import KiteTicker
import logging

logger = logging.getLogger(__name__)


class LiveDataStream:
    """Stream live market data via WebSocket."""
    
    def __init__(self, api_key: str, access_token: str, on_tick_callback):
        """
        Initialize live stream.
        
        Args:
            api_key: Broker API key
            access_token: Broker access token
            on_tick_callback: Function to call on each tick
        """
        self.kws = KiteTicker(api_key, access_token)
        self.on_tick_callback = on_tick_callback
        
        # Set callbacks
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect
        self.kws.on_close = self.on_close
        self.kws.on_error = self.on_error
        
        self.tokens = []
    
    def add_symbols(self, instrument_tokens: list):
        """Add symbols to stream."""
        self.tokens.extend(instrument_tokens)
    
    def start(self):
        """Start streaming."""
        logger.info(f"Starting live data stream for {len(self.tokens)} symbols")
        self.kws.connect(threaded=True)
    
    def stop(self):
        """Stop streaming."""
        self.kws.close()
    
    def on_ticks(self, ws, ticks):
        """Called when ticks are received."""
        for tick in ticks:
            self.on_tick_callback(tick)
    
    def on_connect(self, ws, response):
        """Called when connected."""
        logger.info("WebSocket connected, subscribing to tokens...")
        ws.subscribe(self.tokens)
        ws.set_mode(ws.MODE_FULL, self.tokens)
    
    def on_close(self, ws, code, reason):
        """Called when disconnected."""
        logger.warning(f"WebSocket closed: {code} - {reason}")
    
    def on_error(self, ws, code, reason):
        """Called on error."""
        logger.error(f"WebSocket error: {code} - {reason}")


# Example usage
def handle_tick(tick):
    """Process each tick."""
    print(f"Symbol: {tick['instrument_token']}, LTP: {tick['last_price']}")
    # Run strategy analysis here
    # Generate signals if conditions met
    # Send to Discord

if __name__ == "__main__":
    stream = LiveDataStream(
        api_key="your_api_key",
        access_token="your_access_token",
        on_tick_callback=handle_tick
    )
    
    # Add symbols (use instrument tokens)
    stream.add_symbols([738561])  # SBIN
    
    # Start streaming
    stream.start()
```

---

## 🔗 Integration with Live Scheduler

### **Update Live Scheduler**

```python
# backend/live_scheduler.py (add to existing file)

from backend.data_fetch_broker import BrokerDataFetcher

class LiveScheduler:
    def __init__(self):
        # ... existing code ...
        
        # Add broker data fetcher
        self.broker_fetcher = BrokerDataFetcher('config/broker.yaml')
    
    def _run_profile_job(self, profile_name: str):
        """Execute scheduled job - now using broker API."""
        # ... existing code ...
        
        try:
            # OLD: df = self.data_manager.load_source(profile.data_source)
            
            # NEW: Fetch from broker API
            symbol = cfg['symbol']
            interval = profile.data_source.get('interval', '1d')
            
            # Fetch historical data for strategy
            from_date = datetime.now() - timedelta(days=365)
            to_date = datetime.now()
            
            df = self.broker_fetcher.fetch_historical_data(
                symbol=symbol,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            if df.empty:
                logger.warning(f"[{profile_name}] No data from broker API")
                return
            
            # Continue with strategy analysis...
            # ... rest of existing code ...
```

---

## 📱 Discord Alert Format

### **Enhanced Signal Messages**

```python
def send_vcp_signal_to_discord(signal_data: dict):
    """Send VCP signal to Discord."""
    webhook_url = "your_discord_webhook"
    
    grade = signal_data['vcp_grade']
    emoji = "⭐⭐⭐" if grade == 'A' else "⭐⭐"
    
    message = {
        "embeds": [{
            "title": f"🎯 VCP GRADE {grade} BREAKOUT {emoji}",
            "color": 0x00ff00,  # Green
            "fields": [
                {"name": "Symbol", "value": signal_data['symbol'], "inline": True},
                {"name": "Price", "value": f"₹{signal_data['price']:.2f}", "inline": True},
                {"name": "Signal Strength", "value": f"{signal_data['strength']:.1f}/10", "inline": True},
                {"name": "Entry", "value": f"₹{signal_data['entry']:.2f}", "inline": True},
                {"name": "Stop Loss", "value": f"₹{signal_data['stop_loss']:.2f} ({signal_data['risk_pct']:.1f}%)", "inline": True},
                {"name": "Take Profit", "value": f"₹{signal_data['take_profit']:.2f} ({signal_data['reward_pct']:.1f}%)", "inline": True},
                {"name": "Contractions", "value": str(signal_data['contractions']), "inline": True},
                {"name": "Prior Gain", "value": f"{signal_data['prior_gain']:.1f}%", "inline": True},
                {"name": "Risk:Reward", "value": f"1:{signal_data['rr_ratio']:.2f}", "inline": True},
                {"name": "Volume", "value": f"{signal_data['volume']:,} ({signal_data['volume_vs_avg']:.0f}% of avg)", "inline": False},
                {"name": "⚠️ Action", "value": "Manual trade execution required", "inline": False}
            ],
            "footer": {"text": f"GOD Indicator • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        }]
    }
    
    requests.post(webhook_url, json=message)
```

---

## 📋 Configuration Files

### **Broker Config**
```yaml
# config/broker.yaml
broker: "zerodha"  # or "grow"

zerodha:
  api_key: "your_api_key"
  api_secret: "your_api_secret"
  access_token: "refresh_daily"

grow:
  api_key: "your_grow_key"
  api_secret: "your_grow_secret"

# Symbols to monitor
symbols:
  - SBIN
  - INFY
  - TCS
  - RELIANCE
  - HDFCBANK

# Live streaming settings
streaming:
  enabled: true
  mode: "full"  # full tick data
  reconnect_on_error: true
```

### **Updated Strategy Profile**
```yaml
# config/profiles/vcp_nifty50.yaml
name: "VCP_NIFTY50"
enabled: true

strategy:
  class: "VCPStrategy"
  params:
    lookback_period: 60
    grade_a_final_contraction: 0.15
    grade_b_final_contraction: 0.25

data_source:
  type: "broker_api"  # NEW
  broker: "zerodha"
  symbols: ["SBIN", "INFY", "TCS"]
  interval: "day"

live:
  enabled: true
  schedule: "0 15 * * 1-5"  # 3:00 PM weekdays (after market close)
  confidence_threshold: 7.0
  alert_channels: ["vcp_signals"]
```

---

## 🚀 Deployment Workflow

### **Daily Operation**

1. **Morning (9:00 AM)**:
   ```bash
   # Refresh Zerodha access token
   python scripts/refresh_zerodha_token.py
   ```

2. **Market Hours (9:15 AM - 3:30 PM)**:
   ```bash
   # Start live scheduler
   python launch_complete_system.py
   
   # System will:
   # - Stream live data from broker
   # - Run VCP/EMA/ICT strategies
   # - Send signals to Discord
   # - You place trades manually
   ```

3. **After Market (3:30 PM+)**:
   ```bash
   # Run backtests on today's data
   python main_professional.py
   
   # Review performance
   # Adjust parameters if needed
   ```

---

## 💡 Best Practices

### **API Usage**
- ✅ Cache historical data to reduce API calls
- ✅ Use WebSocket for live data (more efficient)
- ✅ Handle API rate limits gracefully
- ✅ Refresh access tokens daily (Zerodha)

### **Signal Generation**
- ✅ Only send high-quality signals (strength > 7/10)
- ✅ Filter by volume (avoid low liquidity)
- ✅ Consider market conditions (avoid in bear markets)
- ✅ Send summary at EOD with all signals

### **Risk Management**
- ✅ Never risk more than 1-2% per trade
- ✅ Use proper stop losses
- ✅ Diversify across multiple stocks
- ✅ Track all trades in spreadsheet

---

## 📊 Next Steps

1. **Get API Access**:
   - [ ] Sign up for Zerodha Kite Connect
   - [ ] Create app and get API credentials
   - [ ] OR contact Grow for API access

2. **Install Dependencies**:
   ```bash
   pip install kiteconnect
   ```

3. **Create Broker Config**:
   - [ ] Create `config/broker.yaml`
   - [ ] Add API credentials
   - [ ] Add symbols to monitor

4. **Test Integration**:
   ```bash
   python backend/data_fetch_broker.py
   ```

5. **Update Live Scheduler**:
   - [ ] Replace yfinance with broker API
   - [ ] Test with paper trading first

6. **Go Live**:
   - [ ] Start with small position sizes
   - [ ] Monitor signals closely
   - [ ] Scale up gradually

---

## ⚠️ Important Notes

- **No Auto-Trading**: System NEVER places orders automatically
- **Manual Execution**: You receive signals → You place trades
- **API Costs**: Zerodha charges ₹2000/month for API access
- **Data Limits**: Be mindful of API rate limits
- **Token Refresh**: Zerodha tokens expire daily

---

Your system is now ready to integrate with broker APIs! 🚀📊

**Current Status:**
- ✅ 3 Strategies (EMA30, ICT, VCP)
- ✅ Broker API integration guide ready
- ✅ Live data streaming architecture defined
- ✅ Discord alerts configured
- ⏳ Waiting for broker API credentials

Once you get API access, we can complete the integration! 🎯
