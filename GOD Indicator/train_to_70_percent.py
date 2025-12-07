#!/usr/bin/env python3
"""
🎯 TRAIN RL MODELS TO 70%+ WIN RATE
Comprehensive training script with proper historical data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from backend.advanced_rl_trading_system import TradingEnvironment, PPOAgent
from backend.data_fetch_yfinance import YFinanceDataFetcher
from backend.banknifty_data_loader import BankNiftyDataLoader
from backend.ema_strategy import EMA30Strategy
from backend.ict_strategy import ICTStrategy
from backend.vcp_strategy import VCPStrategy


# Training configurations for 70%+ win rate
TRAINING_CONFIGS = {
    'EMA30Strategy': {
        'symbols': ['GC=F', 'SI=F', 'CL=F', 'BANKNIFTY', 'AAPL', 'MSFT'],
        'episodes': 2000,  # Increased from 500
        'max_steps': 500,
        'reward_scaling': {
            'win_bonus': 2.0,      # Increased reward for wins
            'loss_penalty': -1.5,   # Moderate penalty for losses
            'hold_penalty': -0.01   # Small penalty for holding
        }
    },
    'ICTStrategy': {
        'symbols': ['GC=F', 'SI=F', 'EURUSD=X', 'GBPUSD=X', 'BANKNIFTY'],
        'episodes': 2500,  # More episodes for complex strategy
        'max_steps': 500,
        'reward_scaling': {
            'win_bonus': 2.5,
            'loss_penalty': -1.2,
            'hold_penalty': -0.01
        }
    },
    'VCPStrategy': {
        'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'BANKNIFTY', 'RELIANCE.NS', 'TCS.NS'],
        'episodes': 2000,
        'max_steps': 500,
        'reward_scaling': {
            'win_bonus': 2.0,
            'loss_penalty': -1.5,
            'hold_penalty': -0.01
        }
    }
}


def fetch_historical_data(symbol: str, years: int = 5) -> pd.DataFrame:
    """Fetch comprehensive historical data."""
    logger.info(f"📊 Fetching {years} years of data for {symbol}...")
    
    # Special handling for Bank Nifty
    if 'BANKNIFTY' in symbol.upper() or 'NSEBANK' in symbol.upper():
        logger.info("Using Bank Nifty GitHub data source...")
        try:
            loader = BankNiftyDataLoader(interval='1h', use_cache=True)
            df = loader.load(fallback_to_yahoo=True)
            
            if df is not None and not df.empty:
                logger.info(f"✓ Loaded {len(df)} Bank Nifty candles (GitHub source)")
                return df
        except Exception as e:
            logger.warning(f"Bank Nifty GitHub load failed: {e}, trying Yahoo...")
    
    # Standard Yahoo Finance fetch
    fetcher = YFinanceDataFetcher(
        symbol=symbol,
        interval='1h',
        period='max',
        use_cache=True
    )
    
    df = fetcher.get_data()
    
    if df is None or df.empty:
        logger.warning(f"⚠️ No data for {symbol}, trying alternative...")
        # Try daily data
        fetcher = YFinanceDataFetcher(
            symbol=symbol,
            interval='1d',
            period='5y',
            use_cache=True
        )
        df = fetcher.get_data()
    
    if df is not None and not df.empty:
        logger.info(f"✓ Loaded {len(df)} candles for {symbol}")
        return df
    
    logger.error(f"❌ Failed to load data for {symbol}")
    return None


def train_strategy_model(strategy_name: str, config: dict) -> dict:
    """Train RL model for specific strategy."""
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🎯 TRAINING {strategy_name}")
    logger.info(f"{'='*80}")
    
    # Get strategy class
    strategy_map = {
        'EMA30Strategy': EMA30Strategy,
        'ICTStrategy': ICTStrategy,
        'VCPStrategy': VCPStrategy
    }
    strategy_class = strategy_map[strategy_name]
    
    results = {}
    
    for symbol in config['symbols']:
        logger.info(f"\n📈 Training on {symbol}...")
        
        # Fetch data
        df = fetch_historical_data(symbol, years=5)
        if df is None or df.empty:
            logger.warning(f"⚠️ Skipping {symbol} - no data")
            continue
        
        # Split data: 80% train, 20% validation
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx].copy()
        val_df = df.iloc[split_idx:].copy()
        
        logger.info(f"Training samples: {len(train_df)}, Validation: {len(val_df)}")
        
        # Initialize strategy
        strategy = strategy_class(symbol=symbol)
        
        # Create environment with enhanced rewards
        env = TradingEnvironment(
            data=train_df,
            strategy=strategy,
            initial_capital=10000,
            reward_scaling=config['reward_scaling']
        )
        
        # Initialize agent
        agent = PPOAgent(
            state_size=24,
            action_size=4,
            learning_rate=0.0003,  # Lower LR for stable convergence
            gamma=0.99,
            clip_epsilon=0.2
        )
        
        # Train
        logger.info(f"🚀 Training {config['episodes']} episodes...")
        
        best_reward = float('-inf')
        best_win_rate = 0
        no_improvement = 0
        
        for episode in range(config['episodes']):
            state = env.reset()
            episode_reward = 0
            done = False
            step = 0
            
            while not done and step < config['max_steps']:
                action, log_prob, value = agent.select_action(state)
                next_state, reward, done, info = env.step(action)
                
                agent.store_transition(state, action, reward, log_prob, value, done)
                
                state = next_state
                episode_reward += reward
                step += 1
            
            # Update agent
            agent.update()
            
            # Calculate win rate from environment
            trades = getattr(env, 'trades', [])
            wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
            win_rate = (wins / len(trades) * 100) if trades else 0
            
            # Log progress
            if episode % 100 == 0:
                logger.info(
                    f"Episode {episode}/{config['episodes']} | "
                    f"Reward: {episode_reward:.2f} | "
                    f"Win Rate: {win_rate:.1f}% | "
                    f"Trades: {len(trades)}"
                )
            
            # Track best model
            if episode_reward > best_reward:
                best_reward = episode_reward
                best_win_rate = win_rate
                no_improvement = 0
            else:
                no_improvement += 1
            
            # Early stopping if no improvement
            if no_improvement > 300:
                logger.info(f"⚠️ Early stopping - no improvement for 300 episodes")
                break
        
        # Validate on validation set
        logger.info("🔍 Validating model...")
        val_env = TradingEnvironment(
            data=val_df,
            strategy=strategy,
            initial_capital=10000
        )
        
        state = val_env.reset()
        done = False
        val_step = 0
        
        while not done and val_step < config['max_steps']:
            action, _, _ = agent.select_action(state)
            state, _, done, _ = val_env.step(action)
            val_step += 1
        
        val_trades = getattr(val_env, 'trades', [])
        val_wins = sum(1 for t in val_trades if t.get('pnl', 0) > 0)
        val_win_rate = (val_wins / len(val_trades) * 100) if val_trades else 0
        
        logger.info(
            f"✅ Validation Results: "
            f"Win Rate: {val_win_rate:.1f}% | "
            f"Trades: {len(val_trades)} | "
            f"Wins: {val_wins}"
        )
        
        # Save model if performance is acceptable
        if val_win_rate >= 60:  # Minimum threshold
            slug = strategy_name.lower().replace('strategy', '')
            symbol_safe = symbol.replace('=', '_').replace('.', '_').replace('^', '_').lower()
            model_path = Path('models') / 'rl' / f'{slug}_{symbol_safe}.pth'
            model_path.parent.mkdir(parents=True, exist_ok=True)
            
            agent.save(str(model_path))
            logger.info(f"💾 Saved model: {model_path}")
            
            results[symbol] = {
                'train_reward': best_reward,
                'train_win_rate': best_win_rate,
                'val_win_rate': val_win_rate,
                'val_trades': len(val_trades),
                'model_path': str(model_path)
            }
        else:
            logger.warning(f"⚠️ Model performance below threshold ({val_win_rate:.1f}% < 60%)")
            results[symbol] = {
                'status': 'failed',
                'val_win_rate': val_win_rate,
                'reason': 'Below 60% win rate threshold'
            }
    
    return results


def main():
    """Run comprehensive training for all strategies."""
    
    print("\n" + "="*80)
    print("🎯 RL TRAINING TO 70%+ WIN RATE")
    print("="*80)
    print("Training 3 strategies across multiple symbols")
    print("Target: 70%+ win rate on validation data")
    print("This will take 30-60 minutes...")
    print("="*80 + "\n")
    
    all_results = {}
    
    for strategy_name, config in TRAINING_CONFIGS.items():
        results = train_strategy_model(strategy_name, config)
        all_results[strategy_name] = results
    
    # Summary
    print("\n" + "="*80)
    print("📊 TRAINING SUMMARY")
    print("="*80)
    
    for strategy_name, results in all_results.items():
        print(f"\n{strategy_name}:")
        
        successful = 0
        total = 0
        avg_win_rate = 0
        
        for symbol, result in results.items():
            total += 1
            if result.get('status') != 'failed':
                successful += 1
                val_win_rate = result['val_win_rate']
                avg_win_rate += val_win_rate
                
                status = "✅" if val_win_rate >= 70 else "🟡" if val_win_rate >= 60 else "❌"
                print(f"  {status} {symbol}: {val_win_rate:.1f}% win rate ({result['val_trades']} trades)")
            else:
                print(f"  ❌ {symbol}: Failed - {result.get('reason', 'Unknown')}")
        
        if successful > 0:
            avg_win_rate /= successful
            print(f"\n  Average Win Rate: {avg_win_rate:.1f}%")
            print(f"  Success Rate: {successful}/{total} symbols")
    
    print("\n" + "="*80)
    print("✅ Training complete!")
    print("Models saved to: models/rl/")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
