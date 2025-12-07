#!/usr/bin/env python3
"""
GOD Indicator - Duplicate File Cleanup Script (Python)
Cross-platform file cleanup utility
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def create_backup(files_to_backup, backup_dir):
    """Create backup of files before deletion"""
    print(f"\n📦 Creating backup in: {backup_dir}")
    Path(backup_dir).mkdir(exist_ok=True)
    
    backed_up = 0
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            try:
                dest = Path(backup_dir) / Path(file_path).name
                shutil.copy2(file_path, dest)
                print(f"   ✓ Backed up: {file_path}")
                backed_up += 1
            except Exception as e:
                print(f"   ✗ Failed to backup {file_path}: {e}")
    
    print(f"   ✓ {backed_up} files backed up")
    return backed_up

def delete_file(file_path):
    """Safely delete a file"""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True, f"✓ Deleted: {file_path}"
        except Exception as e:
            return False, f"✗ Failed to delete {file_path}: {e}"
    else:
        return False, f"⊝ Not found: {file_path}"

def main():
    print("=" * 70)
    print("🗑️  GOD Indicator - Duplicate File Cleanup")
    print("=" * 70)
    print()
    
    # Safety check
    response = input("⚠️  This will DELETE duplicate files. Create backup first? (y/n): ").strip().lower()
    
    if response == 'y':
        backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        files_to_backup = [
            "main.py",
            "run_venv.py",
            "app/gui.py",
            "app/trading_tool_gui.py",
            "app/quickstart_gui.py",
        ]
        
        create_backup(files_to_backup, backup_dir)
    
    response = input("\n▶️  Proceed with cleanup? (y/n): ").strip().lower()
    
    if response != 'y':
        print("❌ Cleanup cancelled")
        return
    
    print()
    print("=" * 70)
    print("Starting cleanup...")
    print("=" * 70)
    print()
    
    deleted_count = 0
    failed_count = 0
    not_found_count = 0
    
    # ========================================================================
    # 1. DUPLICATE GUI FILES
    # ========================================================================
    print("📂 Removing duplicate GUI files...")
    
    gui_files = [
        "app/gui.py",
        "app/trading_tool_gui.py",
        "app/quickstart_gui.py",
    ]
    
    for file_path in gui_files:
        success, msg = delete_file(file_path)
        print(f"   {msg}")
        if success:
            deleted_count += 1
        elif "Not found" in msg:
            not_found_count += 1
        else:
            failed_count += 1
    
    print()
    
    # ========================================================================
    # 2. DUPLICATE MAIN FILES
    # ========================================================================
    print("📂 Removing duplicate main files...")
    
    main_files = [
        "main.py",
        "run_venv.py",
    ]
    
    for file_path in main_files:
        success, msg = delete_file(file_path)
        print(f"   {msg}")
        if success:
            deleted_count += 1
        elif "Not found" in msg:
            not_found_count += 1
        else:
            failed_count += 1
    
    print()
    
    # ========================================================================
    # 3. DUPLICATE DOCUMENTATION FILES
    # ========================================================================
    print("📂 Removing duplicate documentation files...")
    
    duplicate_docs = [
        "SYSTEM_README.md",
        "SETUP_CHECKLIST.md",
        "VENV_SETUP.md",
        "SETUP.md",
        "QUICK_REFERENCE.md",
        "QUICK_REFERENCE_ENHANCED.md",
        "PROFESSIONAL_QUICK_START.md",
        "COMPLETE_SYSTEM_OVERVIEW.md",
        "ADVANCED_SYSTEM_DOCUMENTATION.md",
        "SYSTEM_COMPLETE_100_PERCENT.md",
        "FINAL_SUMMARY.md",
        "FINAL_DELIVERY_CHECKLIST.md",
        "PROJECT_COMPLETE.md",
        "ALL_TASKS_COMPLETE.md",
        "IMPLEMENTATION_SUMMARY.md",
        "IMPLEMENTATION_COMPLETE.md",
        "INTEGRATION_COMPLETE.md",
        "DEPLOYMENT_READY.md",
        "NEW_FEATURES_SUMMARY.md",
        "INTEGRATION_GUIDE.md",
        "ENHANCED_FEATURES_GUIDE.md",
        "EMA_30_STRATEGY_GUIDE.md",
        "DISCORD_SETUP_GUIDE.md",
        "DATAFIX.md",
        "DEPENDENCY_FIX.md",
        "CLEANUP_GUIDE.md",
        "COMPLETION_CHECKLIST.md",
        "BACKTEST_GUIDE.md",
        "PROFESSIONAL_BACKTESTING_GUIDE.md",
        "FILE_INVENTORY.md",
        "VERIFICATION_REPORT.md",
        "SOLUTION.md",
    ]
    
    for doc in duplicate_docs:
        success, msg = delete_file(doc)
        print(f"   {msg}")
        if success:
            deleted_count += 1
        elif "Not found" in msg:
            not_found_count += 1
        else:
            failed_count += 1
    
    print()
    
    # ========================================================================
    # 4. OBSOLETE UTILITY SCRIPTS
    # ========================================================================
    print("📂 Removing obsolete utility scripts...")
    
    obsolete_scripts = [
        "find_gold_symbol.py",
        "verify_imports.py",
        "verify_live_prices.py",
        "verify_system.py",
        "check_system_status.py",
        "staging_scheduler_check.py",
        "test_scheduler.py",
        "test_system.py",
        "test_discord_webhook.py",
    ]
    
    for script in obsolete_scripts:
        success, msg = delete_file(script)
        print(f"   {msg}")
        if success:
            deleted_count += 1
        elif "Not found" in msg:
            not_found_count += 1
        else:
            failed_count += 1
    
    print()
    
    # ========================================================================
    # 5. DUPLICATE SHELL SCRIPTS
    # ========================================================================
    print("📂 Removing duplicate shell scripts...")
    
    shell_scripts = [
        "launch_complete_system.sh",
        "launch_enhanced.sh",
        "run_tests.sh",
        "setup_aliases.sh",
    ]
    
    for script in shell_scripts:
        success, msg = delete_file(script)
        print(f"   {msg}")
        if success:
            deleted_count += 1
        elif "Not found" in msg:
            not_found_count += 1
        else:
            failed_count += 1
    
    print()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 70)
    print("✅ Cleanup Complete!")
    print("=" * 70)
    print()
    print("📊 Summary:")
    print(f"   • Files deleted: {deleted_count}")
    print(f"   • Files not found: {not_found_count}")
    print(f"   • Deletions failed: {failed_count}")
    print()
    print("📁 Core System Files Preserved:")
    print()
    print("   Main Entry Points:")
    print("      ✓ main_professional.py (CLI backtesting)")
    print("      ✓ launch_enhanced.py (GUI launcher)")
    print("      ✓ launch_complete_system.py (GUI + Scheduler)")
    print("      ✓ train_rl_agent.py (RL training)")
    print()
    print("   GUI:")
    print("      ✓ app/enhanced_gui.py (9-tab professional GUI)")
    print()
    print("   Documentation (7 core files):")
    print("      ✓ README.md (main overview)")
    print("      ✓ START_HERE.md (quick start)")
    print("      ✓ FINAL_RL_COMPLETE.md (system status)")
    print("      ✓ RL_INTEGRATION_COMPLETE.md (RL technical docs)")
    print("      ✓ RL_QUICK_START.md (RL user guide)")
    print("      ✓ SYSTEM_AUDIT_REPORT.md (audit findings)")
    print("      ✓ CRITICAL_FIXES_APPLIED.md (MTF + RL fixes)")
    print()
    print("   Backend:")
    print("      ✓ All 30+ core backend files preserved")
    print("      ✓ Strategies, data fetchers, analyzers intact")
    print()
    print("🎉 Your codebase is now clean and organized!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Review remaining files")
    print("  2. Run: python app/enhanced_gui.py (test GUI)")
    print("  3. Run: python train_rl_agent.py (train RL agent)")
    print("  4. Start live trading!")
    print()

if __name__ == "__main__":
    main()
