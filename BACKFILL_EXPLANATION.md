# 🔄 Backfill Implementation Guide

## ✅ What is Backfilling?

**Backfilling** = Copying the last N historical messages from a source channel to a target channel when you first set up the bot or add a new channel pair.

For example, if you set `backfill_count: 10`, the bot will copy the **last 10 messages** from the source channel to the target channel before it starts forwarding new messages.

---

## 📦 How It Works

### 1️⃣ **First Time Bot Starts**

When you start the bot for the first time (or after adding a new pair):

```json
{
  "source": -1001234567890,
  "target": -1009876543210,
  "enabled": true,
  "backfill_count": 10
}
```

**What happens:**
1. ✅ Bot checks `backfill_tracking.json` - this pair is NOT in the file
2. ✅ Bot says: "This pair needs backfill!"
3. ✅ Bot copies the **last 10 messages** from source → target
4. ✅ Bot marks this pair as backfilled in `backfill_tracking.json`
5. ✅ Bot starts polling for **new** messages

**Log output:**
```
📦 Checking if backfill is needed for channel pairs...
📋 Pair: -1001234567890 -> -1009876543210, backfill_count: 10
🔄 BACKFILLING 10 messages: -1001234567890 -> -1009876543210
Backfilling last 10 messages from -1001234567890 to -1009876543210
✅ Backfill complete for -1001234567890 -> -1009876543210
```

---

### 2️⃣ **Bot Restarts (Same Pairs)**

When you restart the bot with the **same channel pairs**:

**What happens:**
1. ✅ Bot checks `backfill_tracking.json` - this pair IS in the file
2. ✅ Bot says: "This pair was already backfilled, skip!"
3. ✅ Bot starts polling for **new** messages immediately
4. ❌ **Does NOT copy historical messages again**

**Log output:**
```
📦 Checking if backfill is needed for channel pairs...
📋 Pair: -1001234567890 -> -1009876543210, backfill_count: 10
⏭️  SKIPPING - Pair already backfilled: -1001234567890 -> -1009876543210
```

---

### 3️⃣ **Adding New Pair via Admin Bot**

When you add a new pair using the Telegram admin bot:

**What happens:**
1. ✅ You send: `/add_pair` and provide source, target, backfill count
2. ✅ Admin bot saves the pair to `config.json`
3. ✅ Admin bot **removes** this pair from `backfill_tracking.json` (if it exists)
4. ✅ Admin bot creates `trigger_reload.flag` file
5. ✅ Running bot detects the trigger file within 5 seconds
6. ✅ Bot reloads config and sees the new pair
7. ✅ Bot checks `backfill_tracking.json` - pair NOT there
8. ✅ Bot backfills the new pair immediately

**This means: New pairs are backfilled automatically, even while the bot is running!**

---

## 📂 Files Used

### `backfill_tracking.json`
Tracks which pairs have been backfilled (to avoid duplicates).

**Format:**
```json
{
  "-1001234567890:-1009876543210": 1700000000.0,
  "-1009876543211:-1001234567892": 1700000100.0
}
```

- **Key:** `"source_id:target_id"`
- **Value:** Unix timestamp when backfilled

### `last_processed.json`
Tracks the last message ID forwarded for each source channel (for polling).

**Format:**
```json
{
  "-1001234567890": 12345,
  "-1009876543211": 67890
}
```

### `trigger_reload.flag`
Empty file created by admin bot to signal the running bot to reload config.

---

## 🔧 Configuration

Set `backfill_count` in your `config.json`:

```json
{
  "workers": [
    {
      "worker_id": "worker_1",
      "channel_pairs": [
        {
          "source": -1001234567890,
          "target": -1009876543210,
          "enabled": true,
          "backfill_count": 10  ← Set this!
        }
      ]
    }
  ]
}
```

**Options:**
- `backfill_count: 0` → No backfill, only forward new messages
- `backfill_count: 10` → Copy last 10 messages on first run
- `backfill_count: 100` → Copy last 100 messages on first run

---

## 🎯 Use Cases

### Use Case 1: Testing New Source Channel
```json
{
  "source": -1001111111111,
  "target": -1002222222222,
  "backfill_count": 5  ← Test with just 5 messages
}
```

Start bot → Check target channel → See last 5 messages copied → Verify formatting looks good.

---

### Use Case 2: Starting Fresh Channel
```json
{
  "source": -1003333333333,
  "target": -1004444444444,
  "backfill_count": 100  ← Fill channel with last 100 messages
}
```

Start bot → Target channel gets populated with last 100 posts → New messages start forwarding automatically.

---

### Use Case 3: No Historical Messages
```json
{
  "source": -1005555555555,
  "target": -1006666666666,
  "backfill_count": 0  ← No backfill, fresh start
}
```

Start bot → Target channel stays empty → Only **new** messages after bot start are forwarded.

---

## 🛠️ Troubleshooting

### Problem: Bot backfills every time it restarts

**Cause:** `backfill_tracking.json` is being deleted or not saved.

**Solution:**
1. Check if the file exists: `ls backfill_tracking.json`
2. Check file permissions: `ls -l backfill_tracking.json`
3. Check bot logs for "Failed to save backfill tracking" errors

---

### Problem: New pair not backfilling

**Cause:** Pair key already exists in `backfill_tracking.json`.

**Solution:**
1. Stop the bot
2. Open `backfill_tracking.json`
3. Remove the pair key: `"source:target"`
4. Start the bot → Backfill will run

---

### Problem: Want to re-backfill an existing pair

**Scenario:** You changed replacement rules and want to re-copy messages with new rules.

**Solution:**
```bash
# Stop the bot
./stop.sh

# Remove the pair from tracking
# Edit backfill_tracking.json and delete the line with your pair

# Or clear all backfill tracking:
rm backfill_tracking.json

# Start the bot
./start.sh
```

---

## 📊 Behavior Summary

| Scenario | Backfill? | Why? |
|----------|-----------|------|
| First bot start | ✅ YES | Pair not in `backfill_tracking.json` |
| Bot restart (same pairs) | ❌ NO | Pair already in `backfill_tracking.json` |
| Add new pair (bot running) | ✅ YES | Admin bot removes pair from tracking |
| `backfill_count: 0` | ❌ NO | Explicitly disabled |
| Deleted `backfill_tracking.json` | ✅ YES | All pairs treated as new |

---

## 🚀 Best Practices

### ✅ DO:
- Use `backfill_count: 10` for testing (small, fast)
- Use `backfill_count: 100` for production (populate channel)
- Keep `backfill_tracking.json` in `.gitignore` (it's instance-specific)
- Monitor logs for backfill progress
- Test with one pair before adding many

### ❌ DON'T:
- Don't set `backfill_count` too high (>200) - might hit rate limits
- Don't delete `backfill_tracking.json` unless intentional
- Don't manually edit `backfill_tracking.json` while bot is running
- Don't expect backfill to happen twice for same pair (by design)

---

## 🔍 Monitoring Backfill

### Check if backfill is needed:
```bash
cat backfill_tracking.json
```

If your pair `"source:target"` is NOT in this file → Backfill will run on next start.

### Watch backfill in real-time:
```bash
tail -f logs/forwarder.log | grep -i backfill
```

Output:
```
[INFO] 📦 Checking if backfill is needed...
[INFO] 🔄 BACKFILLING 10 messages: -1001234567890 -> -1009876543210
[INFO] Backfilling last 10 messages from -1001234567890 to -1009876543210
[INFO] ✅ Backfill complete for -1001234567890 -> -1009876543210
```

---

## ✅ Verification

After backfill runs, verify:

1. **Check target channel:**
   - Open target channel in Telegram
   - Should see the last N messages from source

2. **Check tracking file:**
   ```bash
   cat backfill_tracking.json
   ```
   Should see your pair: `"-1001234567890:-1009876543210": 1700000000.0`

3. **Check logs:**
   ```bash
   grep "Backfill completed" logs/forwarder.log
   ```

4. **Restart bot:**
   - Should see "⏭️ SKIPPING - Pair already backfilled"
   - Confirms backfill won't run again

---

## 🎓 Summary

- ✅ **Automatic:** Backfill runs on first start for each pair
- ✅ **Once only:** Won't re-backfill on restart (unless you delete tracking)
- ✅ **New pairs:** Admin bot marks new pairs for backfill automatically
- ✅ **Configurable:** Set `backfill_count` per pair (0 to disable)
- ✅ **Smart:** Respects media groups, filters, and replacement rules during backfill
- ✅ **Tracked:** Uses `backfill_tracking.json` to remember what's done

**Result:** Clean, populated target channels with historical context + automatic forwarding of new messages! 🎉

