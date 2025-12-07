#!/usr/bin/env python3
"""Check M2 GPU availability"""

import torch

print("🔍 M2 GPU Check:")
print(f"MPS Available: {torch.backends.mps.is_available()}")
print(f"MPS Built: {torch.backends.mps.is_built()}")
print(f"PyTorch Version: {torch.__version__}")

if torch.backends.mps.is_available():
    print("\n✅ M2 GPU acceleration is available!")
    print("Training will be 5-10x faster")
else:
    print("\n⚠️ MPS not available - will use CPU")
