# Multi-Worker Config Fix - Replacement Rules

## Issue

When using the admin bot to add replacement rules in **multi-worker mode**, the rules were being added to the wrong location in `config.json`.

### Incorrect Structure (Before Fix)

```json
{
  "workers": [
    {
      "worker_id": "5",
      "replacement_rules": [...]  // Worker's rules
    }
  ],
  "replacement_rules": [...]  // ❌ WRONG! Top-level rules (ignored)
}
```

### Correct Structure (After Fix)

```json
{
  "workers": [
    {
      "worker_id": "5",
      "replacement_rules": [...]  // ✅ All rules go here
    }
  ]
  // No top-level replacement_rules in multi-worker mode
}
```

## What Was Fixed

### 1. ConfigManager (`src/config_manager.py`)

Updated to properly detect and handle multi-worker mode:

- **`is_multi_worker_mode()`** - Detects if config uses workers array
- **`get_replacement_rules()`** - Aggregates rules from all workers
- **`add_replacement_rule()`** - Adds rules to workers, not top-level
- **`remove_replacement_rule()`** - Removes from correct worker
- **`update_replacement_rule()`** - Updates in correct worker

Also updated channel pair methods to handle multi-worker mode.

### 2. Cleanup Script (`fix_config_rules.py`)

Created script to fix existing broken configs:

```bash
# Run on PythonAnywhere or local machine
python3 fix_config_rules.py config.json
```

This script:
- ✅ Finds top-level replacement_rules
- ✅ Moves them to worker's replacement_rules
- ✅ Avoids duplicates
- ✅ Creates backup before modifying
- ✅ Works with any multi-worker config

## How to Fix Your Config

### Option 1: Use the Cleanup Script (Recommended)

```bash
cd /home/yourusername/telegram-addresser
python3 fix_config_rules.py config.json
```

The script will:
1. Show you what rules are in the wrong place
2. Ask for confirmation
3. Move rules to correct location
4. Create backup
5. Save fixed config

### Option 2: Manual Fix

1. **Open config.json**
2. **Find top-level `replacement_rules`** array (at root level, same level as `workers`)
3. **Copy those rules**
4. **Paste them into your worker's `replacement_rules`** array
5. **Delete the top-level `replacement_rules`** array
6. **Save the file**

## How to Verify Fix

After fixing, your config should look like this:

```json
{
  "admin_bot_token": "...",
  "admin_user_ids": [...],
  "workers": [
    {
      "worker_id": "5",
      "replacement_rules": [
        // All rules go here, including the ones that were at top-level
        {"find": "@HelpDeskMCP", "replace": "@Trademaster666", ...},
        {"find": "...", "replace": "...", ...}
      ]
    }
  ]
  // No "replacement_rules" at this level!
}
```

## Future Additions

From now on, when you add rules via admin bot:
- ✅ Rules will be added to worker's replacement_rules
- ✅ Rules will be properly applied to forwarded messages
- ✅ No more top-level rules that get ignored

## For PythonAnywhere Users

### Fix Remote Config

```bash
# SSH or use PythonAnywhere console
cd ~/telegram-addresser
python3 fix_config_rules.py config.json

# Reload config (bot detects changes automatically)
# Or manually trigger reload:
touch trigger_reload.flag
```

### Update Code

```bash
cd ~/telegram-addresser
git pull origin main

# Restart bot (or wait for auto-restart)
# Check it's using new code:
cat src/config_manager.py | grep "is_multi_worker_mode"
```

## Testing

After fixing:

1. **Check existing rules work:**
   ```bash
   # In admin bot, send /status
   # Verify rule count is correct
   ```

2. **Add a new test rule:**
   ```bash
   # Use admin bot to add a rule
   # Check config.json - should be in worker's array
   ```

3. **Verify forwarding applies rules:**
   - Send a test message to source channel
   - Check target channel - replacements should be applied

## Troubleshooting

### Rules still not working after fix?

1. **Restart the bot** (config should auto-reload, but restart ensures it)
2. **Check logs** for any errors
3. **Verify JSON syntax** is valid: `python3 -m json.tool config.json`

### Script fails with error?

- Check you have permissions to write config.json
- Check JSON is valid before running script
- Check Python 3 is installed: `python3 --version`

### Rules duplicated?

The script checks for duplicates and skips them. If you see duplicates:
1. Manually edit config.json
2. Remove duplicate rules
3. Keep only one copy in worker's replacement_rules

---

**Updated:** December 2025  
**Affects:** Multi-worker mode configs only  
**Severity:** High - Rules in wrong location don't work  
**Status:** Fixed ✅
