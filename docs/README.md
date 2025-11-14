# 🚀 Telegram Multi-Channel Forwarder Bot

A robust, 24/7 automated forwarding system that copies messages from multiple source channels to corresponding target channels. Built with Python and Telethon.

## ✨ Features

### Core Functionality
- ✅ **Real-time forwarding** - Near-zero delay message forwarding
- ✅ **Multi-channel support** - Forward from 10+ source channels simultaneously
- ✅ **Preserves "Forwarded from"** - Maintains original message metadata
- ✅ **Media group support** - Handles albums, photos+captions correctly
- ✅ **All content types** - Text, photos, videos, documents, voice messages

### Text Processing
- ✅ **Custom rewrite rules** - Replace keywords/sentences before forwarding
- ✅ **Case-sensitive/insensitive** - Flexible text replacement options
- ✅ **Link replacement** - Custom WhatsApp, Telegram, or any link replacements
- ✅ **Caption processing** - Rules apply to media captions too

### Filtering
- ✅ **Whitelist mode** - Forward only messages containing specific keywords
- ✅ **Blacklist mode** - Forward all except messages with specific keywords
- ✅ **Easy configuration** - Manage filters via web admin panel

### Reliability
- ✅ **Auto-retry logic** - Exponential backoff on failures
- ✅ **Flood-wait handling** - Automatic rate limit management
- ✅ **Crash-proof** - Auto-restart on unexpected errors
- ✅ **Comprehensive logging** - Rotating logs with detailed diagnostics

### Management
- ✅ **Web admin panel** - Beautiful, easy-to-use configuration interface
- ✅ **No code editing needed** - All settings manageable via UI or JSON
- ✅ **24/7 daemon mode** - Runs as a background service
- ✅ **Backfill support** - Forward recent messages on startup

## 📋 Requirements

- Python 3.8+
- Telegram API credentials (API ID and API HASH)
- Linux server or VPS (for 24/7 operation)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd telegram-addresser

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click on "API development tools"
4. Create a new application
5. Copy your `api_id` and `api_hash`

### 3. Configure the Bot

Edit `config.json`:

```json
{
  "api_credentials": {
    "api_id": YOUR_API_ID,
    "api_hash": "YOUR_API_HASH",
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
  "replacement_rules": [
    {
      "find": "Elite",
      "replace": "Excellent",
      "case_sensitive": false
    }
  ]
}
```

**How to get Channel IDs:**
- Forward a message from the channel to @userinfobot
- Or use @getidsbot
- Channel IDs are negative numbers (e.g., -1001234567890)

### 4. First Run

```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python bot.py
```

On first run, you'll be prompted to:
1. Enter your phone number
2. Enter the confirmation code sent to your Telegram
3. Enter 2FA password (if enabled)

The bot will create a session file and start forwarding.

## 🎛️ Admin Panel

The web-based admin panel provides an easy interface to manage everything:

### Start the Admin Panel

```bash
python admin_panel.py
```

Then open http://127.0.0.1:5000 in your browser.

### Features:
- **Add/Remove Channel Pairs** - No need to edit JSON files
- **Manage Replacement Rules** - Add custom text replacements
- **Configure Filters** - Set up whitelist/blacklist keywords
- **Toggle Channels** - Enable/disable specific pairs
- **Adjust Settings** - Retry attempts, delays, log levels

## 📖 Usage Examples

### Example 1: Simple Forwarding

Forward all messages from Channel A to Channel B:

```json
{
  "channel_pairs": [
    {
      "source": -1001111111111,
      "target": -1002222222222,
      "enabled": true,
      "backfill_count": 10
    }
  ]
}
```

### Example 2: Multi-Channel with Replacements

Forward from multiple sources with text replacement:

```json
{
  "channel_pairs": [
    {
      "source": -1001111111111,
      "target": -1002222222222,
      "enabled": true,
      "backfill_count": 10
    },
    {
      "source": -1003333333333,
      "target": -1004444444444,
      "enabled": true,
      "backfill_count": 5
    }
  ],
  "replacement_rules": [
    {
      "find": "Elite",
      "replace": "Premium",
      "case_sensitive": false
    },
    {
      "find": "https://wa.me/1234567890",
      "replace": "https://wa.me/9876543210",
      "case_sensitive": true
    }
  ]
}
```

### Example 3: Filtered Forwarding

Only forward messages containing specific keywords:

```json
{
  "filters": {
    "enabled": true,
    "mode": "whitelist",
    "keywords": ["GOLD", "BUY", "SELL", "SIGNAL"]
  }
}
```

## 🔧 Configuration Reference

### Channel Pairs

| Field | Type | Description |
|-------|------|-------------|
| `source` | int | Source channel ID (negative number) |
| `target` | int | Target channel ID (negative number) |
| `enabled` | bool | Whether this pair is active |
| `backfill_count` | int | Number of recent messages to forward on startup (0-100) |

### Replacement Rules

| Field | Type | Description |
|-------|------|-------------|
| `find` | string | Text to search for |
| `replace` | string | Text to replace with |
| `case_sensitive` | bool | Whether matching is case-sensitive |

### Filters

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Enable/disable filtering |
| `mode` | string | `"whitelist"` or `"blacklist"` |
| `keywords` | array | List of keywords to filter by |

### Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `retry_attempts` | int | 5 | Number of retry attempts on failure |
| `retry_delay` | int | 5 | Initial delay between retries (seconds) |
| `flood_wait_extra_delay` | int | 10 | Extra delay added to flood wait time |
| `max_message_length` | int | 4096 | Maximum message length before splitting |
| `log_level` | string | "INFO" | Logging level (DEBUG, INFO, WARNING, ERROR) |

## 📊 Logging

Logs are stored in `logs/forwarder.log` with automatic rotation:

- **Max size**: 10MB per file
- **Backup count**: 5 files
- **Format**: `[YYYY-MM-DD HH:MM:SS] LEVEL [module:function:line] message`

View recent logs:
```bash
tail -f logs/forwarder.log
```

## 🛠️ Troubleshooting

### Bot doesn't start
- Check API credentials in `config.json`
- Ensure virtual environment is activated
- Check `logs/forwarder.log` for errors

### Messages not forwarding
- Verify channel IDs are correct (negative numbers)
- Check if bot account has access to both source and target channels
- Review filter settings (might be blocking messages)
- Check logs for permission errors

### Flood wait errors
- Bot automatically handles these
- Increase `flood_wait_extra_delay` in settings if frequent
- Consider reducing backfill count

### Permission errors
- Bot account must be a member of source channel
- For target channel, bot account may need admin rights depending on channel settings
- Some channels block forwarding - check channel settings

## 🔒 Security Notes

- **Never share** your `api_id`, `api_hash`, or session files
- The `.session` file contains authentication - keep it secure
- Use strong 2FA on your Telegram account
- Review all channel pairs before deployment
- Monitor logs regularly for suspicious activity

## 🚦 Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on:
- VPS setup
- Systemd service configuration
- Auto-start on boot
- Monitoring and maintenance
- Security hardening

## 🤝 Support

For issues or questions:
1. Check `logs/forwarder.log` for error messages
2. Review this README thoroughly
3. Ensure all configuration is correct
4. Test with small channel first before scaling

## 📝 License

This project is provided as-is for automation purposes. Ensure compliance with Telegram's Terms of Service when using.

## 🔄 Updates

To update the bot:
```bash
# Backup your config
cp config.json config.json.backup

# Pull latest changes or replace files
# Restore your config
cp config.json.backup config.json

# Restart the bot
sudo systemctl restart telegram-forwarder
```

---

**Made with ❤️ for seamless Telegram automation**

