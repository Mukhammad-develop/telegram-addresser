# 📦 Full Copy Mode - Complete Channel Backup

## Overview

**Full Copy Mode** copies **ALL messages** from a channel starting from message ID 1 to the latest message, then continues with normal live forwarding.

---

## 🎯 When to Use

### Use Full Copy Mode When:
- ✅ Starting a brand new target channel (want complete history)
- ✅ Creating a backup/mirror of an entire channel
- ✅ Migrating content from one channel to another
- ✅ Building an archive with all historical posts

### Use Normal Backfill When:
- ⏭️ Only need recent context (last 10-100 messages)
- ⏭️ Channel has thousands of old messages you don't need
- ⏭️ Want faster setup (full copy can take hours for large channels)

---

## ⚙️ Configuration

In your `config.json`, set `backfill_count` to **0** for full copy:

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
          "backfill_count": 0    ← Set to 0 for FULL COPY
        }
      ]
    }
  ]
}
```

### Configuration Options:

| `backfill_count` | Behavior |
|------------------|----------|
| `0` | **Full Copy** - Copies ALL messages from beginning |
| `10` | Copies last 10 messages only |
| `100` | Copies last 100 messages only |
| `-1` or negative | No backfill, only live messages |

---

## 📊 How It Works

### Full Copy Process:

```
1. Bot starts
2. Detects backfill_count = 0
3. Enters FULL COPY MODE
4. Fetches messages in batches of 100
5. Starts from message ID 1 (oldest)
6. Copies in chronological order
7. Continues until no more messages
8. Marks pair as backfilled
9. Switches to normal polling mode (live forwarding)
```

### Example Flow:

```
Channel has 5,000 messages total

00:00 - Full copy starts
00:00 - Batch 1: Messages 1-100 (copied)
00:02 - Batch 2: Messages 101-200 (copied)
00:04 - Batch 3: Messages 201-300 (copied)
...
02:30 - Batch 50: Messages 4901-5000 (copied)
02:30 - ✅ Full copy complete! (5000 messages)
02:30 - Switching to live mode
02:30 - Now checking for new messages every 5 seconds
```

---

## ⏱️ Time Estimates

### Depends on:
- Number of messages in channel
- Network speed
- Telegram rate limits
- Message types (text vs media)

### Rough Estimates:

| Channel Size | Estimated Time |
|--------------|----------------|
| 100 messages | ~2 minutes |
| 1,000 messages | ~20 minutes |
| 5,000 messages | ~2 hours |
| 10,000 messages | ~4-5 hours |
| 50,000 messages | ~24 hours |

**Note:** Media-heavy channels (lots of photos/videos) take longer due to download/upload time.

---

## 📝 Log Output

### Full Copy Mode Logs:

```
[INFO] 🔄 FULL COPY MODE: Starting complete channel copy from -1001234567890 to -1009876543210
[INFO] This will copy ALL messages from the beginning. This may take a while...
[INFO] 📦 Processing batch: 100 messages (IDs 1 to 100)
[INFO] 📊 Progress: 50 messages copied, 3 skipped
[INFO] 📦 Processing batch: 100 messages (IDs 101 to 200)
[INFO] 📊 Progress: 100 messages copied, 7 skipped
[INFO] 📦 Processing batch: 100 messages (IDs 201 to 300)
[INFO] 📊 Progress: 150 messages copied, 10 skipped
...
[INFO] 📭 No more messages to copy
[INFO] ✅ FULL COPY COMPLETED: 4,823 messages copied, 177 skipped from -1001234567890 -> -1009876543210
```

### Normal Backfill Logs (for comparison):

```
[INFO] Backfilling last 10 messages from -1001234567890 to -1009876543210
[INFO] Backfill completed for -1001234567890 -> -1009876543210
```

---

## 🚀 Setup Instructions

### Step 1: Prepare Config

Edit `config.json`:

```json
{
  "channel_pairs": [
    {
      "source": -1001234567890,
      "target": -1009876543210,
      "enabled": true,
      "backfill_count": 0    ← Change this to 0
    }
  ]
}
```

### Step 2: Start Bot

```bash
# Make sure backfill tracking is clear (or bot will skip)
rm -f backfill_tracking.json

# Start the bot
python3 worker_manager.py

# Or via admin bot:
./start.sh
```

### Step 3: Monitor Progress

**Watch logs in real-time:**

```bash
tail -f logs/forwarder.log
```

**Look for:**
- `🔄 FULL COPY MODE` - Copy started
- `📦 Processing batch` - Current batch being copied
- `📊 Progress: X messages copied` - Running total
- `✅ FULL COPY COMPLETED` - All done!

### Step 4: Verify

After full copy completes:

1. **Check target channel** - Should have all historical messages
2. **Send test message** in source - Should appear in target within 5-10 seconds
3. **Check logs** - Should show normal polling mode

---

## ⚠️ Important Notes

### 1. **One-Time Operation**

Full copy runs **once per pair**. After completion:
- Pair is marked as backfilled in `backfill_tracking.json`
- Subsequent restarts will skip the full copy
- Only new live messages are forwarded

**To run full copy again:**
```bash
# Stop bot
# Delete tracking
rm -f backfill_tracking.json
# Restart bot
```

### 2. **Rate Limits**

Telegram has rate limits. The bot includes:
- 1-second delay between batches
- Automatic retry on FloodWaitError
- Exponential backoff on errors

**If you hit rate limits:**
- Bot will wait automatically
- Check logs for "FloodWaitError"
- Bot continues after waiting

### 3. **Interrupted Copy**

If bot crashes during full copy:
- Restart the bot
- It will continue from where it stopped
- No messages are duplicated (thanks to message ID tracking)

### 4. **Disk Space**

Full copy downloads media temporarily:
- Photos, videos stored in `temp_media/`
- Deleted after forwarding
- Ensure enough disk space (especially for media-heavy channels)

### 5. **Bot Must Be Admin**

- Source: Bot account must be member
- Target: Bot must be admin with send permissions

---

## 🔍 Troubleshooting

### Problem: Full Copy Not Starting

**Check config:**
```bash
grep -A 5 "backfill_count" config.json
```

**Should see:**
```json
"backfill_count": 0
```

**If not 0:** Change to 0 and restart bot

### Problem: Bot Says "Pair already backfilled"

**Cause:** `backfill_tracking.json` has this pair

**Fix:**
```bash
# Stop bot
# Remove tracking
rm -f backfill_tracking.json
# Restart bot
```

### Problem: Full Copy Stops Midway

**Check logs:**
```bash
tail -50 logs/forwarder.log
```

**Common causes:**
- FloodWaitError (bot waits automatically)
- Permission error (check bot is admin)
- Network issue (bot retries automatically)

**Solution:** Usually just restart the bot

### Problem: Taking Too Long

**Speed it up:**

1. **Reduce filters** - Fewer filters = faster processing
2. **Disable replacement rules temporarily** - Faster text processing
3. **Check network** - Slow internet = slow copy

**Or switch to normal backfill:**
```json
"backfill_count": 100  // Copy last 100 instead of all
```

### Problem: Duplicate Messages

**This shouldn't happen** - bot tracks processed messages

**If it does:**
- Check if you ran full copy twice
- Check if you manually forwarded messages
- Delete duplicates manually in target channel

---

## 📊 Performance Tips

### Optimize Full Copy:

1. **Run during off-peak hours**
   - Less Telegram traffic = fewer rate limits
   - Night time usually faster

2. **Ensure stable internet**
   - Wired connection better than WiFi
   - VPS/Cloud hosting faster than home connection

3. **Monitor CPU/Memory**
   - Full copy uses more resources
   - Close other applications
   - Check PythonAnywhere CPU limits

4. **Disable non-essential features during copy**
   - Keep filters minimal
   - Simplify replacement rules
   - Enable after copy completes

---

## 🎯 Use Case Examples

### Example 1: Complete Channel Backup

**Scenario:** Want exact copy of source channel

```json
{
  "source": -1001234567890,
  "target": -1009876543210,
  "backfill_count": 0,
  "replacement_rules": [],  // No modifications
  "filters": {"enabled": false}  // No filtering
}
```

**Result:** Perfect 1:1 copy of entire channel

### Example 2: Curated Archive

**Scenario:** Copy all but filter out certain content

```json
{
  "source": -1001234567890,
  "target": -1009876543210,
  "backfill_count": 0,
  "replacement_rules": [...],  // Apply branding
  "filters": {
    "enabled": true,
    "mode": "blacklist",
    "keywords": ["spam", "promo"]  // Skip these
  }
}
```

**Result:** Full history with filtering applied

### Example 3: Combine with Live Forwarding

**Scenario:** Get all history + continue live

```json
{
  "source": -1001234567890,
  "target": -1009876543210,
  "backfill_count": 0  // Full copy first
}
```

**Process:**
1. Full copy completes (all historical messages)
2. Bot switches to polling mode
3. New messages forwarded within 5 seconds
4. Target channel stays up-to-date forever

---

## ✅ Summary

**Full Copy Mode (`backfill_count: 0`):**

✅ Copies ALL messages from beginning to end
✅ Processes in chronological order
✅ Respects filters and replacement rules
✅ Handles media groups correctly
✅ Automatic rate limit handling
✅ Resumes after interruption
✅ Transitions to live forwarding automatically

**Perfect for:** Complete channel mirrors, backups, migrations

**Time:** Hours to days depending on channel size

**After completion:** Normal live forwarding continues forever

---

**🎉 Your complete channel history is now preserved and live-syncing!**

