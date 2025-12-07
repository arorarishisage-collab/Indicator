"""
Advanced Reinforcement Learning Trading System
Uses PPO (Proximal Policy Optimization) with LSTM networks for adaptive trading
Includes feature engineering, reward shaping, and continuous learning
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime
import json
from pathlib import Path
from collections import deque
import pickle

# Deep Learning imports
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.distributions import Categorical
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available. Install with: pip install torch")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set PyTorch threading globally (once at module import)
if TORCH_AVAILABLE:
    try:
        torch.set_num_threads(8)  # Use all 8 cores
        torch.set_num_interop_threads(8)
    except RuntimeError:
        pass  # Already set


class TradingEnvironment:
    """
    Advanced Trading Environment for RL
    - Multi-dimensional state space (price, indicators, regime, portfolio)
    - Continuous learning with experience replay
    - Reward shaping for better convergence
    """
    
    def __init__(self, 
                 df: pd.DataFrame,
                 initial_balance: float = 10000,
                 transaction_cost: float = 0.001,
                 max_position_size: float = 1.0,
                 lookback_window: int = 50):
        """
        Initialize trading environment
        
        Args:
            df: DataFrame with OHLCV and technical indicators
            initial_balance: Starting capital
            transaction_cost: Transaction cost per trade (0.1%)
            max_position_size: Maximum position size as fraction of capital
            lookback_window: Number of bars to include in state
        """
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        self.max_position_size = max_position_size
        self.lookback_window = lookback_window
        
        # Environment state
        self.current_step = lookback_window
        self.balance = initial_balance
        self.position = 0  # -1 (short), 0 (flat), 1 (long)
        self.position_size = 0
        self.entry_price = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.max_balance = initial_balance
        
        # Experience replay buffer
        self.experience_buffer = deque(maxlen=10000)

        # Feedback-driven tuning
        self.action_bias = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
        self.win_rate_target = 0.6
        self.loss_penalty_scale = 0.0
        
        # Feature engineering
        self._prepare_features()
    
    def _prepare_features(self):
        """Prepare engineered features for RL"""
        df = self.df.copy()
        
        # Price-based features
        df['returns'] = df['Close'].pct_change()
        df['log_returns'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # Volatility features
        df['volatility'] = df['returns'].rolling(20).std()
        df['atr'] = self._calculate_atr(df)
        
        # Momentum features
        df['rsi'] = self._calculate_rsi(df['Close'], 14)
        df['macd'], df['macd_signal'] = self._calculate_macd(df['Close'])
        df['momentum'] = df['Close'] - df['Close'].shift(10)
        
        # Trend features
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['sma_50'] = df['Close'].rolling(50).mean()
        df['ema_12'] = df['Close'].ewm(span=12).mean()
        df['ema_26'] = df['Close'].ewm(span=26).mean()
        
        # Volume features
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma']
        
        # Price action features
        df['high_low_ratio'] = (df['High'] - df['Low']) / df['Close']
        df['close_open_ratio'] = (df['Close'] - df['Open']) / df['Open']
        
        # Market structure
        df['higher_high'] = (df['High'] > df['High'].shift(1)).astype(int)
        df['lower_low'] = (df['Low'] < df['Low'].shift(1)).astype(int)
        
        self.df = df.fillna(0)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Calculate MACD"""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        return macd, signal
    
    def reset(self) -> np.ndarray:
        """Reset environment to initial state"""
        self.current_step = self.lookback_window
        self.balance = self.initial_balance
        self.position = 0
        self.position_size = 0
        self.entry_price = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.max_balance = self.initial_balance
        
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """
        Get current state representation
        Returns normalized feature vector
        """
        if self.current_step < self.lookback_window:
            return np.zeros(self._get_state_size())
        
        # Get historical window
        start = self.current_step - self.lookback_window
        end = self.current_step
        
        window = self.df.iloc[start:end]
        
        # Price features (normalized)
        close_prices = window['Close'].values
        normalized_prices = (close_prices - close_prices.mean()) / (close_prices.std() + 1e-8)
        
        # Technical indicators
        features = []
        
        # Latest values of key indicators
        latest = window.iloc[-1]
        features.extend([
            latest['returns'] / (latest['volatility'] + 1e-8),  # Normalized return
            latest['rsi'] / 100,  # RSI normalized to [0,1]
            np.tanh(latest['macd'] / (latest['Close'] + 1e-8)),  # MACD normalized
            latest['volume_ratio'],
            latest['high_low_ratio'],
            latest['close_open_ratio'],
        ])
        
        # Trend indicators
        features.extend([
            1 if latest['Close'] > latest['sma_20'] else 0,
            1 if latest['sma_20'] > latest['sma_50'] else 0,
            1 if latest['ema_12'] > latest['ema_26'] else 0,
        ])
        
        # Position information
        features.extend([
            self.position / 1.0,  # Normalize position (-1, 0, 1)
            self.position_size / self.max_position_size,
            (self.balance - self.initial_balance) / self.initial_balance,  # P&L %
        ])
        
        # Market regime features (simplified)
        volatility_percentile = window['volatility'].rank(pct=True).iloc[-1]
        volume_percentile = window['volume_ratio'].rank(pct=True).iloc[-1]
        features.extend([volatility_percentile, volume_percentile])
        
        # Time-series features (last 10 returns)
        recent_returns = window['returns'].tail(10).values
        features.extend(recent_returns.tolist())
        
        state = np.array(features, dtype=np.float32)
        
        # Clip extreme values
        state = np.clip(state, -10, 10)
        
        return state
    
    def _get_state_size(self) -> int:
        """Get size of state vector"""
        # 6 indicators + 3 trend + 3 position + 2 regime + 10 returns = 24
        return 24
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute action and return next state, reward, done, info
        
        Actions:
        0 = Hold/Do nothing
        1 = Buy/Long
        2 = Sell/Short
        3 = Close position
        """
        current_price = self.df.iloc[self.current_step]['Close']
        
        # Execute action
        reward = 0
        info = {}
        
        if action == 1 and self.position <= 0:  # Buy
            # Close short if exists
            if self.position == -1:
                reward += self._close_position(current_price)
            
            # Open long
            self.position = 1
            self.entry_price = current_price * (1 + self.transaction_cost)
            self.position_size = self.balance * self.max_position_size / self.entry_price
            self.total_trades += 1
            info['action'] = 'BUY'
        
        elif action == 2 and self.position >= 0:  # Sell
            # Close long if exists
            if self.position == 1:
                reward += self._close_position(current_price)
            
            # Open short
            self.position = -1
            self.entry_price = current_price * (1 - self.transaction_cost)
            self.position_size = self.balance * self.max_position_size / self.entry_price
            self.total_trades += 1
            info['action'] = 'SELL'
        
        elif action == 3 and self.position != 0:  # Close
            reward += self._close_position(current_price)
            info['action'] = 'CLOSE'
        
        else:  # Hold
            info['action'] = 'HOLD'
            # Small penalty for holding losing positions
            if self.position != 0:
                unrealized_pnl = self._calculate_unrealized_pnl(current_price)
                if unrealized_pnl < 0:
                    reward -= 0.001  # Small penalty

        reward += self.action_bias.get(action, 0.0)
        
        # Move to next step
        self.current_step += 1
        
        # Check if episode is done
        done = self.current_step >= len(self.df) - 1 or self.balance <= self.initial_balance * 0.5
        
        # Calculate reward with shaping
        reward += self._calculate_reward(current_price, done)
        
        # Update max balance for drawdown calculation
        self.max_balance = max(self.max_balance, self.balance)
        
        # Get next state
        next_state = self._get_state()
        
        # Store experience
        self.experience_buffer.append({
            'state': self._get_state(),
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'done': done
        })
        
        info.update({
            'balance': self.balance,
            'position': self.position,
            'total_trades': self.total_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        })
        
        return next_state, reward, done, info
    
    def _close_position(self, current_price: float) -> float:
        """Close current position and return reward"""
        if self.position == 0:
            return 0
        
        # Calculate P&L
        if self.position == 1:  # Long
            exit_price = current_price * (1 - self.transaction_cost)
            pnl = (exit_price - self.entry_price) * self.position_size
        else:  # Short
            exit_price = current_price * (1 + self.transaction_cost)
            pnl = (self.entry_price - exit_price) * self.position_size
        
        self.balance += pnl
        
        # Track winning trades
        if pnl > 0:
            self.winning_trades += 1
        
        # Reset position
        self.position = 0
        self.position_size = 0
        self.entry_price = 0
        
        # Return normalized reward
        return pnl / self.initial_balance
    
    def _calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L for open position"""
        if self.position == 0:
            return 0
        
        if self.position == 1:  # Long
            return (current_price - self.entry_price) * self.position_size
        else:  # Short
            return (self.entry_price - current_price) * self.position_size
    
    def _calculate_reward(self, current_price: float, done: bool) -> float:
        """
        Calculate shaped reward for better learning
        Combines immediate P&L with risk-adjusted metrics
        """
        reward = 0
        
        # 1. P&L-based reward (primary)
        if self.position != 0:
            unrealized_pnl = self._calculate_unrealized_pnl(current_price)
            reward += unrealized_pnl / self.initial_balance
        
        # 2. Sharpe ratio bonus (risk-adjusted)
        if self.total_trades >= 10:
            win_rate = self.winning_trades / self.total_trades
            if win_rate > self.win_rate_target:
                reward += 0.1  # Bonus for high win rate
        
        # 3. Drawdown penalty
        drawdown = (self.max_balance - self.balance) / self.max_balance
        if drawdown > 0.2:
            reward -= 0.5  # Heavy penalty for large drawdown

        # Experience-based penalty for underwater trades
        if self.position != 0 and self.loss_penalty_scale > 0:
            unrealized_pnl = self._calculate_unrealized_pnl(current_price)
            if unrealized_pnl < 0:
                reward -= self.loss_penalty_scale * abs(unrealized_pnl) / self.initial_balance
        
        # 4. Episode completion bonus
        if done and self.balance > self.initial_balance:
            profit_pct = (self.balance - self.initial_balance) / self.initial_balance
            reward += profit_pct * 2  # Bonus for profitable episode
        
        return reward
    
    def get_action_space_size(self) -> int:
        """Get number of possible actions"""
        return 4  # Hold, Buy, Sell, Close

    def configure_from_feedback(
        self,
        action_bias: Optional[Dict[int, float]] = None,
        win_rate_target: Optional[float] = None,
        loss_penalty_scale: Optional[float] = None,
    ) -> None:
        """Apply paper-trade feedback into reward shaping."""
        if action_bias:
            for action, bias in action_bias.items():
                if action in self.action_bias:
                    self.action_bias[action] = bias
        if win_rate_target is not None:
            self.win_rate_target = max(0.4, min(0.9, win_rate_target))
        if loss_penalty_scale is not None:
            self.loss_penalty_scale = max(0.0, loss_penalty_scale)


class LSTMPolicyNetwork(nn.Module):
    """
    LSTM-based Policy Network for PPO
    Uses LSTM to capture temporal dependencies in market data
    """
    
    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        super(LSTMPolicyNetwork, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = 2
        
        # LSTM layer for temporal features
        self.lstm = nn.LSTM(state_size, hidden_size, batch_first=True, num_layers=self.num_layers)
        
        # Policy head (actor)
        self.policy_fc1 = nn.Linear(hidden_size, 64)
        self.policy_fc2 = nn.Linear(64, action_size)
        
        # Value head (critic)
        self.value_fc1 = nn.Linear(hidden_size, 64)
        self.value_fc2 = nn.Linear(64, 1)
        
        # Dropout for regularization
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x, hidden=None):
        """Forward pass"""
        # Reshape for LSTM if needed (batch, seq, features)
        if len(x.shape) == 2:
            x = x.unsqueeze(1)  # Add sequence dimension
        
        # Initialize hidden state on same device as input if not provided
        if hidden is None:
            batch_size = x.size(0)
            hidden = (torch.zeros(self.num_layers, batch_size, self.hidden_size, device=x.device),
                     torch.zeros(self.num_layers, batch_size, self.hidden_size, device=x.device))
        
        # LSTM forward
        lstm_out, hidden = self.lstm(x, hidden)
        lstm_out = lstm_out[:, -1, :]  # Take last output
        
        # Policy (actor)
        policy = F.relu(self.policy_fc1(lstm_out))
        policy = self.dropout(policy)
        policy = self.policy_fc2(policy)
        action_probs = F.softmax(policy, dim=-1)
        
        # Value (critic)
        value = F.relu(self.value_fc1(lstm_out))
        value = self.value_fc2(value)
        
        return action_probs, value, hidden


def _parallel_worker(worker_id, num_episodes, env_data, agent_state, device_type):
    """
    Worker function for parallel episode training (module-level for pickling)
    """
    # Recreate environment
    worker_env = TradingEnvironment(
        df=env_data['df'],
        initial_balance=env_data['initial_balance'],
        transaction_cost=env_data['transaction_cost'],
        max_position_size=env_data['max_position_size'],
        lookback_window=env_data['lookback_window']
    )
    
    # Recreate agent with same architecture
    worker_agent = PPOAgent(
        state_size=agent_state['state_size'],
        action_size=agent_state['action_size'],
        lr=agent_state['lr'],
        gamma=agent_state['gamma'],
        clip_epsilon=agent_state['clip_epsilon']
    )
    
    # Load policy weights
    worker_agent.policy.load_state_dict(agent_state['policy_state'])
    worker_agent.policy.eval()
    
    # Force CPU for worker (avoid GPU conflicts)
    worker_agent.device = torch.device("cpu")
    worker_agent.policy = worker_agent.policy.to(worker_agent.device)
    
    # Train episodes
    worker_results = []
    for ep in range(num_episodes):
        state = worker_env.reset()
        episode_reward = 0
        done = False
        
        states, actions, rewards, log_probs, values = [], [], [], [], []
        
        while not done:
            action, log_prob = worker_agent.select_action(state, training=True)
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(worker_agent.device)
            with torch.no_grad():
                _, value, _ = worker_agent.policy(state_tensor)
            
            next_state, reward, done, info = worker_env.step(action)
            
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            log_probs.append(log_prob)
            values.append(value.item())
            
            state = next_state
            episode_reward += reward
        
        worker_results.append({
            'reward': episode_reward,
            'length': len(states),
            'states': states,
            'actions': actions,
            'rewards': rewards,
            'log_probs': log_probs,
            'values': values
        })
    
    return worker_results


class PPOAgent:
    """
    Proximal Policy Optimization Agent
    - Clip objective for stable learning
    - LSTM network for temporal understanding
    - Experience replay for sample efficiency
    - M2 GPU acceleration for 5-10x speedup
    """
    
    def __init__(self, 
                 state_size: int,
                 action_size: int,
                 lr: float = 0.0003,
                 gamma: float = 0.99,
                 clip_epsilon: float = 0.2,
                 epochs: int = 10):
        """
        Initialize PPO agent
        
        Args:
            state_size: Dimension of state space
            action_size: Number of possible actions
            lr: Learning rate
            gamma: Discount factor
            clip_epsilon: PPO clipping parameter
            epochs: Number of training epochs per update
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required for RL. Install with: pip install torch")
        
        # Force CPU for parallel training (better for RL)
        self.device = torch.device("cpu")
        print("✅ Using CPU with 8 cores for parallel training")
        
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.clip_epsilon = clip_epsilon
        self.epochs = epochs
        
        # Policy network (move to M2 GPU)
        self.policy = LSTMPolicyNetwork(state_size, action_size).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        
        # Training metrics
        self.episode_rewards = []
        self.episode_lengths = []
        
    def select_action(self, state: np.ndarray, training: bool = True) -> Tuple[int, float]:
        """
        Select action using current policy
        
        Args:
            state: Current state
            training: If True, sample from distribution; if False, take argmax
            
        Returns:
            Tuple of (action, log_prob)
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action_probs, _, _ = self.policy(state_tensor)
        
        if training:
            dist = Categorical(action_probs)
            action = dist.sample()
            log_prob = dist.log_prob(action)
            return action.item(), log_prob.item()
        else:
            action = torch.argmax(action_probs, dim=-1)
            return action.item(), 0.0
    
    def train(self, env: TradingEnvironment, episodes: int = 1000, verbose: bool = True) -> Dict:
        """
        Train agent on environment
        
        Args:
            env: Trading environment
            episodes: Number of episodes to train
            verbose: Print progress
            
        Returns:
            Training metrics dictionary
        """
        best_reward = -np.inf
        
        for episode in range(episodes):
            state = env.reset()
            episode_reward = 0
            episode_length = 0
            done = False
            
            # Collect trajectory
            states, actions, rewards, log_probs, values = [], [], [], [], []
            
            while not done:
                # Select action
                action, log_prob = self.select_action(state, training=True)
                
                # Get value estimate
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    _, value, _ = self.policy(state_tensor)
                
                # Execute action
                next_state, reward, done, info = env.step(action)
                
                # Store transition
                states.append(state)
                actions.append(action)
                rewards.append(reward)
                log_probs.append(log_prob)
                values.append(value.item())
                
                state = next_state
                episode_reward += reward
                episode_length += 1
            
            # Update policy
            self._update_policy(states, actions, rewards, log_probs, values)
            
            # Track metrics
            self.episode_rewards.append(episode_reward)
            self.episode_lengths.append(episode_length)
            
            if episode_reward > best_reward:
                best_reward = episode_reward
            
            # Log progress
            if verbose and (episode + 1) % 50 == 0:
                avg_reward = np.mean(self.episode_rewards[-50:])
                win_rate = info.get('win_rate', 0)
                logger.info(
                    f"Episode {episode+1}/{episodes} | "
                    f"Avg Reward: {avg_reward:.4f} | "
                    f"Best: {best_reward:.4f} | "
                    f"Win Rate: {win_rate:.2%} | "
                    f"Balance: ${info['balance']:.2f}"
                )
        
        return {
            'episode_rewards': self.episode_rewards,
            'episode_lengths': self.episode_lengths,
            'best_reward': best_reward,
            'final_balance': env.balance
        }
    
    def train_parallel(
        self,
        env: TradingEnvironment,
        episodes: int = 1000,
        n_workers: int = 8,
        verbose: bool = True,
        batch_size: Optional[int] = None
    ) -> Dict:
        """
        Train agent with parallel episodes using threading (works with GPU)
        Runs multiple episodes concurrently
        
        Args:
            env: Trading environment
            episodes: Total number of episodes
            n_workers: Number of parallel threads
            verbose: Print progress
            batch_size: Number of completed episodes to aggregate before a PPO update
            
        Returns:
            Training metrics dictionary
        """
        import concurrent.futures
        import threading
        
        effective_batch_size = max(1, batch_size or n_workers)
        if verbose:
            logger.info(
                f"🚀 Training with {n_workers} parallel threads (CPU cores) | Batch size: {effective_batch_size} episodes"
            )
        
        # Lock for thread-safe updates
        update_lock = threading.Lock()
        best_reward = -np.inf
        
        def train_episode(episode_id):
            """Train a single episode"""
            # Each thread gets its own environment copy
            thread_env = TradingEnvironment(
                df=env.df.copy(),
                initial_balance=env.initial_balance,
                transaction_cost=env.transaction_cost,
                max_position_size=env.max_position_size,
                lookback_window=env.lookback_window
            )
            
            state = thread_env.reset()
            episode_reward = 0
            done = False
            
            states, actions, rewards, log_probs, values = [], [], [], [], []
            
            while not done:
                action, log_prob = self.select_action(state, training=True)
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    _, value, _ = self.policy(state_tensor)
                
                next_state, reward, done, info = thread_env.step(action)
                
                states.append(state)
                actions.append(action)
                rewards.append(reward)
                log_probs.append(log_prob)
                values.append(value.item())
                
                state = next_state
                episode_reward += reward
            
            return {
                'reward': episode_reward,
                'length': len(states),
                'states': states,
                'actions': actions,
                'rewards': rewards,
                'log_probs': log_probs,
                'values': values
            }
        
        # Run episodes in parallel using thread pool with batched updates
        batch_update_size = effective_batch_size
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
            # Submit all episodes
            futures = [executor.submit(train_episode, i) for i in range(episodes)]
            
            # Collect results in batches
            batch_results = []
            completed = 0
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                batch_results.append(result)
                completed += 1
                
                # Update policy after collecting batch_update_size episodes
                if len(batch_results) >= batch_update_size:
                    with update_lock:
                        # Batch all experiences together for single update
                        all_states, all_actions, all_rewards, all_log_probs, all_values = [], [], [], [], []
                        
                        for batch_result in batch_results:
                            all_states.extend(batch_result['states'])
                            all_actions.extend(batch_result['actions'])
                            all_rewards.extend(batch_result['rewards'])
                            all_log_probs.extend(batch_result['log_probs'])
                            all_values.extend(batch_result['values'])
                            
                            self.episode_rewards.append(batch_result['reward'])
                            self.episode_lengths.append(batch_result['length'])
                            
                            if batch_result['reward'] > best_reward:
                                best_reward = batch_result['reward']
                        
                        # Single policy update for entire batch
                        self._update_policy(all_states, all_actions, all_rewards, all_log_probs, all_values)
                        
                        if verbose and completed % (batch_update_size * 2) == 0:
                            avg_reward = np.mean(self.episode_rewards[-100:]) if len(self.episode_rewards) >= 100 else np.mean(self.episode_rewards)
                            logger.info(f"Progress: {completed}/{episodes} episodes | Avg Reward: {avg_reward:.4f} | Best: {best_reward:.4f}")
                    
                    batch_results = []  # Clear batch
            
            # Update remaining episodes in final batch
            if batch_results:
                with update_lock:
                    all_states, all_actions, all_rewards, all_log_probs, all_values = [], [], [], [], []
                    
                    for batch_result in batch_results:
                        all_states.extend(batch_result['states'])
                        all_actions.extend(batch_result['actions'])
                        all_rewards.extend(batch_result['rewards'])
                        all_log_probs.extend(batch_result['log_probs'])
                        all_values.extend(batch_result['values'])
                        
                        self.episode_rewards.append(batch_result['reward'])
                        self.episode_lengths.append(batch_result['length'])
                        
                        if batch_result['reward'] > best_reward:
                            best_reward = batch_result['reward']
                    
                    # Final policy update
                    self._update_policy(all_states, all_actions, all_rewards, all_log_probs, all_values)
        
        if verbose:
            avg_reward = np.mean(self.episode_rewards[-episodes:])
            logger.info(f"✅ Completed {episodes} episodes | Avg Reward: {avg_reward:.4f} | Best: {best_reward:.4f}")
        
        return {
            'episode_rewards': self.episode_rewards,
            'episode_lengths': self.episode_lengths,
            'best_reward': best_reward,
            'final_balance': env.balance
        }
    
    def _update_policy(self, states, actions, rewards, old_log_probs, values):
        """Update policy using PPO objective"""
        # Calculate returns and advantages
        returns = self._calculate_returns(rewards)
        advantages = returns - np.array(values)
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        advantages = returns - np.array(values)
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Convert to tensors (move to device)
        states_tensor = torch.FloatTensor(np.array(states)).to(self.device)
        actions_tensor = torch.LongTensor(actions).to(self.device)
        returns_tensor = torch.FloatTensor(returns).to(self.device)
        advantages_tensor = torch.FloatTensor(advantages).to(self.device)
        old_log_probs_tensor = torch.FloatTensor(old_log_probs).to(self.device)
        
        # PPO update
        for _ in range(self.epochs):
            # Forward pass
            action_probs, values_pred, _ = self.policy(states_tensor)
            
            # Calculate new log probs
            dist = Categorical(action_probs)
            new_log_probs = dist.log_prob(actions_tensor)
            
            # PPO ratio
            ratio = torch.exp(new_log_probs - old_log_probs_tensor)
            
            # Clipped surrogate objective
            surr1 = ratio * advantages_tensor
            surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages_tensor
            actor_loss = -torch.min(surr1, surr2).mean()
            
            # Value loss
            critic_loss = F.mse_loss(values_pred.squeeze(), returns_tensor)
            
            # Entropy bonus for exploration
            entropy = dist.entropy().mean()
            
            # Total loss
            loss = actor_loss + 0.5 * critic_loss - 0.01 * entropy
            
            # Optimize
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
            self.optimizer.step()
    
    def _calculate_returns(self, rewards: List[float]) -> np.ndarray:
        """Calculate discounted returns"""
        returns = []
        R = 0
        for r in reversed(rewards):
            R = r + self.gamma * R
            returns.insert(0, R)
        return np.array(returns)
    
    def save(self, filepath: str):
        """Save agent"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'episode_rewards': self.episode_rewards,
        }, filepath)
        logger.info(f"Agent saved to {filepath}")
    
    def load(self, filepath: str):
        """Load agent"""
        # PyTorch 2.6+ requires weights_only=False for backward compatibility
        checkpoint = torch.load(filepath, weights_only=False)
        self.policy.load_state_dict(checkpoint['policy_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.episode_rewards = checkpoint.get('episode_rewards', [])
        logger.info(f"Agent loaded from {filepath}")


# Example usage and testing
if __name__ == '__main__':
    print("\n🤖 Testing Advanced RL Trading System\n")
    
    if not TORCH_AVAILABLE:
        print("❌ PyTorch not installed. Install with:")
        print("   pip install torch")
        exit(1)
    
    # Generate sample data
    from data_fetch_yfinance import YFinanceDataFetcher
    
    fetcher = YFinanceDataFetcher()
    df = fetcher.fetch_historical_data('GC=F', period='2y', interval='1d')
    
    print(f"Data: {len(df)} days of gold prices\n")
    
    # Create environment
    env = TradingEnvironment(df, initial_balance=10000)
    
    print(f"Environment:")
    print(f"  State size: {env._get_state_size()}")
    print(f"  Action space: {env.get_action_space_size()}")
    print(f"  Initial balance: ${env.initial_balance:,.0f}\n")
    
    # Create agent
    agent = PPOAgent(
        state_size=env._get_state_size(),
        action_size=env.get_action_space_size(),
        lr=0.0003,
        gamma=0.99,
        clip_epsilon=0.2
    )
    
    print("="*70)
    print("TRAINING PPO AGENT")
    print("="*70)
    
    # Train agent
    metrics = agent.train(env, episodes=200, verbose=True)
    
    print("\n" + "="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    print(f"Best Episode Reward: {metrics['best_reward']:.4f}")
    print(f"Final Balance: ${metrics['final_balance']:,.2f}")
    print(f"Total Return: {((metrics['final_balance'] / 10000 - 1) * 100):.2f}%")
    
    # Save agent
    agent.save('models/ppo_trading_agent.pth')
    
    print("\n✅ Advanced RL System Ready!")
    print("\nNext steps:")
    print("1. Train on more data (5+ years)")
    print("2. Tune hyperparameters (lr, gamma, clip_epsilon)")
    print("3. Add more sophisticated reward shaping")
    print("4. Implement ensemble of agents")
    print("5. Deploy with live_scheduler for continuous learning")
