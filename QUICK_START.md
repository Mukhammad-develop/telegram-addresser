# 🚀 Quick Start Guide

## ⚡ TL;DR (Too Long; Didn't Read)

```bash
# 1. Copy and edit config
cp config.example.json config.json
# Edit config.json with your API credentials

# 2. Run the bot
./start.sh

# That's it! The bot auto-detects single or multi-worker mode.
```

---

## 📋 Step-by-Step Setup

### Step 1: Get API Credentials

Go to https://my.telegram.org/apps and create an app:
- You'll get `api_id` (numbers)
- You'll get `api_hash` (long string)

**Need multiple workers?** Create multiple apps/accounts for better performance.

---

### Step 2: Create Config File

```bash
cp config.example.json config.json
```

Then edit `config.json`:

#### Option A: Single Worker (Simple)

Keep the `api_credentials` section, remove `workers`:

```json
{
  "admin_bot_token": "YOUR_BOT_TOKEN",
  "admin_user_ids": [YOUR_USER_ID],
  
  "api_credentials": {
    "api_id": 12345678,
    "api_hash": "abc123def456...",
    "session_name": "forwarder_session"
  },
  
  "channel_pairs": [
    {
      "source": -1001234567890,
      "target": -1009876543210,
      "enabled": true,
      "backfill_count": 10
    }
  ],
  
  "replacement_rules": [],
  "filters": {"enabled": false},
  "settings": {...}
}
```

#### Option B: Multi-Worker (Advanced)

Remove `api_credentials`, add `workers` array:

```json
{
  "admin_bot_token": "YOUR_BOT_TOKEN",
  "admin_user_ids": [YOUR_USER_ID],
  
  "workers": [
    {
      "worker_id": "worker_1",
      "api_id": 12345678,
      "api_hash": "abc123...",
      "session_name": "worker_1_session",
      "enabled": true,
      "channel_pairs": [...],
      ...
    },
    {
      "worker_id": "worker_2",
      "api_id": 87654321,
      "api_hash": "xyz789...",
      "session_name": "worker_2_session",
      "enabled": true,
      "channel_pairs": [...],
      ...
    }
  ]
}
```

---

### Step 3: Get Channel IDs

Forward a message from your channels to [@userinfobot](https://t.me/userinfobot) on Telegram.

It will show:
```
Forwarded from: Channel Name
Channel ID: -1001234567890
```

Use these IDs in your `channel_pairs`.

---

### Step 4: Run the Bot

```bash
./start.sh
```

The script automatically:
- ✅ Creates virtual environment
- ✅ Installs dependencies
- ✅ Detects single vs multi-worker mode
- ✅ Starts the appropriate bot

**Output for single-worker:**
```
📡 Single-Worker Mode Detected
🎉 Starting bot...
```

**Output for multi-worker:**
```
🎯 Multi-Worker Mode Detected
📊 Active workers: 2
🎉 Starting Worker Manager...
```

---

## 🎮 Using Admin Bot

After bot is running, use the admin bot in Telegram:

1. Start your admin bot: `@your_bot_name`
2. Send `/start`
3. Manage channels, rules, and workers from Telegram!

---

## ❓ FAQ

**Q: Single or Multi-Worker mode?**
A: 
- **Single:** Simpler setup, good for < 10 channel pairs
- **Multi:** Better performance, bypasses rate limits, good for 10+ pairs

**Q: How many workers do I need?**
A: 
- 1-10 channels: 1 worker
- 10-30 channels: 2-3 workers
- 30+ channels: 4+ workers

**Q: Can I switch modes later?**
A: Yes! Just edit `config.json` and restart with `./start.sh`

**Q: Where are logs?**
A: `logs/forwarder.log` (single) or `logs/worker_manager.log` (multi)

**Q: How do I stop the bot?**
A: Press `Ctrl+C` in the terminal

**Q: Bot won't start?**
A: 
1. Check `config.json` is valid JSON
2. Verify API credentials are correct
3. Check logs in `logs/` directory

---

## 🎯 Next Steps

After setup:

1. **Add Channel Pairs**: Use admin bot or edit `config.json`
2. **Set Replacement Rules**: Replace text/links in forwarded messages
3. **Configure Filters**: Whitelist/blacklist specific keywords
4. **Monitor Logs**: Check `logs/` directory for any issues

---

## 📚 More Documentation

- Full Feature Guide: `docs/V0.6_FEATURES.md`
- Development Status: `docs/V0.6_STATUS.md`
- Main README: `README.md`

---

## 🆘 Need Help?

1. Check logs: `tail -f logs/forwarder.log`
2. Check config is valid: `python3 -m json.tool config.json`
3. See documentation in `docs/` folder
4. Report issues with log output

---

**That's it! You're ready to go! 🎉**

