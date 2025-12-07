#!/usr/bin/env python3
"""
🧠 INTELLIGENT RL BRAIN TRAINING SYSTEM
Train once with massive historical data, self-improve through live trading
Target: 90%+ on historical → 70%+ in real-world
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import json
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from backend.advanced_rl_trading_system import TradingEnvironment, PPOAgent
from backend.data_fetch_yfinance import YFinanceDataFetcher
from backend.banknifty_data_loader import BankNiftyDataLoader
from backend.ema_strategy import EMA30Strategy
from backend.ict_strategy import ICTStrategy
from backend.vcp_strategy import VCPStrategy


class IntelligentRLBrain:
    """
    Self-improving RL brain that trains once and adapts continuously.
    """
    
    def __init__(self, brain_dir: str = 'models/rl_brain'):
        self.brain_dir = Path(brain_dir)
        self.brain_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.brain_dir / 'brain_metadata.json'
        self.performance_log = self.brain_dir / 'performance_history.csv'
        
        # Training targets
        self.HISTORICAL_TARGET = 90.0  # 90% on historical data
        self.REALWORLD_TARGET = 70.0   # 70% in live trading
        self.MIN_ACCEPTABLE = 85.0     # Minimum to save model
        
    def save_brain_state(self, strategy: str, symbol: str, metadata: dict):
        """Save brain metadata for continuous learning."""
        brain_key = f"{strategy}_{symbol}"
        
        # Load existing metadata
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                all_metadata = json.load(f)
        else:
            all_metadata = {}
        
        # Update with new training info
        all_metadata[brain_key] = {
            'last_trained': datetime.now().isoformat(),
            'training_episodes': metadata.get('episodes', 0),
            'historical_win_rate': metadata.get('train_win_rate', 0),
            'validation_win_rate': metadata.get('val_win_rate', 0),
            'total_samples': metadata.get('total_samples', 0),
            'best_reward': metadata.get('best_reward', 0),
            'model_version': metadata.get('version', 1),
            'data_sources': metadata.get('data_sources', []),
            'needs_retraining': False
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(all_metadata, f, indent=2)
        
        logger.info(f"💾 Brain state saved: {brain_key}")
    
    def log_performance(self, strategy: str, symbol: str, win_rate: float, 
                       trades: int, source: str = 'live'):
        """Log performance for continuous monitoring."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy,
            'symbol': symbol,
            'win_rate': win_rate,
            'trades': trades,
            'source': source
        }
        
        df = pd.DataFrame([log_entry])
        
        if self.performance_log.exists():
            df.to_csv(self.performance_log, mode='a', header=False, index=False)
        else:
            df.to_csv(self.performance_log, index=False)
    
    def should_retrain(self, strategy: str, symbol: str) -> bool:
        """Check if model needs retraining based on recent performance."""
        if not self.performance_log.exists():
            return False
        
        df = pd.read_csv(self.performance_log)
        recent = df[
            (df['strategy'] == strategy) & 
            (df['symbol'] == symbol) &
            (df['source'] == 'live')
        ].tail(50)  # Last 50 live trades
        
        if len(recent) < 20:
            return False  # Not enough data
        
        recent_win_rate = recent['win_rate'].mean()
        
        if recent_win_rate < self.REALWORLD_TARGET:
            logger.warning(
                f"⚠️ {strategy} on {symbol}: {recent_win_rate:.1f}% < {self.REALWORLD_TARGET}% "
                f"- Retraining recommended"
            )
            return True
        
        return False


def fetch_all_historical_data(symbol: str) -> List[pd.DataFrame]:
    """Fetch maximum historical data from all sources."""
    datasets = []
    
    # Special handling for Bank Nifty - load from local CSV files
    if 'BANKNIFTY' in symbol.upper():
        logger.info(f"📊 Loading Bank Nifty data from local CSV files...")
        
        # Map to local CSV files in BankNifty-Data-main folder
        csv_files = {
            '1m': 'BankNifty-Data-main/bank-nifty-1m-data.csv',
            '5m': 'BankNifty-Data-main/bank-nifty-5m-data.csv',
            '15m': 'BankNifty-Data-main/bank-nifty-15m-data.csv',
            '1h': 'BankNifty-Data-main/bank-nifty-1h-data.csv',
            '2h': 'BankNifty-Data-main/bank-nifty-2h-data.csv',
            '3h': 'BankNifty-Data-main/bank-nifty-3h-data.csv',
            '1d': 'BankNifty-Data-main/bank-nifty-1d-data.csv'
        }
        
        for interval, csv_path in csv_files.items():
            try:
                from pathlib import Path
                file_path = Path(csv_path)
                
                if not file_path.exists():
                    logger.warning(f"File not found: {csv_path}")
                    continue
                
                logger.info(f"Loading {interval} data from {csv_path}...")
                df = pd.read_csv(csv_path)
                
                # Parse DateTime column (format: DD-MM-YYYY HH:MM:SS or YYYY-MM-DD HH:MM:SS)
                if 'DateTime' in df.columns:
                    df['DateTime'] = pd.to_datetime(df['DateTime'])
                elif 'Date' in df.columns and 'Time' in df.columns:
                    df['DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
                elif 'Date' in df.columns:
                    df['DateTime'] = pd.to_datetime(df['Date'])
                else:
                    logger.warning(f"No DateTime column in {csv_path}")
                    continue
                
                df.set_index('DateTime', inplace=True)
                
                # Keep only OHLCV columns
                required_cols = ['Open', 'High', 'Low', 'Close']
                if not all(col in df.columns for col in required_cols):
                    logger.warning(f"Missing OHLC columns in {csv_path}")
                    continue
                
                # Add Volume if missing
                if 'Volume' not in df.columns:
                    df['Volume'] = 0
                
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                
                # Remove duplicates and sort
                df = df[~df.index.duplicated(keep='first')]
                df.sort_index(inplace=True)
                
                logger.info(f"✓ Loaded {len(df)} candles from {interval} data ({df.index[0]} to {df.index[-1]})")
                datasets.append(df)
                
            except Exception as e:
                logger.warning(f"Failed to load {interval} data: {e}")
        
        if not datasets:
            logger.error("❌ No Bank Nifty data loaded from local files!")
            logger.info("Trying GitHub backup...")
            # Fallback to GitHub download
            for interval in ['1h', '2h', '3h', '1d']:
                try:
                    loader = BankNiftyDataLoader(interval=interval, use_cache=True)
                    df = loader.load_from_github()
                    if df is not None and not df.empty:
                        logger.info(f"✓ Loaded {len(df)} candles ({interval} interval)")
                        datasets.append(df)
                except Exception as e:
                    logger.warning(f"Failed to load {interval} data: {e}")
        
        return datasets
    
    else:
        # Standard symbols - fetch multiple timeframes
        for interval in ['1h', '4h', '1d']:
            try:
                fetcher = YFinanceDataFetcher()
                df = fetcher.fetch_historical_data(
                    symbol=symbol,
                    interval=interval,
                    period='max'
                )
                
                if df is not None and not df.empty:
                    logger.info(f"✓ Loaded {len(df)} candles ({interval} interval)")
                    datasets.append(df)
            except Exception as e:
                logger.warning(f"Failed to load {interval} data: {e}")
    
    return datasets


def intelligent_hyperparameter_tuning(
    strategy_class,
    symbol: str,
    train_data: pd.DataFrame,
    target_win_rate: float = 90.0,
    learning_rates: Optional[List[float]] = None,
    reward_configs: Optional[List[Dict[str, float]]] = None,
    episode_counts: Optional[List[int]] = None,
    n_workers: int = 8,
    batch_size: Optional[int] = None
) -> Tuple[dict, float]:
    """
    Intelligently tune hyperparameters to reach target win rate.
    """
    logger.info(f"🎯 Auto-tuning hyperparameters for {strategy_class.__name__} on {symbol}...")
    
    # Hyperparameter search space - ORIGINAL WORKING CONFIG
    learning_rates = learning_rates or [0.0001, 0.0003, 0.0005, 0.001]
    reward_configs = reward_configs or [
        {'win_bonus': 5.0, 'loss_penalty': -1.5, 'hold_penalty': -0.01},
        {'win_bonus': 10.0, 'loss_penalty': -2.0, 'hold_penalty': -0.02},
        {'win_bonus': 15.0, 'loss_penalty': -2.5, 'hold_penalty': -0.03},
        {'win_bonus': 20.0, 'loss_penalty': -3.0, 'hold_penalty': -0.04}
    ]
    episode_counts = episode_counts or [1500, 2000, 3000, 5000]
    
    # Load combo-level checkpoint
    model_key = f"{strategy_class.__name__}_{symbol}"
    combo_checkpoint = load_combo_checkpoint(model_key)
    
    best_config = combo_checkpoint.get('best_config')
    best_win_rate = combo_checkpoint.get('best_win_rate', 0)
    best_agent = None
    completed_combos = combo_checkpoint.get('completed_combos', [])
    
    total_combinations = len(learning_rates) * len(reward_configs) * len(episode_counts)
    logger.info(f"Testing {total_combinations} hyperparameter combinations for 90%+ target...")
    logger.info(f"Expected duration: {total_combinations * 15} minutes (~{total_combinations * 15 / 60:.1f} hours)")
    
    if completed_combos:
        logger.info(f"🔄 Resuming: {len(completed_combos)}/{total_combinations} combos already tested")
    
    iteration = 0
    for lr in learning_rates:
        for reward_config in reward_configs:
            for episodes in episode_counts:
                iteration += 1
                
                # Create unique combo ID
                combo_id = f"lr{lr}_ep{episodes}_wb{reward_config['win_bonus']}"
                
                # Skip if already completed
                if combo_id in completed_combos:
                    logger.info(f"[{iteration}/{total_combinations}] ⏭️  Skipping {combo_id} (already tested)")
                    continue
                
                logger.info(f"\n[{iteration}/{total_combinations}] Testing: LR={lr}, Episodes={episodes}")
                
                # Initialize strategy and environment
                strategy = strategy_class()
                env = TradingEnvironment(
                    df=train_data,
                    initial_balance=10000
                )
                
                # Train agent with parallel episodes (8 cores)
                agent = PPOAgent(
                    state_size=24,
                    action_size=4,
                    lr=lr,
                    gamma=0.99,
                    clip_epsilon=0.2
                )
                
                # Use sequential training (proven to work)
                training_results = agent.train(
                    env,
                    episodes=episodes,
                    verbose=False
                )
                
                # Evaluate
                win_rate = (env.winning_trades / env.total_trades * 100) if env.total_trades > 0 else 0
                
                logger.info(f"  Result: {win_rate:.1f}% win rate ({env.winning_trades}/{env.total_trades} trades)")
                
                # Track best
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    best_config = {
                        'learning_rate': lr,
                        'reward_config': reward_config,
                        'episodes': episodes
                    }
                    best_agent = agent
                    
                    logger.info(f"  🌟 New best: {win_rate:.1f}%")
                
                # Save combo checkpoint after each test
                completed_combos.append(combo_id)
                save_combo_checkpoint(model_key, completed_combos, best_config, best_win_rate)
                
                # Early exit if target reached
                if win_rate >= target_win_rate:
                    logger.info(f"🎉 TARGET ACHIEVED: {win_rate:.1f}% >= {target_win_rate}%")
                    return best_config, best_win_rate, best_agent
    
    logger.info(f"\n✅ Best configuration: {best_win_rate:.1f}% win rate")
    logger.info(f"   LR: {best_config['learning_rate']}")
    logger.info(f"   Rewards: {best_config['reward_config']}")
    logger.info(f"   Episodes: {best_config['episodes']}")
    
    return best_config, best_win_rate, best_agent


def train_intelligent_brain(
    strategy_name: str,
    symbol: str,
    target_win_rate: float = 90.0
) -> bool:
    """
    Train RL brain to target win rate using intelligent tuning.
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"🧠 TRAINING INTELLIGENT BRAIN")
    logger.info(f"Strategy: {strategy_name} | Symbol: {symbol}")
    logger.info(f"Target: {target_win_rate}% win rate")
    logger.info(f"{'='*80}\n")
    
    # Get strategy class
    strategy_map = {
        'EMA30Strategy': EMA30Strategy,
        'ICTStrategy': ICTStrategy,
        'VCPStrategy': VCPStrategy
    }
    strategy_class = strategy_map[strategy_name]
    
    # Fetch all available data
    logger.info("📊 Fetching maximum historical data...")
    datasets = fetch_all_historical_data(symbol)
    
    if not datasets:
        logger.error(f"❌ No data available for {symbol}")
        return False
    
    # Combine and deduplicate datasets (use longest timeframe)
    logger.info(f"Combining {len(datasets)} datasets...")
    combined_df = pd.concat(datasets).sort_index()
    combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
    
    logger.info(f"✓ Total data: {len(combined_df)} candles ({combined_df.index[0]} to {combined_df.index[-1]})")
    
    # Split: 85% train, 15% validation
    split_idx = int(len(combined_df) * 0.85)
    train_df = combined_df.iloc[:split_idx].copy()
    val_df = combined_df.iloc[split_idx:].copy()
    
    logger.info(f"Training: {len(train_df)} candles | Validation: {len(val_df)} candles")
    
    # Intelligent hyperparameter tuning
    best_config, train_win_rate, best_agent = intelligent_hyperparameter_tuning(
        strategy_class=strategy_class,
        symbol=symbol,
        train_data=train_df,
        target_win_rate=target_win_rate
    )
    
    if train_win_rate < 85.0:
        logger.warning(f"⚠️ Training win rate {train_win_rate:.1f}% below 85% - trying extended training...")
        
        # Extended training with best config
        strategy = strategy_class()
        env = TradingEnvironment(
            df=train_df,
            initial_balance=10000
        )
        
        agent = PPOAgent(
            state_size=24,
            action_size=4,
            lr=best_config['learning_rate'],
            gamma=0.99,
            clip_epsilon=0.2
        )
        
        # Use built-in train method
        extended_episodes = 10000  # Deep training for 90%+ accuracy
        logger.info(f"🚀 Extended deep training: {extended_episodes} episodes (may take hours)...")
        training_results = agent.train(env, episodes=extended_episodes, verbose=True)
        
        best_agent = agent
        
        # Final evaluation
        train_win_rate = (env.winning_trades / env.total_trades * 100) if env.total_trades > 0 else 0
    
    # Validate on unseen data
    logger.info("\n🔍 Validating on unseen data...")
    strategy = strategy_class()
    val_env = TradingEnvironment(
        df=val_df,
        initial_balance=10000
    )
    
    state = val_env.reset()
    done = False
    step = 0
    
    while not done and step < 1000:
        action, _ = agent.select_action(state, training=False)
        state, _, done, _ = val_env.step(action)
        step += 1
    
    val_win_rate = (val_env.winning_trades / val_env.total_trades * 100) if val_env.total_trades > 0 else 0
    
    logger.info(f"✅ Validation: {val_win_rate:.1f}% win rate ({val_env.winning_trades}/{val_env.total_trades} trades)")
    
    # Save only if performance meets 85%+ threshold for 90% real-world target
    if val_win_rate >= 85.0:
        slug = strategy_name.lower().replace('strategy', '')
        symbol_safe = symbol.replace('=', '_').replace('.', '_').replace('^', '_').lower()
        model_path = Path('models') / 'rl_brain' / f'{slug}_{symbol_safe}.pth'
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        best_agent.save(str(model_path))
        logger.info(f"💾 Brain saved: {model_path}")
        
        # Save metadata
        brain = IntelligentRLBrain()
        brain.save_brain_state(
            strategy=strategy_name,
            symbol=symbol,
            metadata={
                'episodes': best_config['episodes'],
                'train_win_rate': train_win_rate,
                'val_win_rate': val_win_rate,
                'total_samples': len(combined_df),
                'best_reward': 0,
                'version': 1,
                'data_sources': [str(type(ds)) for ds in datasets]
            }
        )
        
        logger.info(f"🎉 SUCCESS: {val_win_rate:.1f}% validation win rate!")
        return True
    
    else:
        logger.error(f"❌ FAILED: {val_win_rate:.1f}% < 85% threshold")
        logger.error("Model not saved - needs 85%+ validation accuracy for 90% target")
        logger.error("Recommendation: Add more historical data or adjust reward scaling")
        return False


def load_checkpoint():
    """Load training checkpoint to resume."""
    checkpoint_file = Path('training_checkpoint.json')
    
    # First try to load from previous Kaggle output
    if Path('/kaggle/input').exists():
        for dataset_dir in Path('/kaggle/input').iterdir():
            checkpoint_path = dataset_dir / 'training_checkpoint.json'
            if checkpoint_path.exists():
                logger.info(f"🔄 Loading model checkpoint from previous session: {checkpoint_path}")
                with open(checkpoint_path, 'r') as f:
                    return json.load(f)
    
    # Otherwise try local file
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    
    return {'completed_models': [], 'current_index': 0}

def load_combo_checkpoint(model_key: str):
    """Load combo-level checkpoint for a specific model."""
    filename = f'combo_checkpoint_{model_key}.json'
    
    # First try to load from previous Kaggle output (if exists from last session)
    previous_output = Path('/kaggle/input') / 'your-notebook-name' / filename
    checkpoint_file = Path(filename)
    
    # Check if we're on Kaggle and have previous output
    if Path('/kaggle/input').exists():
        # Look for any dataset that might have our checkpoints
        for dataset_dir in Path('/kaggle/input').iterdir():
            checkpoint_path = dataset_dir / filename
            if checkpoint_path.exists():
                logger.info(f"🔄 Loading checkpoint from previous session: {checkpoint_path}")
                with open(checkpoint_path, 'r') as f:
                    return json.load(f)
    
    # Otherwise try local file
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    
    return {'completed_combos': [], 'best_config': None, 'best_win_rate': 0}

def save_combo_checkpoint(model_key: str, completed_combos: list, best_config: dict, best_win_rate: float):
    """Save combo-level checkpoint after each hyperparameter test."""
    checkpoint = {
        'model_key': model_key,
        'completed_combos': completed_combos,
        'best_config': best_config,
        'best_win_rate': best_win_rate,
        'last_updated': datetime.now().isoformat()
    }
    
    filename = f'combo_checkpoint_{model_key}.json'
    
    # Save to current directory (local or Kaggle working)
    with open(filename, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    # CRITICAL: Also save to Kaggle persistent output (survives session restart)
    kaggle_output_dir = Path('/kaggle/working')
    if kaggle_output_dir.exists():
        # Save to working (will be copied to output dataset automatically)
        output_file = kaggle_output_dir / filename
        with open(output_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        # Also save models directory structure for persistence
        models_dir = kaggle_output_dir / 'models' / 'rl_brain'
        models_dir.mkdir(parents=True, exist_ok=True)

def save_checkpoint(completed_models: list, current_index: int):
    """Save training progress checkpoint."""
    checkpoint = {
        'completed_models': completed_models,
        'current_index': current_index,
        'timestamp': datetime.now().isoformat()
    }
    
    # Save to working directory
    with open('training_checkpoint.json', 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    # CRITICAL: Save to Kaggle working (will be saved to output dataset)
    kaggle_output = Path('/kaggle/working/training_checkpoint.json')
    if kaggle_output.parent.exists():
        with open(kaggle_output, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        logger.info(f"💾 Checkpoint saved to Kaggle output: {len(completed_models)}/{current_index} models")
    
    logger.info(f"💾 Checkpoint saved: {len(completed_models)}/{current_index} models complete")

def main():
    """Train intelligent RL brains for all strategies."""
    
    print("\n" + "="*80)
    print("🧠 INTELLIGENT RL BRAIN TRAINING SYSTEM")
    print("="*80)
    print("Goal: Train once to 90%+ historical accuracy")
    print("Expected real-world: 70%+ win rate")
    print("Self-improvement: Continuous learning from live trades")
    print("="*80 + "\n")
    
    # Training configuration - FULL COVERAGE
    TRAINING_TASKS = [
        # Gold (GC=F) - All 3 strategies
        ('EMA30Strategy', 'GC=F', 90.0),
        ('ICTStrategy', 'GC=F', 90.0),
        ('VCPStrategy', 'GC=F', 90.0),
        
        # Bank Nifty - All 3 strategies
        ('EMA30Strategy', 'BANKNIFTY', 90.0),
        ('ICTStrategy', 'BANKNIFTY', 90.0),
        ('VCPStrategy', 'BANKNIFTY', 90.0),
        
        # Apple - All 3 strategies
        ('EMA30Strategy', 'AAPL', 90.0),
        ('ICTStrategy', 'AAPL', 90.0),
        ('VCPStrategy', 'AAPL', 90.0),
        
        # Microsoft - All 3 strategies
        ('EMA30Strategy', 'MSFT', 90.0),
        ('ICTStrategy', 'MSFT', 90.0),
        ('VCPStrategy', 'MSFT', 90.0),
    ]
    # Total: 12 models (4 symbols × 3 strategies)
    
    print(f"📋 TRAINING QUEUE: {len(TRAINING_TASKS)} models")
    print("="*80)
    for i, (strategy, symbol, target) in enumerate(TRAINING_TASKS, 1):
        print(f"  {i}. {strategy} on {symbol} (target: {target}%)")
    print("="*80)
    print(f"\n⏱️  Estimated time: {len(TRAINING_TASKS) * 2}-{len(TRAINING_TASKS) * 4} hours")
    print("💡 Tip: Run in background with: nohup python train_intelligent_brain.py &\n")
    
    # Load checkpoint to resume training
    checkpoint = load_checkpoint()
    completed_models = checkpoint['completed_models']
    start_idx = checkpoint['current_index']
    
    if start_idx > 0:
        print(f"🔄 RESUMING from checkpoint: {start_idx}/{len(TRAINING_TASKS)} models already trained")
        print(f"✅ Previously completed: {', '.join(completed_models)}\n")
    
    results = {}
    
    for idx, (strategy, symbol, target) in enumerate(TRAINING_TASKS, 1):
        model_key = f"{strategy}_{symbol}"
        
        # Skip already completed models
        if model_key in completed_models:
            print(f"⏭️  SKIPPING {idx}/{len(TRAINING_TASKS)}: {model_key} (already trained)")
            results[model_key] = True
            continue
        
        print(f"\n{'='*80}")
        print(f"🎯 TASK {idx}/{len(TRAINING_TASKS)}: {strategy} on {symbol}")
        print(f"{'='*80}\n")
        
        success = train_intelligent_brain(
            strategy_name=strategy,
            symbol=symbol,
            target_win_rate=target
        )
        results[model_key] = success
        
        # Save checkpoint after each model
        if success:
            completed_models.append(model_key)
        save_checkpoint(completed_models, idx)
        
        # Progress update
        completed = sum(1 for v in results.values() if v)
        print(f"\n✅ Completed: {len(results)}/{len(TRAINING_TASKS)} | Successful: {completed}/{len(results)}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 TRAINING SUMMARY")
    print("="*80)
    
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    for key, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {key}")
    
    print(f"\nSuccess Rate: {successful}/{total}")
    print("="*80)
    
    if successful == total:
        print("\n🎉 ALL BRAINS TRAINED SUCCESSFULLY!")
        print("Models saved to: models/rl_brain/")
        print("\n📝 Next steps:")
        print("1. Run: python run.py (launch trading dashboard)")
        print("2. System will use trained brains automatically")
        print("3. Brains will self-improve from live paper trades")
        print("4. Monitor performance in: models/rl_brain/performance_history.csv")
    else:
        print("\n⚠️ Some models failed to reach 85%+ threshold")
        print("Consider: Adjust reward scaling or get more historical data")


if __name__ == "__main__":
    main()
