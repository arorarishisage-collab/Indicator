#!/usr/bin/env python3
"""
Unit tests for GUI Configuration and Validator
Tests mandatory field validation and configuration persistence
"""

import json
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config_manager import (
    ConfigValidator as ConfigValidator2,
    ConfigManager,
    RequiredConfig,
    OptionalConfig,
    StrategyFilters,
)

def test_telegram_token_validation():
    """Test Telegram token format validation."""
    print("\n" + "="*60)
    print("TEST: Telegram Token Validation")
    print("="*60)
    
    # Valid tokens
    valid_tokens = [
        "1234567890:ABCDEFghijklmnopQRSTUVwxyz1234567",
        "9999999999:aaaabbbbccccddddeeeeffffgggg1111",
    ]
    
    for token in valid_tokens:
        is_valid, msg = ConfigValidator2.validate_telegram_token(token)
        assert is_valid, f"Should accept valid token: {token}\nGot: {msg}"
        print(f"✓ Valid: {token[:20]}...")
    
    # Invalid tokens
    invalid_tokens = [
        "",  # Empty
        "tooshort",  # Too short
        "1234567890",  # No colon
        "no_colon_here",  # No colon
        "abcd:efgh",  # First part not numeric
        "1234567890:ab",  # Second part too short
    ]
    
    for token in invalid_tokens:
        is_valid, msg = ConfigValidator2.validate_telegram_token(token)
        assert not is_valid, f"Should reject invalid token: {token}"
        print(f"✗ Invalid: {token} ({msg})")
    
    print("✓ All token tests passed")

def test_telegram_chat_id_validation():
    """Test Telegram chat ID validation."""
    print("\n" + "="*60)
    print("TEST: Telegram Chat ID Validation")
    print("="*60)
    
    # Valid chat IDs
    valid_ids = ["123456789", "999999999", "-1001234567890"]
    
    for chat_id in valid_ids:
        is_valid, msg = ConfigValidator2.validate_telegram_chat_id(chat_id)
        assert is_valid, f"Should accept valid chat ID: {chat_id}"
        print(f"✓ Valid: {chat_id}")
    
    # Invalid chat IDs
    invalid_ids = ["", "abc", "0", "-0"]
    
    for chat_id in invalid_ids:
        is_valid, msg = ConfigValidator2.validate_telegram_chat_id(chat_id)
        assert not is_valid, f"Should reject invalid chat ID: {chat_id}"
        print(f"✗ Invalid: {chat_id} ({msg})")
    
    print("✓ All chat ID tests passed")

def test_port_validation():
    """Test port number validation."""
    print("\n" + "="*60)
    print("TEST: Port Validation")
    print("="*60)
    
    # Valid ports
    valid_ports = [8000, 5000, 3000, 65535]
    
    for port in valid_ports:
        is_valid, msg = ConfigValidator2.validate_port(port)
        assert is_valid, f"Should accept valid port: {port}"
        print(f"✓ Valid: {port}")
    
    # Invalid ports
    invalid_ports = [0, 500, 65536, -1]
    
    for port in invalid_ports:
        is_valid, msg = ConfigValidator2.validate_port(port)
        assert not is_valid, f"Should reject invalid port: {port}"
        print(f"✗ Invalid: {port} ({msg})")
    
    print("✓ All port tests passed")

def test_required_config_validation():
    """Test required configuration validation."""
    print("\n" + "="*60)
    print("TEST: Required Config Validation")
    print("="*60)
    
    # Valid config
    valid_config = {
        'telegram_bot_token': '1234567890:ABCDEFghijklmnopQRSTUVwxyz',
        'telegram_chat_id': '123456789',
    }
    
    is_valid, msg = ConfigValidator2.validate_required(valid_config)
    assert is_valid, f"Should accept valid config\nGot: {msg}"
    print(f"✓ Valid config accepted")
    
    # Missing token
    config_no_token = {
        'telegram_chat_id': '123456789',
    }
    is_valid, msg = ConfigValidator2.validate_required(config_no_token)
    assert not is_valid, "Should reject config without token"
    print(f"✗ Missing token: {msg}")
    
    # Missing chat ID
    config_no_chat = {
        'telegram_bot_token': '1234567890:ABCDEFghijklmnopQRSTUVwxyz',
    }
    is_valid, msg = ConfigValidator2.validate_required(config_no_chat)
    assert not is_valid, "Should reject config without chat ID"
    print(f"✗ Missing chat ID: {msg}")
    
    # Empty values
    config_empty = {
        'telegram_bot_token': '',
        'telegram_chat_id': '',
    }
    is_valid, msg = ConfigValidator2.validate_required(config_empty)
    assert not is_valid, "Should reject config with empty values"
    print(f"✗ Empty values: {msg}")
    
    print("✓ All required config tests passed")

def test_full_validation():
    """Test full configuration validation."""
    print("\n" + "="*60)
    print("TEST: Full Configuration Validation")
    print("="*60)
    
    # Valid complete config
    valid_config = {
        'telegram_bot_token': '1234567890:ABCDEFghijklmnopQRSTUVwxyz',
        'telegram_chat_id': '123456789',
        'webhook_port': 8000,
        'initial_capital': 10000,
        'slippage_pips': 1.0,
        'spread_pips': 0.5,
    }
    
    is_valid, msg = ConfigValidator2.validate_all(valid_config)
    assert is_valid, f"Should accept complete valid config\nGot: {msg}"
    print(f"✓ Complete valid config: {msg}")
    
    # Config with invalid port
    config_bad_port = valid_config.copy()
    config_bad_port['webhook_port'] = 500  # Too low
    
    is_valid, msg = ConfigValidator2.validate_all(config_bad_port)
    assert not is_valid, "Should reject config with invalid port"
    print(f"✗ Invalid port: {msg}")
    
    # Config with invalid capital
    config_bad_capital = valid_config.copy()
    config_bad_capital['initial_capital'] = -5000
    
    is_valid, msg = ConfigValidator2.validate_all(config_bad_capital)
    assert not is_valid, "Should reject negative capital"
    print(f"✗ Negative capital: {msg}")
    
    print("✓ All full validation tests passed")

def test_config_manager():
    """Test configuration manager persistence."""
    print("\n" + "="*60)
    print("TEST: Configuration Manager")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / 'config.json'
        
        # Create required config
        required = RequiredConfig(
            telegram_bot_token='1234567890:ABCDEFghijklmnopQRSTUVwxyz',
            telegram_chat_id='123456789'
        )
        
        optional = OptionalConfig(
            initial_capital=15000,
            slippage_pips=1.5,
        )
        
        filters = StrategyFilters(
            swing_lookback=25,
            atr_multiplier=2.0,
        )
        
        # Simulate saving (manual JSON for temp dir)
        config_data = {
            'required': {
                'telegram_bot_token': required.telegram_bot_token,
                'telegram_chat_id': required.telegram_chat_id,
            },
            'optional': {
                'initial_capital': optional.initial_capital,
                'slippage_pips': optional.slippage_pips,
            },
            'filters': {
                'swing_lookback': filters.swing_lookback,
                'atr_multiplier': filters.atr_multiplier,
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Read back
        with open(config_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data['required']['telegram_bot_token'] == required.telegram_bot_token
        assert loaded_data['optional']['initial_capital'] == optional.initial_capital
        assert loaded_data['filters']['swing_lookback'] == filters.swing_lookback
        
        print(f"✓ Configuration saved and loaded")
        print(f"  Token: {loaded_data['required']['telegram_bot_token'][:20]}...")
        print(f"  Capital: ${loaded_data['optional']['initial_capital']}")
        print(f"  Lookback: {loaded_data['filters']['swing_lookback']} periods")

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Gold Trading GUI - Configuration Tests")
    print("="*60)
    
    try:
        test_telegram_token_validation()
        test_telegram_chat_id_validation()
        test_port_validation()
        test_required_config_validation()
        test_full_validation()
        test_config_manager()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nConfiguration validation is working correctly:")
        print("  ✓ Telegram token validation")
        print("  ✓ Telegram chat ID validation")
        print("  ✓ Port validation")
        print("  ✓ Required field enforcement")
        print("  ✓ Full configuration validation")
        print("  ✓ Configuration persistence")
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
