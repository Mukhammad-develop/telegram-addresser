# Automatic Config Reload - No Restart Needed! 🎉

## What's New

Your bot now **automatically detects** when you add new channel pairs to `config.json` - **no restart required**!

## How It Works

### For Multi-Worker Mode (what you're using):

1. **Worker Manager** checks `config.json` every **2 minutes**
2. When changes detected, it automatically:
   - Restarts workers with new channel pairs
   - Starts new workers if you add them
   - Updates settings without manual intervention

### For Single Bot Mode:

1. **Bot** checks `config.json` every **2 minutes**  
2. When changes detected, it automatically:
   - Reloads replacement rules and filters
   - Detects new channel pairs
   - Runs backfill for new pairs
   - Starts forwarding immediately

## Usage

### Adding a New Channel Pair (No Restart!)

1. **Edit config.json** while bot is running:
```json
{
  "workers": [
    {
      "worker_id": "std",
      "channel_pairs": [
        {
          "source": -1002074427408,
          "target": -1003210400780,
          "enabled": true,
          "backfill_count": 10
        },
        {
          "source": -1002382939779,  // ← NEW PAIR
          "target": -1003210400780,
          "enabled": true,
          "backfill_count": 10
        }
      ]
    }
  ]
}
```

2. **Save the file**

3. **Wait up to 2 minutes** - you'll see in logs:
```
[INFO] 🔄 Config file modified - checking for changes...
[INFO] 🔄 Config changed for worker std - restarting...
[INFO] ✅ Worker std restarted with new config
[INFO] 🆕 New pair detected: -1002382939779 -> -1003210400780
[INFO] 🔄 Backfilling 10 messages...
[INFO] ✅ New pair backfilled and ready
```

4. **Done!** New pair is now forwarding messages

## What Gets Reloaded Automatically

✅ **New channel pairs** - Auto-detected and started  
✅ **Replacement rules** - Text processing updated  
✅ **Filters** - Keyword filters updated  
✅ **Settings** - Retry delays, logging, etc.  
✅ **Backfill** - Automatically runs for new pairs  

## Monitoring

### Check Worker Manager Logs
```bash
tail -f logs/worker_manager.log
```

### Check Individual Worker Logs
```bash
tail -f logs/worker_std.log
```

## Immediate Reload (No Wait)

If you can't wait 2 minutes, create a trigger file:

```bash
touch trigger_reload.flag
```

The bot will reload **immediately** (within 5 seconds).

## Troubleshooting

### "Config changed but worker didn't restart"

- Check file was actually saved (modification time changed)
- Check JSON syntax is valid: `python -m json.tool config.json`
- Check logs for error messages

### "Worker restarted but pair still not working"

- Verify channel IDs are correct (must start with -100)
- Check your account has access to both channels
- Look for error messages in worker logs

## Tips

- **Don't restart manually** - let auto-reload handle it
- **Wait 2 minutes** after editing config
- **Check logs** to confirm reload happened
- **Test with backfill_count: 1** first to avoid flooding

## Technical Details

- **Check interval**: Every 2 minutes (120 seconds)
- **Worker restart**: Graceful shutdown + restart with new config
- **Backfill**: Runs automatically for new pairs
- **Message tracking**: Preserves deletion sync across restarts

---

**No more restarts needed!** Just edit, save, and wait 2 minutes. 🚀
