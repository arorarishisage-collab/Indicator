#!/usr/bin/env python3
"""Profile training performance to find bottlenecks"""

import torch
import time
import numpy as np
from backend.advanced_rl_trading_system import PPOAgent, TradingEnvironment
from backend.data_fetch import DataFetcher

print("🔬 Training Performance Profiler")
print("=" * 60)

# Check device
print(f"\n📱 Device: {torch.device('mps' if torch.backends.mps.is_available() else 'cpu')}")
print(f"   MPS Available: {torch.backends.mps.is_available()}")

# Create small test environment
print("\n📊 Loading test data...")
df = DataFetcher().fetch_data(symbol="GC=F", period="1mo", interval="1h")
print(f"   Loaded {len(df)} candles")

env = TradingEnvironment(df=df, lookback_window=20)
state_size = env._get_state_size()
action_size = env.get_action_space_size()

print(f"   State size: {state_size}, Action size: {action_size}")

# Create agent
print("\n🤖 Creating PPO Agent...")
agent = PPOAgent(state_size=state_size, action_size=action_size, lr=0.0001)

# Test different episode counts
for episodes in [10, 50, 100]:
    print(f"\n⏱️  Testing {episodes} episodes...")
    
    start_time = time.time()
    metrics = agent.train(env, episodes=episodes, verbose=False)
    elapsed = time.time() - start_time
    
    print(f"   Time: {elapsed:.1f}s ({elapsed/episodes:.2f}s per episode)")
    print(f"   Avg reward: {np.mean(metrics['episode_rewards']):.2f}")

# Calculate projected time
print("\n" + "=" * 60)
print("📈 PROJECTIONS:")
print("=" * 60)

# Assume 2000 episodes per combo
episodes_per_combo = 2000
seconds_per_episode = elapsed / episodes  # From last test

time_per_combo_min = (episodes_per_combo * seconds_per_episode) / 60
total_time_hours = (48 * time_per_combo_min) / 60

print(f"   Seconds per episode: {seconds_per_episode:.2f}")
print(f"   Minutes per combo (2000 episodes): {time_per_combo_min:.1f}")
print(f"   Total time for 48 combos: {total_time_hours:.1f} hours")

if time_per_combo_min > 30:
    print("\n⚠️  WARNING: Training is SLOW!")
    print("   Expected: ~15 min per combo with GPU")
    print("   Actual projection: ~{:.1f} min per combo".format(time_per_combo_min))
    print("\n💡 Possible issues:")
    print("   1. MPS not actually being used (data transfer bottleneck)")
    print("   2. LSTM too large for M2 GPU (memory thrashing)")
    print("   3. Batch size too small (not utilizing GPU parallelism)")
    print("   4. Episode count too high (2000 is a lot)")
else:
    print("\n✅ Training speed looks good!")

print("=" * 60)
