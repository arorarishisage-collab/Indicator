"""
Configuration Management Module
Handles all config validation, persistence, and retrieval
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequiredConfig:
    """Required configuration fields."""
    telegram_bot_token: str
    telegram_chat_id: str


@dataclass
class OptionalConfig:
    """Optional configuration fields."""
    oanda_api_key: Optional[str] = None
    webhook_port: int = 8000
    initial_capital: float = 10000.0
    slippage_pips: float = 1.0
    spread_pips: float = 0.5
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    timeframe: str = "1h"


@dataclass
class StrategyFilters:
    """Strategy filter parameters."""
    swing_lookback: int = 20
    atr_multiplier: float = 1.5
    min_risk_reward: float = 1.5
    min_confluence: int = 2
    ema_fast: int = 30
    ema_slow: int = 200
    include_demand: bool = True
    include_supply: bool = True
    include_ob: bool = True
    include_fvg: bool = True


class ConfigValidator:
    """Validate configuration parameters."""
    
    @staticmethod
    def validate_telegram_token(token: str) -> Tuple[bool, str]:
        """
        Validate Telegram bot token format.
        Format: numeric_id:alphanumeric_string
        """
        if not token or len(token) < 20:
            return False, "Token too short. Should be > 20 characters"
        
        if ':' not in token:
            return False, "Invalid format. Should contain ':' separator"
        
        parts = token.split(':')
        if len(parts) != 2:
            return False, "Invalid format. Should have exactly one ':'"
        
        try:
            int(parts[0])
        except ValueError:
            return False, "Invalid format. First part should be numeric"
        
        if not parts[1].isalnum() or len(parts[1]) < 10:
            return False, "Invalid format. Second part should be alphanumeric (>10 chars)"
        
        return True, "Valid Telegram token"
    
    @staticmethod
    def validate_telegram_chat_id(chat_id: str) -> Tuple[bool, str]:
        """Validate Telegram chat ID (must be numeric)."""
        if not chat_id or not chat_id.strip():
            return False, "Chat ID cannot be empty"
        
        try:
            int_id = int(chat_id)
            if int_id == 0:
                return False, "Chat ID cannot be zero"
            return True, f"Valid Telegram chat ID: {int_id}"
        except ValueError:
            return False, f"Chat ID must be numeric, got: {chat_id}"
    
    @staticmethod
    def validate_port(port: int) -> Tuple[bool, str]:
        """Validate port number."""
        if not isinstance(port, int):
            return False, "Port must be an integer"
        
        if port < 1024:
            return False, "Port must be >= 1024"
        
        if port > 65535:
            return False, "Port must be <= 65535"
        
        return True, f"Valid port: {port}"
    
    @staticmethod
    def validate_required(config: Dict) -> Tuple[bool, str]:
        """Validate all required fields are present and valid."""
        # Telegram credentials are optional for backtesting and offline use.
        # If provided, validate their format; otherwise allow missing and
        # indicate that live alerts will be disabled.
        token = config.get('telegram_bot_token', '').strip()
        chat_id = config.get('telegram_chat_id', '').strip()

        if not token and not chat_id:
            return True, "✓ Telegram not configured (live alerts disabled)"

        # If one is provided, require both and validate
        if not token or not chat_id:
            return False, "❌ Both Telegram Bot Token and Chat ID are required to enable Telegram alerts"

        is_valid, msg = ConfigValidator.validate_telegram_token(token)
        if not is_valid:
            return False, f"❌ Invalid Telegram Bot Token: {msg}"

        is_valid, msg = ConfigValidator.validate_telegram_chat_id(chat_id)
        if not is_valid:
            return False, f"❌ Invalid Telegram Chat ID: {msg}"

        return True, "✓ All required fields valid"
    
    @staticmethod
    def validate_optional(config: Dict) -> Tuple[bool, str]:
        """Validate optional fields if present."""
        if 'webhook_port' in config:
            is_valid, msg = ConfigValidator.validate_port(config['webhook_port'])
            if not is_valid:
                return False, f"❌ Invalid webhook port: {msg}"
        
        if 'initial_capital' in config:
            try:
                capital = float(config['initial_capital'])
                if capital <= 0:
                    return False, "❌ Initial capital must be > 0"
            except ValueError:
                return False, "❌ Initial capital must be numeric"
        
        if 'slippage_pips' in config:
            try:
                slippage = float(config['slippage_pips'])
                if slippage < 0.1 or slippage > 10:
                    return False, "❌ Slippage should be between 0.1 and 10 pips"
            except ValueError:
                return False, "❌ Slippage must be numeric"
        
        if 'spread_pips' in config:
            try:
                spread = float(config['spread_pips'])
                if spread < 0.1 or spread > 10:
                    return False, "❌ Spread should be between 0.1 and 10 pips"
            except ValueError:
                return False, "❌ Spread must be numeric"
        
        return True, "✓ Optional fields valid"
    
    @classmethod
    def validate_all(cls, config: Dict) -> Tuple[bool, str]:
        """Validate complete configuration."""
        # Validate required first
        is_valid, msg = cls.validate_required(config)
        if not is_valid:
            return False, msg
        
        # Validate optional
        is_valid, msg = cls.validate_optional(config)
        if not is_valid:
            return False, msg
        
        return True, "✓ Configuration is valid and ready to use"


class ConfigManager:
    """Manage application configuration."""
    
    def __init__(self):
        self.config_dir = Path.home() / '.gold_trading'
        self.config_file = self.config_dir / 'config.json'
        self.config_file.parent.mkdir(exist_ok=True)
        
        self.required: Optional[RequiredConfig] = None
        self.optional: Optional[OptionalConfig] = None
        self.filters: Optional[StrategyFilters] = None
        
        self._load()
    
    def _load(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Load required
                req_data = data.get('required', {})
                if req_data.get('telegram_bot_token') and req_data.get('telegram_chat_id'):
                    self.required = RequiredConfig(**req_data)
                
                # Load optional
                opt_data = data.get('optional', {})
                self.optional = OptionalConfig(**opt_data)
                
                # Load filters
                filt_data = data.get('filters', {})
                self.filters = StrategyFilters(**filt_data)
                
                logger.info("Configuration loaded from file")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                self._init_defaults()
        else:
            self._init_defaults()
    
    def _init_defaults(self):
        """Initialize with default values."""
        self.required = None
        self.optional = OptionalConfig()
        self.filters = StrategyFilters()
    
    def save(self, required: RequiredConfig, optional: OptionalConfig, 
             filters: StrategyFilters) -> Tuple[bool, str]:
        """
        Save configuration to file.
        
        Returns:
            (success, message)
        """
        # Validate before saving
        config_dict = {
            'required': asdict(required),
            'optional': asdict(optional),
            'filters': asdict(filters),
        }
        
        is_valid, msg = ConfigValidator.validate_required(config_dict['required'])
        if not is_valid:
            return False, msg
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            self.required = required
            self.optional = optional
            self.filters = filters
            
            logger.info(f"Configuration saved to {self.config_file}")
            return True, "✓ Configuration saved successfully"
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False, f"❌ Error saving configuration: {e}"
    
    def is_configured(self) -> bool:
        """Check if required configuration is set."""
        if not self.required:
            return False
        
        is_valid, _ = ConfigValidator.validate_required({
            'telegram_bot_token': self.required.telegram_bot_token,
            'telegram_chat_id': self.required.telegram_chat_id,
        })
        return is_valid
    
    def get_config_status(self) -> Dict:
        """Get configuration status report."""
        status = {
            'is_configured': self.is_configured(),
            'required': {
                'telegram_bot_token': '✓ Set' if (self.required and self.required.telegram_bot_token) else '❌ Missing',
                'telegram_chat_id': '✓ Set' if (self.required and self.required.telegram_chat_id) else '❌ Missing',
            },
            'optional': asdict(self.optional) if self.optional else {},
            'filters': asdict(self.filters) if self.filters else {},
        }
        return status


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
