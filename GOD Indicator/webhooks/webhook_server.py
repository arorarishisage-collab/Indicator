"""
Webhook Server for Pine Script Integration
FastAPI app to receive signals from TradingView and process them.
"""

try:
    from fastapi import FastAPI, HTTPException, Request
except ImportError as e:
    raise ImportError("fastapi not installed. Install with: pip install fastapi uvicorn")

from pydantic import BaseModel
from typing import Optional
import logging
import os
from datetime import datetime
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gold Trading Signal Webhook", version="1.0.0")


class PineScriptSignal(BaseModel):
    """Schema for signals from Pine Script."""
    action: str  # 'buy' or 'sell'
    symbol: str = 'XAUUSD'
    entry_price: float
    stop_loss: float
    take_profit: float
    timeframe: str = '1H'
    reason: str = 'Signal from Pine Script'


class WebhookProcessor:
    """Process incoming webhook signals."""
    
    def __init__(self, webhook_key: Optional[str] = None):
        """
        Initialize webhook processor.
        
        Args:
            webhook_key: Secret key for webhook verification (optional)
        """
        self.webhook_key = webhook_key or os.getenv('WEBHOOK_KEY', 'default-key')
        self.signal_log = Path('./reports/webhook_signals.json')
        self.signal_log.parent.mkdir(parents=True, exist_ok=True)
    
    def validate_webhook(self, request: Request) -> bool:
        """
        Validate incoming webhook request.
        
        Args:
            request: FastAPI request object
        
        Returns:
            True if valid, False otherwise
        """
        # In production, verify with HMAC signature or API key
        auth_header = request.headers.get('Authorization', '')
        
        # Placeholder validation
        logger.info(f"Webhook validation check: {bool(auth_header)}")
        return True
    
    def process_signal(self, signal: PineScriptSignal) -> dict:
        """
        Process incoming signal.
        
        Args:
            signal: PineScriptSignal object
        
        Returns:
            Processing result dictionary
        """
        signal_dict = {
            'timestamp': datetime.now().isoformat(),
            'action': signal.action.upper(),
            'symbol': signal.symbol,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'timeframe': signal.timeframe,
            'reason': signal.reason
        }
        
        # Calculate risk/reward
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.entry_price)
        rr = reward / risk if risk > 0 else 0
        
        signal_dict['risk'] = risk
        signal_dict['reward'] = reward
        signal_dict['risk_reward_ratio'] = rr
        
        # Validation checks
        checks = []
        
        # Check risk/reward >= 1.5
        if rr >= 1.5:
            checks.append(('risk_reward', True))
        else:
            checks.append(('risk_reward', False))
            logger.warning(f"R/R ratio {rr:.2f} below threshold 1.5")
        
        # Check for valid entry/SL/TP
        if signal.action.upper() == 'BUY':
            if signal.entry_price > signal.stop_loss and signal.take_profit > signal.entry_price:
                checks.append(('logic', True))
            else:
                checks.append(('logic', False))
                logger.warning("Invalid BUY: entry should be between SL and TP")
        
        else:  # SELL
            if signal.entry_price < signal.stop_loss and signal.take_profit < signal.entry_price:
                checks.append(('logic', True))
            else:
                checks.append(('logic', False))
                logger.warning("Invalid SELL: entry should be between SL and TP")
        
        signal_dict['validation'] = {check[0]: check[1] for check in checks}
        signal_dict['valid'] = all(check[1] for check in checks)
        
        # Log signal
        self._log_signal(signal_dict)
        
        logger.info(f"Signal processed: {signal.action} {signal.symbol} @ {signal.entry_price}")
        
        return signal_dict
    
    def _log_signal(self, signal: dict) -> None:
        """Log signal to file."""
        signals = []
        
        if self.signal_log.exists():
            with open(self.signal_log, 'r') as f:
                signals = json.load(f)
        
        signals.append(signal)
        
        with open(self.signal_log, 'w') as f:
            json.dump(signals, f, indent=2)
    
    async def send_to_telegram(self, signal: dict) -> bool:
        """
        Send signal to Telegram (placeholder).
        
        Args:
            signal: Processed signal dictionary
        
        Returns:
            True if sent successfully
        """
        # Import here to avoid dependency issues if python-telegram-bot not installed
        try:
            from telegram_bot import send_signal_sync
            
            telegram_signal = {
                'entry_price': signal['entry_price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'risk_reward': signal['risk_reward_ratio'],
                'timeframe': signal['timeframe'],
                'reason': signal['reason']
            }
            
            success = send_signal_sync(telegram_signal, signal['action'])
            
            if success:
                logger.info("✓ Signal sent to Telegram")
            else:
                logger.warning("✗ Failed to send to Telegram")
            
            return success
        
        except ImportError:
            logger.warning("Telegram bot not available. Install python-telegram-bot to enable.")
            return False
        except Exception as e:
            logger.error(f"Error sending to Telegram: {e}")
            return False


# Initialize processor
webhook_processor = WebhookProcessor()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Gold Trading Signal Webhook",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/webhook")
async def receive_signal(signal: PineScriptSignal, request: Request):
    """
    Receive signal from Pine Script.
    
    Args:
        signal: PineScriptSignal payload
        request: FastAPI request object
    
    Returns:
        Processing result
    """
    try:
        # Validate webhook
        if not webhook_processor.validate_webhook(request):
            logger.warning("Webhook validation failed")
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Process signal
        processed = webhook_processor.process_signal(signal)
        
        # Send to Telegram if valid
        if processed.get('valid', False):
            await webhook_processor.send_to_telegram(processed)
        
        return {
            "status": "received",
            "signal": processed,
            "message": "Signal processed successfully" if processed.get('valid') else "Signal received but validation failed"
        }
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/signals/recent")
async def get_recent_signals(limit: int = 10):
    """Get recent signals from log."""
    try:
        processor = WebhookProcessor()
        
        if not processor.signal_log.exists():
            return {"signals": [], "count": 0}
        
        with open(processor.signal_log, 'r') as f:
            signals = json.load(f)
        
        return {
            "signals": signals[-limit:],
            "count": len(signals[-limit:]),
            "total": len(signals)
        }
    
    except Exception as e:
        logger.error(f"Error retrieving signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test")
async def test_signal():
    """Test endpoint with sample signal."""
    test_signal = PineScriptSignal(
        action='buy',
        symbol='XAUUSD',
        entry_price=2050.00,
        stop_loss=2040.00,
        take_profit=2070.00,
        timeframe='1H',
        reason='Test signal from webhook'
    )
    
    processed = webhook_processor.process_signal(test_signal)
    
    return {
        "status": "test_signal_processed",
        "signal": processed
    }


if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        raise ImportError("uvicorn not installed. Install with: pip install uvicorn")
    
    # Run: uvicorn webhook_server:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('PORT', 8000)),
        log_level="info"
    )
