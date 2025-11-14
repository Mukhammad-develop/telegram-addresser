# 🎯 START HERE - Telegram Forwarder Bot

Welcome! This is your complete Telegram multi-channel forwarding system.

---

## ⚡ What This Bot Does

Automatically forwards messages from multiple Telegram channels to other channels with:
- **Real-time forwarding** (near-zero delay)
- **Text replacement** (customize messages)
- **Message filtering** (forward only what you need)
- **Media support** (photos, videos, documents, albums)
- **24/7 operation** (runs continuously)
- **Web admin panel** (easy configuration)

---

## 🚀 Getting Started (3 Steps)

### Step 1: Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click "API development tools"
4. Create an app (name can be anything)
5. **Copy your `api_id` and `api_hash`**

### Step 2: Configure

Open `config.json` and update:

```json
{
  "api_credentials": {
    "api_id": PUT_YOUR_API_ID_HERE,
    "api_hash": "PUT_YOUR_API_HASH_HERE",
    "session_name": "forwarder_session"
  }
}
```

**Get Channel IDs:**
- Forward a message from the channel to @userinfobot
- Copy the negative number (e.g., -1001234567890)

Add your channel pairs:

```json
{
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

### Step 3: Run

```bash
./start.sh
```

First time you'll need to:
1. Enter phone number (with country code: +1234567890)
2. Enter verification code from Telegram
3. Enter 2FA password (if enabled)

**Done!** Bot is now forwarding messages.

---

## 📁 What's Included

| File | Purpose |
|------|---------|
| `bot.py` | Main bot application |
| `admin_panel.py` | Web interface for configuration |
| `config.json` | Your configuration |
| `start.sh` | Quick start script |
| `requirements.txt` | Python dependencies |
| **Documentation:** | |
| `README.md` | Complete user guide |
| `QUICK_START.md` | 5-minute setup guide |
| `DEPLOYMENT.md` | VPS deployment guide |
| `TROUBLESHOOTING.md` | Problem solving |
| `PROJECT_OVERVIEW.md` | Technical overview |

---

## 🎛️ Using the Admin Panel

For easy configuration without editing JSON:

```bash
python admin_panel.py
```

Open http://127.0.0.1:5000

From there you can:
- ✅ Add/remove channel pairs
- ✅ Create text replacement rules
- ✅ Configure filters
- ✅ Adjust settings

---

## 📖 Documentation Roadmap

**Choose your path:**

### 🟢 I'm a beginner
👉 Read [QUICK_START.md](QUICK_START.md)
- Simple 5-minute setup
- Step-by-step with examples
- Common tasks explained

### 🟡 I want to learn everything
👉 Read [README.md](README.md)
- Complete feature list
- All configuration options
- Advanced usage examples
- Security best practices

### 🔵 I'm deploying to a server
👉 Read [DEPLOYMENT.md](DEPLOYMENT.md)
- VPS setup instructions
- Systemd service configuration
- Production best practices
- Monitoring and maintenance

### 🔴 I have a problem
👉 Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Common issues and solutions
- Diagnostic commands
- Emergency procedures
- Performance optimization

### ⚫ I'm a developer
👉 Read [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
- Technical architecture
- Code structure
- API reference
- Extension guide

---

## 🎯 Common Use Cases

### Use Case 1: Simple Forwarding
**Scenario:** Forward all messages from Channel A to Channel B

**Setup:**
```json
{
  "channel_pairs": [
    {"source": -1001111111111, "target": -1002222222222, "enabled": true, "backfill_count": 10}
  ]
}
```

### Use Case 2: Rebrand Messages
**Scenario:** Forward messages but replace brand names

**Setup:**
```json
{
  "replacement_rules": [
    {"find": "OldBrand", "replace": "NewBrand", "case_sensitive": false},
    {"find": "https://old-link.com", "replace": "https://new-link.com", "case_sensitive": true}
  ]
}
```

### Use Case 3: VIP Signals Channel
**Scenario:** Forward only trading signals (messages with keywords)

**Setup:**
```json
{
  "filters": {
    "enabled": true,
    "mode": "whitelist",
    "keywords": ["GOLD", "BUY", "SELL", "SIGNAL"]
  }
}
```

### Use Case 4: Multi-Channel Hub
**Scenario:** Forward from multiple sources to multiple targets

**Setup:**
```json
{
  "channel_pairs": [
    {"source": -1001111111111, "target": -1002222222222, "enabled": true, "backfill_count": 10},
    {"source": -1003333333333, "target": -1004444444444, "enabled": true, "backfill_count": 5},
    {"source": -1005555555555, "target": -1006666666666, "enabled": true, "backfill_count": 10}
  ]
}
```

---

## ✅ Quick Checklist

Before running the bot, make sure:

- [ ] Python 3.8+ is installed (`python3 --version`)
- [ ] You have Telegram API credentials
- [ ] config.json has your API credentials
- [ ] Channel IDs are correct (negative numbers)
- [ ] Your account is a member of source channels
- [ ] Virtual environment dependencies are installed

---

## 🔧 Essential Commands

### Run the bot
```bash
./start.sh
```

### Run admin panel
```bash
python admin_panel.py
```

### View logs
```bash
tail -f logs/forwarder.log
```

### Stop the bot
Press `Ctrl+C`

---

## ❓ FAQ

### Q: How do I get channel IDs?
A: Forward any message from the channel to @userinfobot on Telegram.

### Q: Can I forward from channels I don't own?
A: Yes! You just need to be a member of the channel.

### Q: Will it work if I close my terminal?
A: For local testing: No. For 24/7 operation: See [DEPLOYMENT.md](DEPLOYMENT.md) for running as a service.

### Q: How many channels can I monitor?
A: Unlimited! The bot supports 10+ channels easily.

### Q: Can I replace links in messages?
A: Yes! Add replacement rules for any text including URLs.

### Q: What if Telegram rate limits me?
A: Bot automatically handles rate limits and retries.

### Q: Can I filter which messages to forward?
A: Yes! Use whitelist mode (only certain keywords) or blacklist mode (exclude certain keywords).

### Q: Does it preserve the "Forwarded from" tag?
A: Yes! Messages look exactly like manual forwards.

---

## 🚨 Troubleshooting Quick Tips

### Bot won't start
```bash
# Make sure dependencies are installed
source venv/bin/activate
pip install -r requirements.txt
```

### Messages not forwarding
```bash
# Check logs for errors
tail -f logs/forwarder.log

# Verify channel IDs
# Make sure you're a member of both channels
```

### Can't connect to channel
- Ensure you're a member of the channel
- For private channels, you must be invited
- Some channels block bots - check channel settings

For more help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 🎉 You're Ready!

1. **Configure** `config.json` with your credentials
2. **Run** `./start.sh`
3. **Test** by sending a message to your source channel
4. **Watch** it appear in your target channel!

---

## 📞 Next Steps

After you get it working:

1. ✅ Test with a few messages
2. ✅ Try the admin panel
3. ✅ Add text replacement rules
4. ✅ Set up filters if needed
5. ✅ Deploy to VPS for 24/7 operation

---

## 💡 Pro Tips

- 💡 Start with `backfill_count: 10` to catch recent messages
- 💡 Use admin panel for easy configuration
- 💡 Check logs regularly: `tail -f logs/forwarder.log`
- 💡 Back up your `config.json` and `.session` files
- 💡 Test with one channel pair before adding more
- 💡 Use filters to forward only relevant content

---

## 🌟 Features at a Glance

✅ Real-time forwarding (< 1 second delay)  
✅ Multi-channel support (10+ channels)  
✅ Text replacement (unlimited rules)  
✅ Message filtering (whitelist/blacklist)  
✅ Media support (photos, videos, albums)  
✅ Auto-retry on errors  
✅ Flood-wait handling  
✅ Web admin panel  
✅ Comprehensive logging  
✅ 24/7 operation ready  
✅ Complete documentation  

---

## 🎊 Let's Go!

Everything is set up and ready. Just configure and run!

**Questions?** Check the documentation files above.

**Problems?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Ready to deploy?** See [DEPLOYMENT.md](DEPLOYMENT.md)

---

**Happy Forwarding! 🚀**

