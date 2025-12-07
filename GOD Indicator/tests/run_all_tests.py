#!/usr/bin/env python3
"""
Test Runner - Run all tests with coverage reporting
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run all test suites"""
    
    print("\n" + "="*70)
    print(" "*20 + "GOD INDICATOR TEST SUITE")
    print("="*70 + "\n")
    
    test_dir = Path(__file__).parent
    
    # Test files
    tests = [
        'test_unified_data_fetcher.py',
        'test_strategies.py',
        'test_integration.py'
    ]
    
    passed = 0
    failed = 0
    
    for test_file in tests:
        test_path = test_dir / test_file
        
        if not test_path.exists():
            print(f"⚠️  Test file not found: {test_file}")
            continue
        
        print(f"\n{'='*70}")
        print(f"Running: {test_file}")
        print('='*70)
        
        try:
            result = subprocess.run(
                [sys.executable, str(test_path)],
                cwd=test_dir.parent,
                capture_output=False
            )
            
            if result.returncode == 0:
                passed += 1
                print(f"\n✅ {test_file}: PASSED")
            else:
                failed += 1
                print(f"\n❌ {test_file}: FAILED")
        
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_file}: ERROR - {e}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total test files: {passed + failed}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("="*70 + "\n")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("="*70 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
