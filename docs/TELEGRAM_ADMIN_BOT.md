# 🤖 Telegram Admin Bot Setup Guide

Instead of using a web interface, you can manage your forwarder bot directly from Telegram using an admin bot!

## ✨ Features

The Telegram admin bot allows you to:

- ✅ **Add/Remove Channel Pairs** - Manage forwarding channels
- ✅ **Create Replacement Rules** - Add text replacements on the fly
- ✅ **Configure Filters** - Set up whitelist/blacklist keywords
- ✅ **View Status** - Check current configuration
- ✅ **Toggle Settings** - Enable/disable pairs and filters
- ✅ **Reload Config** - Refresh configuration
- ✅ **Secure** - Only authorized users can access

## 🚀 Setup (3 Steps)

### Step 1: Create a Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow the instructions:
   - Choose a name (e.g., "My Forwarder Admin")
   - Choose a username (e.g., "myforwarder_admin_bot")
4. **Copy the bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID (a number like `123456789`)
3. **Copy your user ID**

### Step 3: Configure

Edit `config.json` and add:

```json
{
  "api_credentials": {
    ...
  },
  "admin_bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
  "admin_user_ids": [123456789],
  "channel_pairs": [
    ...
  ]
}
```

**Important:**
- `admin_bot_token` - Your bot token from BotFather
- `admin_user_ids` - Array of user IDs who can use the admin bot

## 🎯 Running the Admin Bot

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Run the admin bot
python admin_bot.py
```

The bot will start and wait for commands.

## 📱 Using the Admin Bot

### Start the Bot

1. Find your bot on Telegram (search for the username you created)
2. Send `/start`
3. You'll see the main menu with buttons

### Main Menu Options

```
📡 Channel Pairs - Manage forwarding channels
🔄 Replacement Rules - Text replacement settings
🔍 Filters - Message filtering options
⚙️ Settings - View bot settings
📊 Status - Current configuration
🔄 Reload Config - Refresh configuration
```

### Commands

- `/start` - Show main menu
- `/status` - Check bot status
- `/menu` - Show main menu
- `/help` - Get help

## 📋 Common Tasks

### Add a Channel Pair

1. Click **📡 Channel Pairs**
2. Click **➕ Add Pair**
3. Send channel IDs in format: `source_id target_id backfill_count`
4. Example: `-1001234567890 -1009876543210 10`

**To get channel IDs:**
- Forward a message from the channel to @userinfobot
- Copy the channel ID (negative number)

### Add Replacement Rule

1. Click **🔄 Replacement Rules**
2. Click **➕ Add Rule**
3. Send in format: `find | replace | case_sensitive`
4. Example: `Elite | Premium | no`

### Configure Filters

1. Click **🔍 Filters**
2. Options:
   - **🔄 Toggle** - Enable/disable filtering
   - **📝 Change Mode** - Switch between whitelist/blacklist
   - **➕ Add Keyword** - Add keywords to filter
   - **🗑️ Clear Keywords** - Remove all keywords

**Filter Modes:**
- **Whitelist** - Forward only messages containing keywords
- **Blacklist** - Forward all except messages with keywords

### Adding Keywords

Send keywords in two formats:

**Option 1: One per line**
```
GOLD
SIGNAL
BUY
```

**Option 2: Comma-separated**
```
GOLD, SIGNAL, BUY
```

## 🔒 Security

### Restrict Access

Only users in `admin_user_ids` can use the bot:

```json
{
  "admin_user_ids": [123456789, 987654321]
}
```

Add multiple user IDs to allow access to team members.

### Best Practices

- ✅ Keep your bot token secret
- ✅ Only add trusted user IDs
- ✅ Don't share the bot publicly
- ✅ Use a strong bot username

## 🎭 Example Usage Flow

### Scenario: Add a new channel pair

1. **Send /start** to your admin bot
2. **Click** "📡 Channel Pairs"
3. **Click** "➕ Add Pair"
4. **Send**: `-1001111111111 -1002222222222 10`
5. **Bot replies**: ✅ Channel pair added!
6. **Restart** the main forwarder bot
7. **Done!** Messages will now forward from new source

### Scenario: Add text replacement

1. **Send /start**
2. **Click** "🔄 Replacement Rules"
3. **Click** "➕ Add Rule"
4. **Send**: `Elite | Premium | no`
5. **Bot replies**: ✅ Replacement rule added!
6. **Restart** the forwarder bot
7. **Done!** Text will be replaced in messages

## 🔄 Running Both Bots

You need to run TWO bots:

### Terminal 1: Main Forwarder Bot
```bash
python bot.py
```
This bot does the actual message forwarding.

### Terminal 2: Admin Bot
```bash
python admin_bot.py
```
This bot handles your admin commands.

**Or use tmux/screen:**

```bash
# Terminal multiplexer approach
tmux new -s forwarder
python bot.py
# Press Ctrl+B then D to detach

tmux new -s admin
python admin_bot.py
# Press Ctrl+B then D to detach

# To reattach: tmux attach -t forwarder or tmux attach -t admin
```

## 🚀 Production Deployment

### Option 1: Systemd Services

Create two service files:

**1. Forwarder Bot Service** (already included)
```bash
sudo systemctl start telegram-forwarder
```

**2. Admin Bot Service**

Create `/etc/systemd/system/telegram-admin-bot.service`:

```ini
[Unit]
Description=Telegram Forwarder Admin Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/telegram-addresser
Environment="PATH=/path/to/telegram-addresser/venv/bin"
ExecStart=/path/to/telegram-addresser/venv/bin/python admin_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable telegram-admin-bot
sudo systemctl start telegram-admin-bot
```

### Option 2: Screen/Tmux

```bash
# Start forwarder bot
screen -dmS forwarder bash -c 'cd /path/to/telegram-addresser && python bot.py'

# Start admin bot
screen -dmS admin bash -c 'cd /path/to/telegram-addresser && python admin_bot.py'

# View screens
screen -ls

# Attach to a screen
screen -r forwarder
screen -r admin
```

## 📊 Comparison: Web vs Telegram Bot

| Feature | Web Panel | Telegram Bot |
|---------|-----------|--------------|
| **Access** | Browser required | Any device with Telegram |
| **Convenience** | Need to open URL | Instant messaging |
| **Mobile** | Mobile browser | Native Telegram app |
| **Notifications** | No | Yes (from bot) |
| **Ease of Use** | Visual forms | Text commands |
| **Security** | Local/SSH tunnel | User ID authentication |
| **Port** | Requires port 5000 | No extra ports |

**Recommendation:** Use the Telegram bot for most tasks. Keep the web panel as backup.

## ❓ Troubleshooting

### "Invalid token" error

- Check your bot token in `config.json`
- Make sure there are no extra spaces
- Token format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### "You are not authorized" message

- Check your user ID in `admin_user_ids`
- Get your ID from @userinfobot
- Make sure it's a number, not a string

### Bot doesn't respond

- Check if `admin_bot.py` is running
- Look at the console for errors
- Verify bot token is correct
- Make sure bot isn't blocked

### Changes not taking effect

- Changes to config are saved immediately
- **But** you must restart `bot.py` (the forwarder) for changes to apply
- The admin bot doesn't need restarting

## 💡 Tips

### Quick Status Check

Send `/status` anytime to see:
- Number of channel pairs
- Number of replacement rules
- Filter status
- Current configuration

### Multiple Admins

Add multiple user IDs:

```json
{
  "admin_user_ids": [123456789, 987654321, 456789123]
}
```

### Getting Channel IDs Quickly

1. Forward message to @userinfobot
2. Or use @getidsbot
3. Or check with your admin bot using /status

### Test Changes

Before restarting the forwarder:
1. Add new channel pair via admin bot
2. Check /status to verify
3. Then restart forwarder bot

## 🎉 You're Ready!

Your Telegram admin bot is set up! Now you can:

✅ Manage everything from Telegram  
✅ Add channels on the go  
✅ Update rules anytime  
✅ Check status instantly  
✅ Control from any device  

---

**Pro Tip:** Pin the admin bot chat in Telegram for quick access! 📌

