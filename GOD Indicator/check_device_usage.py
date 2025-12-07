#!/usr/bin/env python3
"""Check if training is using CPU or M2 GPU (MPS)"""

import torch
import psutil
import time
import sys

print("🔍 Device Usage Checker")
print("=" * 60)

# Check PyTorch device
print("\n📱 PyTorch Configuration:")
print(f"   PyTorch Version: {torch.__version__}")
print(f"   MPS Available: {torch.backends.mps.is_available()}")
print(f"   MPS Built: {torch.backends.mps.is_built()}")

# Check what device is being used
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"   Default Device: {device}")

# Create test tensor to verify
test_tensor = torch.randn(100, 100).to(device)
print(f"   Test Tensor Device: {test_tensor.device}")

# Check training process
print("\n🔬 Training Process Status:")
try:
    # Find training process
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'train_intelligent_brain.py' in cmdline:
                pid = proc.info['pid']
                print(f"   PID: {pid}")
                
                # Get process details
                p = psutil.Process(pid)
                
                # CPU usage
                cpu_percent = p.cpu_percent(interval=1.0)
                print(f"   CPU Usage: {cpu_percent}%")
                
                # Memory
                mem = p.memory_info()
                print(f"   Memory: {mem.rss / 1024 / 1024:.1f} MB")
                
                # Thread count
                print(f"   Threads: {p.num_threads()}")
                
                # Analyze CPU usage
                print("\n💡 Analysis:")
                if cpu_percent < 150:
                    print("   ⚠️  LOW CPU usage - possibly GPU-bound (GOOD!)")
                    print("   ✅ Likely using M2 GPU acceleration")
                else:
                    print("   ⚠️  HIGH CPU usage - possibly CPU-bound")
                    print("   ❌ May not be using GPU effectively")
                
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    else:
        print("   ❌ Training process not found")
        print("   Start with: nohup python3 train_intelligent_brain.py > training_m2_full.log 2>&1 &")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check log for MPS messages
print("\n📋 Log Analysis:")
try:
    with open('training_m2_full.log', 'r') as f:
        log_content = f.read()
        
        if 'Using M2 GPU' in log_content or 'mps' in log_content.lower():
            print("   ✅ Log shows M2 GPU activation")
        else:
            print("   ⚠️  No M2 GPU messages in log")
        
        if 'device(type=\'mps\')' in log_content:
            print("   ✅ MPS device confirmed in log")
            
        # Count combinations tested
        combo_count = log_content.count('Testing: LR=')
        print(f"   📊 Hyperparameter combos tested: {combo_count}")
        
except FileNotFoundError:
    print("   ❌ training_m2_full.log not found")

print("\n" + "=" * 60)
print("🎯 Quick Check: Low CPU + 'M2 GPU' in log = GPU is working!")
print("=" * 60)
