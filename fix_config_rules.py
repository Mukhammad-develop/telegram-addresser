#!/usr/bin/env python3
"""
Fix config.json - Move top-level replacement_rules to worker's replacement_rules.

This script fixes the issue where the admin bot incorrectly added rules to the 
top-level replacement_rules array instead of to the worker's replacement_rules.
"""

import json
import sys
from pathlib import Path


def fix_config(config_path: str = "config.json"):
    """Move top-level replacement_rules to worker's replacement_rules."""
    
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Check if it's multi-worker mode
    if "workers" not in config:
        print("✅ Not a multi-worker config, nothing to fix")
        return
    
    # Check if there are top-level replacement_rules
    top_level_rules = config.get("replacement_rules", [])
    if not top_level_rules:
        print("✅ No top-level replacement_rules found, nothing to fix")
        return
    
    print(f"🔍 Found {len(top_level_rules)} rule(s) at top-level (incorrect location)")
    
    # Display the rules
    for i, rule in enumerate(top_level_rules, 1):
        print(f"  {i}. {rule['find']} → {rule['replace']}")
    
    # Ask for confirmation
    response = input("\n❓ Move these rules to worker's replacement_rules? (y/n): ")
    if response.lower() != 'y':
        print("❌ Aborted")
        return
    
    # Move rules to each enabled worker
    workers = config.get("workers", [])
    for worker in workers:
        if worker.get("enabled", True):
            worker_id = worker.get("worker_id", "unknown")
            print(f"\n📝 Adding rules to worker: {worker_id}")
            
            # Get existing rules
            existing_rules = worker.get("replacement_rules", [])
            
            # Add top-level rules if not already present
            added_count = 0
            for rule in top_level_rules:
                # Check if rule already exists (by find+replace text)
                exists = any(
                    r.get("find") == rule.get("find") and 
                    r.get("replace") == rule.get("replace")
                    for r in existing_rules
                )
                if not exists:
                    existing_rules.append(rule)
                    added_count += 1
                    print(f"  ✅ Added: {rule['find']}")
                else:
                    print(f"  ⏭️  Skipped (already exists): {rule['find']}")
            
            worker["replacement_rules"] = existing_rules
            print(f"  📊 Total rules in {worker_id}: {len(existing_rules)}")
    
    # Remove top-level replacement_rules
    if "replacement_rules" in config:
        del config["replacement_rules"]
        print(f"\n🗑️  Removed top-level replacement_rules array")
    
    # Create backup
    backup_path = f"{config_path}.backup"
    with open(backup_path, 'w') as f:
        json.dump(json.load(open(config_path)), f, indent=2)
    print(f"\n💾 Backup created: {backup_path}")
    
    # Save fixed config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Config fixed and saved!")
    print(f"\n📋 Summary:")
    print(f"   - Moved {len(top_level_rules)} rule(s) from top-level to workers")
    print(f"   - Updated {len([w for w in workers if w.get('enabled', True)])} worker(s)")
    print(f"   - Backup saved to {backup_path}")
    print(f"\n🎉 Done! The bot will now use the correct rules.")


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    
    if not Path(config_file).exists():
        print(f"❌ Error: {config_file} not found")
        sys.exit(1)
    
    try:
        fix_config(config_file)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
