"""
TradingView Webhook Integration
Send trading signals in TradingView standard format for Pine Script integration
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingViewWebhook:
    """
    Send signals to TradingView via webhooks
    Supports standard alert format for Pine Script integration
    """
    
    def __init__(self, webhook_url: str, api_key: Optional[str] = None):
        """
        Initialize TradingView webhook sender
        
        Args:
            webhook_url (str): Webhook URL (from TradingView alert settings)
            api_key (str): Optional API key for authentication
        """
        self.webhook_url = webhook_url
        self.api_key = api_key
        self.last_signal_time = {}
    
    def send_signal(self, symbol: str, direction: str, strategy: str,
                   entry_price: float, signal_strength: float = 5,
                   stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None,
                   timeframe: str = '1D',
                   risk_percent: Optional[float] = None,
                   exposure_percent: Optional[float] = None,
                   open_trades: Optional[int] = None,
                   extra_fields: Optional[Dict[str, str]] = None,
                   news_headlines: Optional[List[str]] = None) -> bool:
        """
        Send trading signal to TradingView webhook
        
        Args:
            symbol (str): Trading symbol (XAUUSD, BTCUSD, etc.)
            direction (str): 'BUY' or 'SELL'
            strategy (str): Strategy name
            entry_price (float): Suggested entry price
            signal_strength (float): Signal strength 0-10
            stop_loss (float): Stop loss price (optional)
            take_profit (float): Take profit price (optional)
            timeframe (str): Chart timeframe (1D, 4H, 1H, 15M, etc.)
            risk_percent (float): Risk per trade as % (optional)
            exposure_percent (float): Total portfolio exposure % (optional)
            open_trades (int): Number of open trades (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prevent duplicate signals (debounce)
            signal_key = f"{symbol}_{direction}_{strategy}"
            now = datetime.now()
            
            if signal_key in self.last_signal_time:
                time_since_last = (now - self.last_signal_time[signal_key]).total_seconds()
                if time_since_last < 300:  # 5 minute debounce
                    logger.debug(f"Signal skipped (debounce): {signal_key}")
                    return False
            
            # Format signal in TradingView standard format
            payload = self._build_payload(
                symbol=symbol,
                direction=direction,
                strategy=strategy,
                entry_price=entry_price,
                signal_strength=signal_strength,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=timeframe,
                risk_percent=risk_percent,
                exposure_percent=exposure_percent,
                open_trades=open_trades,
                extra_fields=extra_fields,
                news_headlines=news_headlines
            )

            headers = {
                'Content-Type': 'application/json',
            }

            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"✓ Signal sent: {symbol} {direction} @ {entry_price} ({strategy})")
                self.last_signal_time[signal_key] = now
                return True
            else:
                logger.warning(f"⚠️ Webhook failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending webhook: {e}")
            return False

    def _is_discord(self) -> bool:
        return 'discord.com/api/webhooks' in (self.webhook_url or '')

    def _build_payload(self, **kwargs) -> dict:
        if self._is_discord():
            return self._format_discord_alert(**kwargs)
        return self._format_tradingview_alert(**kwargs)
    
    def _format_tradingview_alert(self, symbol: str, direction: str, strategy: str,
                                 entry_price: float, signal_strength: float,
                                 stop_loss: Optional[float],
                                 take_profit: Optional[float],
                                 timeframe: str,
                                 risk_percent: Optional[float] = None,
                                 exposure_percent: Optional[float] = None,
                                 open_trades: Optional[int] = None,
                                 extra_fields: Optional[Dict[str, str]] = None,
                                 news_headlines: Optional[List[str]] = None) -> dict:
        """
        Format signal in TradingView standard alert format
        
        Returns:
            dict: Formatted payload for webhook
        """
        confidence = 'HIGH' if signal_strength >= 7 else 'MEDIUM' if signal_strength >= 5 else 'LOW'
        stars = '⭐' * int(signal_strength / 2) if signal_strength > 0 else ''
        
        # Enhanced alert format with risk info
        alert_text = f"""
🔔 SIGNAL: {direction} {symbol}
Strategy: {strategy}
Timeframe: {timeframe}
Entry: {entry_price}
Confidence: {signal_strength:.1f}/10 {stars} ({confidence})
"""
        
        if stop_loss:
            alert_text += f"Stop Loss: {stop_loss}\n"
        if take_profit:
            alert_text += f"Take Profit: {take_profit}\n"
        
        # Add risk metrics
        if risk_percent is not None:
            alert_text += f"Risk per Trade: {risk_percent:.1f}%\n"
        if exposure_percent is not None:
            alert_text += f"Total Exposure: {exposure_percent:.1f}%\n"
        if open_trades is not None:
            alert_text += f"Open Trades: {open_trades}\n"

        if extra_fields:
            for label, value in extra_fields.items():
                alert_text += f"{label}: {value}\n"

        if news_headlines:
            alert_text += "News Highlights:\n"
            for headline in news_headlines[:3]:
                alert_text += f" • {headline}\n"
        
        # Payload format for TradingView/Pine Script
        payload = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': direction.upper(),  # BUY or SELL
            'strategy': strategy,
            'timeframe': timeframe,
            'price': entry_price,
            'signal_strength': signal_strength,
            'confidence': confidence,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_percent': risk_percent,
            'exposure_percent': exposure_percent,
            'open_trades': open_trades,
            'alert_message': alert_text.strip(),
            'message': alert_text.strip(),  # Alternative field name
        }
        
        return payload

    def _format_discord_alert(self, symbol: str, direction: str, strategy: str,
                               entry_price: float, signal_strength: float,
                               stop_loss: Optional[float],
                               take_profit: Optional[float],
                               timeframe: str,
                               risk_percent: Optional[float] = None,
                               exposure_percent: Optional[float] = None,
                               open_trades: Optional[int] = None,
                               extra_fields: Optional[Dict[str, str]] = None,
                               news_headlines: Optional[List[str]] = None) -> dict:
        """Rich embed formatting for Discord webhooks."""
        confidence = 'HIGH' if signal_strength >= 7 else 'MEDIUM' if signal_strength >= 5 else 'LOW'
        stars = '⭐' * int(signal_strength / 2) if signal_strength > 0 else ''
        color = 0x2ecc71 if direction.upper() == 'BUY' else 0xe74c3c
        
        # Build fields with enhanced info
        fields = [
            {'name': '💰 Entry Price', 'value': f"**{entry_price:.2f}**", 'inline': True},
            {'name': '🎯 Confidence', 'value': f"**{signal_strength:.1f}/10** {stars}\n({confidence})", 'inline': True},
            {'name': '⏰ Timeframe', 'value': timeframe, 'inline': True},
        ]
        
        if stop_loss:
            fields.append({'name': '🛑 Stop Loss', 'value': f"{stop_loss:.2f}", 'inline': True})
        if take_profit:
            fields.append({'name': '🎯 Take Profit', 'value': f"{take_profit:.2f}", 'inline': True})
        
        # Add risk metrics prominently
        if risk_percent is not None:
            fields.append({'name': '⚠️ Risk/Trade', 'value': f"**{risk_percent:.1f}%**", 'inline': True})
        if exposure_percent is not None:
            exposure_color = '🟢' if exposure_percent < 5 else '🟡' if exposure_percent < 10 else '🔴'
            fields.append({'name': f'{exposure_color} Total Exposure', 'value': f"**{exposure_percent:.1f}%**", 'inline': True})
        if open_trades is not None:
            fields.append({'name': '📊 Open Trades', 'value': f"{open_trades}", 'inline': True})
        
        fields.append({'name': '🤖 Strategy', 'value': strategy, 'inline': True})

        if extra_fields:
            for label, value in list(extra_fields.items())[:5]:
                fields.append({'name': label, 'value': value, 'inline': True})

        if news_headlines:
            summary = '\n'.join(f"• {headline}" for headline in news_headlines[:3])
            fields.append({'name': '📰 News Highlights', 'value': summary or 'No recent coverage', 'inline': False})

        description = f"**{strategy}** detected a {confidence} confidence setup."
        if risk_percent and exposure_percent:
            description += f"\n\n*Risk: {risk_percent:.1f}% | Exposure: {exposure_percent:.1f}%*"

        embed = {
            'title': f"{'📈' if direction.upper() == 'BUY' else '📉'} {direction.upper()} {symbol}",
            'description': description,
            'color': color,
            'fields': fields,
            'timestamp': datetime.utcnow().isoformat(),
            'footer': {'text': f'Automated Trading Signal • {datetime.now().strftime("%H:%M:%S")}'}
        }

        content = f"🔔 **{direction.upper()}** signal for **{symbol}** ({timeframe}) {stars}"
        return {
            'username': 'Gold Trading Bot',
            'avatar_url': 'https://cdn-icons-png.flaticon.com/512/2830/2830284.png',  # Gold icon
            'content': content,
            'embeds': [embed]
        }
    
    def send_bulk_signals(self, signals: list) -> dict:
        """
        Send multiple signals at once
        
        Args:
            signals (list): List of signal dicts with keys:
                          {symbol, direction, strategy, entry_price, signal_strength, ...}
                          
        Returns:
            dict: {success: count, failed: count}
        """
        results = {'success': 0, 'failed': 0}
        
        for signal in signals:
            success = self.send_signal(
                symbol=signal['symbol'],
                direction=signal['direction'],
                strategy=signal['strategy'],
                entry_price=signal['entry_price'],
                signal_strength=signal.get('signal_strength', 5),
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit'),
                timeframe=signal.get('timeframe', '1D')
            )
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results


class WebhookConfig:
    """
    Manage webhook configurations
    Allows users to set multiple webhook endpoints
    """
    
    def __init__(self, config_file: str = 'config/webhooks.json'):
        """
        Initialize webhook config manager
        
        Args:
            config_file (str): Path to webhook configuration file
        """
        self.config_file = config_file
        self.webhooks = {}
        self.load_config()
    
    def load_config(self):
        """Load webhook config from file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    self.webhooks = json.load(f)
                logger.info(f"✓ Loaded {len(self.webhooks)} webhooks from config")
            else:
                logger.info("No webhook config found. Create with add_webhook()")
                self.webhooks = {}
        except Exception as e:
            logger.error(f"Error loading webhook config: {e}")
            self.webhooks = {}
    
    def add_webhook(self, name: str, url: str, api_key: Optional[str] = None, 
                   enabled: bool = True) -> bool:
        """
        Add webhook configuration
        
        Args:
            name (str): Webhook name (e.g., 'main', 'backup')
            url (str): Webhook URL
            api_key (str): Optional API key
            enabled (bool): Enable/disable webhook
            
        Returns:
            bool: True if successful
        """
        try:
            self.webhooks[name] = {
                'url': url,
                'api_key': api_key,
                'enabled': enabled,
                'created_at': datetime.now().isoformat(),
            }
            self.save_config()
            logger.info(f"✓ Webhook '{name}' added")
            return True
        except Exception as e:
            logger.error(f"Error adding webhook: {e}")
            return False
    
    def remove_webhook(self, name: str) -> bool:
        """Remove webhook configuration"""
        try:
            if name in self.webhooks:
                del self.webhooks[name]
                self.save_config()
                logger.info(f"✓ Webhook '{name}' removed")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing webhook: {e}")
            return False
    
    def get_webhook(self, name: str = 'main') -> Optional[TradingViewWebhook]:
        """
        Get webhook instance by name
        
        Args:
            name (str): Webhook name
            
        Returns:
            TradingViewWebhook: Webhook instance or None
        """
        if name not in self.webhooks or not self.webhooks[name]['enabled']:
            return None
        
        config = self.webhooks[name]
        return TradingViewWebhook(config['url'], config.get('api_key'))
    
    def save_config(self):
        """Save webhook config to file"""
        try:
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.webhooks, f, indent=2)
            logger.debug(f"✓ Webhook config saved")
        except Exception as e:
            logger.error(f"Error saving webhook config: {e}")
    
    def list_webhooks(self) -> dict:
        """List all configured webhooks"""
        return {name: {
            'enabled': config['enabled'],
            'url': config['url'][:50] + '...' if len(config['url']) > 50 else config['url']
        } for name, config in self.webhooks.items()}


if __name__ == '__main__':
    print("\n🚀 TradingView Webhook Integration Test\n")
    
    # Test webhook config
    config = WebhookConfig()
    
    # Add example webhook (replace with your actual webhook URL)
    config.add_webhook(
        name='main',
        url='https://hooks.slack.com/services/YOUR/WEBHOOK/URL',  # Example Slack webhook
        api_key=None,
        enabled=True
    )
    
    print("Configured webhooks:")
    print(json.dumps(config.list_webhooks(), indent=2))
    
    # Test sending signal
    webhook = config.get_webhook('main')
    if webhook:
        success = webhook.send_signal(
            symbol='XAUUSD',
            direction='BUY',
            strategy='ICTStrategy',
            entry_price=2000,
            signal_strength=7.5,
            stop_loss=1980,
            take_profit=2020,
            timeframe='4H'
        )
        print(f"\nSignal send result: {'✓ Success' if success else '✗ Failed'}")
