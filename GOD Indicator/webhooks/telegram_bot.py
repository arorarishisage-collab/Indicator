"""
Telegram Bot Module for Trading Signal Alerts
Sends formatted trading signals via Telegram.
"""

import os
from typing import Dict, Optional
import logging
import asyncio

try:
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.error import TelegramError
except ImportError as e:
    raise ImportError("python-telegram-bot not installed. Install with: pip install python-telegram-bot")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramTradingBot:
    """Telegram bot for sending trading alerts."""
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram bot.
        
        Args:
            token: Telegram bot token (from BotFather)
            chat_id: Target chat ID (from user)
        """
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.token or not self.chat_id:
            logger.warning("Telegram bot not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.")
            self.bot = None
        else:
            self.bot = Bot(token=self.token)
    
    async def send_buy_signal(self, signal: Dict) -> bool:
        """
        Send buy signal alert.
        
        Args:
            signal: Dictionary with signal details
        
        Returns:
            True if sent successfully
        """
        if not self.bot:
            logger.warning("Bot not initialized")
            return False
        
        message = f"""
🟢 BUY SIGNAL - XAUUSD

📍 Entry:        ${signal.get('entry_price', 'N/A'):.2f}
🛑 Stop Loss:     ${signal.get('stop_loss', 'N/A'):.2f}
🎯 Take Profit:   ${signal.get('take_profit', 'N/A'):.2f}
📊 Risk/Reward:   {signal.get('risk_reward', 'N/A'):.2f}
⏱️  Timeframe:     {signal.get('timeframe', '1H')}

💡 Reason:
{signal.get('reason', 'Multiple confluence factors')}

⚠️  DISCLAIMER: Not financial advice. Trade at your own risk.
"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info("✓ Buy signal sent to Telegram")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send buy signal: {e}")
            return False
    
    async def send_sell_signal(self, signal: Dict) -> bool:
        """
        Send sell signal alert.
        
        Args:
            signal: Dictionary with signal details
        
        Returns:
            True if sent successfully
        """
        if not self.bot:
            logger.warning("Bot not initialized")
            return False
        
        message = f"""
🔴 SELL SIGNAL - XAUUSD

📍 Entry:        ${signal.get('entry_price', 'N/A'):.2f}
🛑 Stop Loss:     ${signal.get('stop_loss', 'N/A'):.2f}
🎯 Take Profit:   ${signal.get('take_profit', 'N/A'):.2f}
📊 Risk/Reward:   {signal.get('risk_reward', 'N/A'):.2f}
⏱️  Timeframe:     {signal.get('timeframe', '1H')}

💡 Reason:
{signal.get('reason', 'Multiple confluence factors')}

⚠️  DISCLAIMER: Not financial advice. Trade at your own risk.
"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info("✓ Sell signal sent to Telegram")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send sell signal: {e}")
            return False
    
    async def send_trade_result(self, trade: Dict) -> bool:
        """
        Send trade result notification.
        
        Args:
            trade: Dictionary with trade details
        
        Returns:
            True if sent successfully
        """
        if not self.bot:
            logger.warning("Bot not initialized")
            return False
        
        emoji = "✅" if trade['pnl'] > 0 else "❌"
        
        message = f"""
{emoji} TRADE CLOSED

Direction:       {trade.get('direction', 'N/A')}
Entry:           ${trade.get('entry', 'N/A'):.2f}
Exit:            ${trade.get('exit', 'N/A'):.2f}
Exit Type:       {trade.get('exit_type', 'N/A')}
P&L:             ${trade.get('pnl', 0):.2f}
Return %:        {(trade.get('pnl', 0) / (trade.get('entry', 1) * trade.get('contracts', 1))) * 100:.2f}%
"""
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info("✓ Trade result sent to Telegram")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send trade result: {e}")
            return False
    
    async def send_status_update(self, status: str) -> bool:
        """
        Send general status update.
        
        Args:
            status: Status message
        
        Returns:
            True if sent successfully
        """
        if not self.bot:
            logger.warning("Bot not initialized")
            return False
        
        message = f"📊 System Status Update:\n\n{status}"
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info("✓ Status update sent to Telegram")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send status: {e}")
            return False


# Synchronous wrapper functions for easy integration
def send_signal_sync(signal: Dict, signal_type: str = 'BUY') -> bool:
    """
    Send signal synchronously.
    
    Args:
        signal: Signal dictionary
        signal_type: 'BUY' or 'SELL'
    
    Returns:
        True if sent successfully
    """
    bot = TelegramTradingBot()
    
    if signal_type.upper() == 'BUY':
        return asyncio.run(bot.send_buy_signal(signal))
    else:
        return asyncio.run(bot.send_sell_signal(signal))


def send_trade_result_sync(trade: Dict) -> bool:
    """Send trade result synchronously."""
    bot = TelegramTradingBot()
    return asyncio.run(bot.send_trade_result(trade))


if __name__ == "__main__":
    # Test bot initialization
    bot = TelegramTradingBot()
    
    # Example signal
    test_signal = {
        'entry_price': 2050.00,
        'stop_loss': 2040.00,
        'take_profit': 2070.00,
        'risk_reward': 2.0,
        'timeframe': '1H',
        'reason': 'Price touched demand zone + bullish OB confluence'
    }
    
    # Send (uncomment to test with real credentials)
    # asyncio.run(bot.send_buy_signal(test_signal))
    logger.info("Telegram bot module loaded. Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable alerts.")
