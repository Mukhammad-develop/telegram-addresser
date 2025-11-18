# ⚡ Quick Start Guide

Get your Telegram Forwarder Bot running in 5 minutes!

## 🎯 Prerequisites

- Python 3.8+
- Telegram account
- API credentials from https://my.telegram.org

> 💡 **New in v0.6:** Multi-worker mode for better performance! See below for setup.

## 🚀 Installation (3 steps)

### Step 1: Get API Credentials

1. Visit https://my.telegram.org
2. Login with your phone number
3. Go to "API development tools"
4. Create an app (name and short name can be anything)
5. Copy your `api_id` (number) and `api_hash` (string)

### Step 2: Configure

Edit `config.json`:

```json
{
  "api_credentials": {
    "api_id": YOUR_API_ID_HERE,
    "api_hash": "YOUR_API_HASH_HERE",
    "session_name": "forwarder_session"
  },
  "channel_pairs": [
    {
      "source": -1001234567890,
      "target": -1009876543210,
      "enabled": true,
      "backfill_count": 10
    }
  ]
}
```

**How to get Channel IDs:**
- Forward any message from the channel to [@userinfobot](https://t.me/userinfobot)
- The bot will reply with the channel ID
- Channel IDs are negative numbers

### Step 3: Run

#### Option A: Using start script (recommended)
```bash
./start.sh
```

#### Option B: Manual
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run bot
python bot.py
```

First time you run, you'll need to:
1. Enter your phone number (with country code, e.g., +1234567890)
2. Enter the code sent to your Telegram
3. Enter 2FA password if you have it enabled

Done! Bot is now running.

---

## 🚀 Multi-Worker Mode (v0.6+)

Want to use **multiple Telegram accounts** for better performance? The bot auto-detects multi-worker mode!

### Setup Multi-Worker:

**Edit `config.json`:**
```json
{
  "admin_bot_token": "YOUR_BOT_TOKEN",
  "admin_user_ids": [123456789],
  "workers": [
    {
      "worker_id": "worker_1",
      "api_credentials": {
        "api_id": 12345678,
        "api_hash": "abc123...",
        "session_name": "worker_1_session"
      },
      "channel_pairs": [...]
    },
    {
      "worker_id": "worker_2",
      "api_credentials": {
        "api_id": 87654321,
        "api_hash": "xyz789...",
        "session_name": "worker_2_session"
      },
      "channel_pairs": [...]
    }
  ]
}
```

**Run the same command:**
```bash
./start.sh  # Automatically detects multi-worker mode!
```

**Benefits:**
- ✅ Bypass rate limits (20 msg/min per worker)
- ✅ Better fault tolerance (one crash doesn't stop others)
- ✅ Higher throughput for busy channels

See [V0.6_FEATURES.md](V0.6_FEATURES.md) for full multi-worker documentation.

---

## 🎛️ Admin Panel (Optional)

Want a web interface? Run:

```bash
python admin_panel.py
```

Open http://127.0.0.1:5000 in your browser.

From the admin panel you can:
- ➕ Add/remove channel pairs
- 🔄 Create text replacement rules
- 🔍 Set up filters
- ⚙️ Adjust settings
- 🔴 Enable/disable channels

All changes save to `config.json` automatically.

## 📝 Common Tasks

### Add a new channel pair

**Via Admin Panel:**
1. Open http://127.0.0.1:5000
2. Fill in Source and Target IDs
3. Click "Add Channel Pair"
4. Restart bot

**Via config.json:**
```json
{
  "channel_pairs": [
    {
      "source": -1001234567890,
      "target": -1009876543210,
      "enabled": true,
      "backfill_count": 10
    },
    {
      "source": -1001111111111,
      "target": -1002222222222,
      "enabled": true,
      "backfill_count": 5
    }
  ]
}
```

### Add text replacement rule

**Example: Replace "Elite" with "Premium"**

Via config.json:
```json
{
  "replacement_rules": [
    {
      "find": "Elite",
      "replace": "Premium",
      "case_sensitive": false
    }
  ]
}
```

### Enable filtering

**Forward only messages with certain keywords:**

```json
{
  "filters": {
    "enabled": true,
    "mode": "whitelist",
    "keywords": ["GOLD", "SIGNAL", "BUY", "SELL"]
  }
}
```

**Block messages with certain keywords:**

```json
{
  "filters": {
    "enabled": true,
    "mode": "blacklist",
    "keywords": ["spam", "advertisement"]
  }
}
```

### View logs

```bash
tail -f logs/forwarder.log
```

### Stop the bot

Press `Ctrl+C`

## 🔧 Running 24/7

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- VPS setup
- Running as system service
- Auto-start on boot
- Production configuration

## ❓ Troubleshooting

### Bot won't start
- Check API credentials in config.json
- Make sure virtual environment is activated
- Run: `pip install -r requirements.txt`

### Messages not forwarding
- Verify channel IDs (must be negative numbers)
- Check if your account is a member of both channels
- Look at logs: `tail -f logs/forwarder.log`

### Can't connect to channel
- Make sure you're a member
- For private channels, you must be invited
- Some channels restrict forwarding

### More help?
Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

## 📚 Full Documentation

- [README.md](README.md) - Complete feature list and usage
- [DEPLOYMENT.md](DEPLOYMENT.md) - VPS deployment guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions

## 🎉 That's It!

Your bot is now:
- ✅ Forwarding messages in real-time
- ✅ Applying text replacements
- ✅ Handling media and albums
- ✅ Automatically retrying on errors
- ✅ Logging all activity

Send a test message to your source channel and watch it appear in the target! 🚀

---

**Pro Tips:**
- 💡 Use the admin panel for easy configuration
- 💡 Start with `backfill_count: 10` to test
- 💡 Enable filters to forward only relevant messages
- 💡 Check logs regularly: `tail -f logs/forwarder.log`
- 💡 Back up your `config.json` and `.session` files

