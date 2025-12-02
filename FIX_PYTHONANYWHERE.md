# Quick Fix for PythonAnywhere

## Problem
Your admin bot was adding replacement rules to the **wrong location** in config.json. The 3 rules you added went to a top-level `replacement_rules` array instead of your worker's `replacement_rules` array, so they're being **ignored**.

## Solution (5 minutes)

### Step 1: Update Code on PythonAnywhere

```bash
# Open PythonAnywhere Bash console
cd ~/telegram-addresser
git pull origin main
```

### Step 2: Fix Your Config

```bash
# Run the cleanup script
python3 fix_config_rules.py config.json
```

The script will:
- ✅ Show you the 3 rules that are in the wrong place
- ✅ Ask for confirmation
- ✅ Move them to worker's replacement_rules
- ✅ Create a backup (config.json.backup)
- ✅ Save the fixed config

### Step 3: Reload Bot

Option A - Wait for auto-reload (2 minutes):
```bash
# Config auto-reload will detect the change
# Just wait 2 minutes
```

Option B - Force immediate reload:
```bash
# Create trigger file for instant reload
cd ~/telegram-addresser
touch trigger_reload.flag
```

Option C - Restart bot:
```bash
# Stop and start from PythonAnywhere Web tab
# Or use systemctl if using systemd
```

## Verify Fix

### Check config structure:
```bash
# The 3 rules should now be inside worker's array
cat config.json | grep -A 20 '"replacement_rules"'
```

### Test with admin bot:
1. Send `/status` - should show all rules
2. Add a test rule - should go to correct location
3. Check a forwarded message - replacements should work

## What Changed

**Before (broken):**
```json
{
  "workers": [{
    "replacement_rules": [...]  // Old rules
  }],
  "replacement_rules": [...]  // ❌ These 3 new rules (ignored!)
}
```

**After (fixed):**
```json
{
  "workers": [{
    "replacement_rules": [...]  // All rules including the 3 new ones ✅
  }]
  // No top-level replacement_rules
}
```

## Future

From now on, when you add rules via admin bot:
- ✅ They'll go to the correct location automatically
- ✅ They'll be applied to messages
- ✅ No manual fixes needed

---

**Quick Commands:**
```bash
# Update code
cd ~/telegram-addresser && git pull origin main

# Fix config
python3 fix_config_rules.py config.json

# Force reload
touch trigger_reload.flag

# Check it worked
tail -50 logs/worker_*.log
```

Done! 🎉
