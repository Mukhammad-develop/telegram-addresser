# 🚀 PythonAnywhere Complete Setup Guide

**Complete guide to deploy and run Telegram Forwarder Bot 24/7 on PythonAnywhere**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Account Setup](#account-setup)
3. [Upload Project Files](#upload-project-files)
4. [Configuration](#configuration)
5. [Worker Authentication](#worker-authentication)
6. [Always-On Tasks Setup](#always-on-tasks-setup)
7. [File Structure](#file-structure)
8. [Monitoring & Logs](#monitoring--logs)
9. [Troubleshooting](#troubleshooting)
10. [Updates & Maintenance](#updates--maintenance)
11. [Best Practices](#best-practices)

---

## Prerequisites

### What You Need:

✅ **PythonAnywhere Account**
- Paid tier required for 24/7 operation ($5/month minimum)
- Free tier only for testing (limited uptime)
- Sign up: https://www.pythonanywhere.com

✅ **Telegram Credentials**
- Bot token (from @BotFather)
- Your user ID (from @userinfobot)
- API ID + API hash (from https://my.telegram.org)
- Phone number for worker authentication

✅ **Channel Information**
- Source channel IDs (negative numbers like `-1001234567890`)
- Target channel IDs (negative numbers)
- Bot must be admin in ALL channels

---

## Account Setup

### Step 1: Create PythonAnywhere Account

1. Go to **https://www.pythonanywhere.com**
2. Click **"Pricing & signup"**
3. Choose **"Hacker"** plan ($5/month) - Recommended for 24/7 operation
4. Complete signup and verify email

### Step 2: Access Dashboard

After login, you'll see tabs:
- **Dashboard** - Overview
- **Consoles** - Terminal access
- **Files** - File manager
- **Web** - Web apps (not needed for this bot)
- **Tasks** - Where we'll set up 24/7 operation
- **Databases** - Not needed

---

## Upload Project Files

### Method 1: Upload via ZIP (Easiest)

1. **Prepare project locally:**
   ```bash
   cd /path/to/telegram-addresser
   
   # Create archive (exclude unnecessary files)
   zip -r telegram-addresser.zip . \
     -x "venv/*" \
     -x "*.session*" \
     -x "logs/*" \
     -x "__pycache__/*" \
     -x ".git/*" \
     -x "*.pyc"
   ```

2. **Upload to PythonAnywhere:**
   - Click **"Files"** tab
   - Click **"Upload a file"**
   - Select `telegram-addresser.zip`
   - Wait for upload to complete

3. **Extract in Bash console:**
   - Click **"Consoles"** tab → **"Bash"**
   ```bash
   cd ~
   unzip telegram-addresser.zip -d telegram-addresser
   cd telegram-addresser
   ```

### Method 2: Clone from GitHub

```bash
# In Bash console
cd ~
git clone https://github.com/YOUR_USERNAME/telegram-addresser.git
cd telegram-addresser
git checkout main
```

---

## Configuration

### Step 1: Install Dependencies

```bash
# In Bash console
cd ~/telegram-addresser

# Create virtual environment
python3.10 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed telethon-1.36.0 pyTelegramBotAPI-4.14.0 ...
```

### Step 2: Upload config.json

**Option A: Upload via Files tab**

1. On your local computer, prepare `config.json`:
   ```json
   {
     "admin_bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
     "admin_user_ids": [123456789, 987654321],
     "workers": [
       {
         "worker_id": "worker_1",
         "api_id": 12345678,
         "api_hash": "abcdef1234567890abcdef1234567890",
         "session_name": "worker_1_session",
         "enabled": true,
         "channel_pairs": [
           {
             "source": -1001234567890,
             "target": -1009876543210,
             "enabled": true,
             "backfill_count": 10
           }
         ],
         "replacement_rules": [...],
         "filters": {...},
         "settings": {...}
       }
     ]
   }
   ```

2. In PythonAnywhere:
   - Click **"Files"** tab
   - Navigate to `/home/YOUR_USERNAME/telegram-addresser/`
   - Click **"Upload a file"**
   - Select your `config.json`

**Option B: Create in Bash console**

```bash
cd ~/telegram-addresser
nano config.json
# Paste your config
# Press Ctrl+X, then Y, then Enter to save
```

### Step 3: Verify Configuration

```bash
# Check if config is valid JSON
python3 -m json.tool config.json > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"

# View config (without sensitive data)
cat config.json | grep -E '"worker_id"|"session_name"|"source"|"target"'
```

---

## Worker Authentication

**⚠️ CRITICAL:** You MUST authenticate each worker BEFORE starting the bot!

### Step 1: Prepare

Make sure you have:
- ✅ Phone number with country code (e.g., `+1234567890`)
- ✅ Access to Telegram on your phone (for verification code)
- ✅ 2FA password (if enabled on your Telegram account)

### Step 2: Authenticate Worker

```bash
cd ~/telegram-addresser
source venv/bin/activate
python3 auth_worker.py
```

**Interactive prompts:**

```
🔐 Available workers:
1. worker_1 (session: worker_1_session)

Enter worker number or worker_id: 1

📱 Enter phone number (with country code, e.g., +1234567890): +421907123456

✉️ Verification code sent to your Telegram!
Enter the code: 12345

🔒 2FA enabled on this account
Enter your 2FA password: ********

✅ Authentication successful!
Session saved: worker_1_session.session
```

### Step 3: Verify Session Created

```bash
ls -lh *.session
# Should see: worker_1_session.session
```

**Repeat for each worker** if you have multiple workers in config.

### Common Issues During Authentication:

**Phone Number Invalid:**
```bash
# Must include country code
❌ 0907123456
✅ +421907123456
```

**Code Expired:**
```
# Request new code - restart auth_worker.py
python3 auth_worker.py
```

**2FA Password Wrong:**
```
# Check your Telegram settings
# Settings → Privacy and Security → Two-Step Verification
```

---

## Always-On Tasks Setup

**You need TWO always-on tasks:**
1. **Admin Bot** - For Telegram management
2. **Worker Manager** - For message forwarding

### Task 1: Admin Bot

**Purpose:** Allows you to manage the bot via Telegram commands

1. Go to **"Tasks"** tab in PythonAnywhere
2. Scroll to **"Always-on tasks"** section
3. Click **"Create a new always-on task"**
4. Fill in:

   **Description:**
   ```
   Telegram Admin Bot
   ```

   **Command:**
   ```bash
   cd /home/YOUR_USERNAME/telegram-addresser && source venv/bin/activate && python3 admin_bot.py
   ```
   
   ⚠️ **Replace `YOUR_USERNAME`** with your actual PythonAnywhere username!

5. **Enable:** ✅ Check the box
6. Click **"Create"**

**Expected result:** Task shows as "Running" with green checkmark

### Task 2: Worker Manager (Message Forwarder)

**Purpose:** Runs the actual message forwarding workers

1. Click **"Create a new always-on task"** again
2. Fill in:

   **Description:**
   ```
   Telegram Message Forwarder
   ```

   **Command:**
   ```bash
   cd /home/YOUR_USERNAME/telegram-addresser && source venv/bin/activate && python3 worker_manager.py
   ```
   
   ⚠️ **Replace `YOUR_USERNAME`** with your actual PythonAnywhere username!

3. **Enable:** ✅ Check the box
4. Click **"Create"**

**Expected result:** Task shows as "Running" with green checkmark

### Verify Both Tasks Running

1. Go to **"Tasks"** tab
2. Under **"Always-on tasks"**, you should see:
   ```
   ✅ Telegram Admin Bot (Running)
   ✅ Telegram Message Forwarder (Running)
   ```

### Test Admin Bot

1. Open Telegram on your phone
2. Search for your bot (@YourBotUsername)
3. Send: `/start`
4. **Expected:** Bot replies with menu buttons
5. **If no reply:** Check task logs (see Monitoring section)

---

## File Structure

### Complete File Layout on PythonAnywhere:

```
/home/YOUR_USERNAME/telegram-addresser/
├── admin_bot.py                 # Admin bot (Telegram interface)
├── admin_panel.py               # Web panel (not used on PA)
├── auth_worker.py               # Worker authentication script
├── bot.py                       # Main forwarder logic
├── worker_manager.py            # Worker process manager
├── config.json                  # ⚠️ YOUR CONFIGURATION
├── requirements.txt             # Python dependencies
├── README.md                    # Project documentation
│
├── src/                         # Source modules
│   ├── __init__.py
│   ├── config_manager.py
│   ├── text_processor.py
│   └── logger_setup.py
│
├── docs/                        # Documentation
│   ├── INDEX.md
│   ├── START_HERE.md
│   └── ... (many guides)
│
├── venv/                        # Virtual environment
│   ├── bin/
│   ├── lib/
│   └── ...
│
├── logs/                        # ✅ Auto-created
│   ├── forwarder.log
│   ├── worker_manager.log
│   └── worker_*.log
│
├── temp_media/                  # ✅ Auto-created (temp downloads)
│
├── *.session                    # ✅ Session files (DON'T DELETE!)
│   ├── worker_1_session.session
│   └── worker_1_session.session-journal
│
├── backfill_tracking.json       # ✅ Auto-created (backfill state)
├── last_processed.json          # ✅ Auto-created (last message IDs)
└── message_id_map.json          # ✅ Auto-created (deletion sync)
```

### Important Files:

| File | Purpose | Can Delete? |
|------|---------|-------------|
| `config.json` | Configuration | ❌ NO - Bot won't work |
| `*.session` | Telegram auth | ❌ NO - Must re-auth |
| `backfill_tracking.json` | Tracks backfilled pairs | ⚠️ Yes, but will re-backfill |
| `last_processed.json` | Last forwarded message | ⚠️ Yes, but will re-forward |
| `message_id_map.json` | Message ID mapping | ⚠️ Yes, but loses deletion sync |
| `logs/*.log` | Log files | ✅ Yes - Auto-recreated |
| `temp_media/*` | Temporary downloads | ✅ Yes - Auto-cleaned |
| `venv/` | Python environment | ⚠️ Yes, but must reinstall |

---

## Monitoring & Logs

### View Logs in Real-Time

**Method 1: Via Bash Console**

```bash
# Open Bash console
cd ~/telegram-addresser

# View forwarder logs
tail -f logs/forwarder.log

# View worker manager logs
tail -f logs/worker_manager.log

# View specific worker logs
tail -f logs/worker_worker_1.log

# Press Ctrl+C to stop
```

**Method 2: Via Files Tab**

1. Click **"Files"** tab
2. Navigate to `/home/YOUR_USERNAME/telegram-addresser/logs/`
3. Click on a log file to view
4. Click **"Reload"** to refresh

### Check Task Status

1. Go to **"Tasks"** tab
2. Under **"Always-on tasks"**, look for status:
   - ✅ **Running** (green) - All good!
   - ⏸️ **Stopped** (gray) - Task stopped
   - ❌ **Error** (red) - Check logs

3. Click task name to see:
   - Last output
   - Error messages
   - Restart history

### Check Process Status

```bash
# In Bash console
ps aux | grep python

# Look for:
python3 admin_bot.py        ← Admin bot running
python3 worker_manager.py   ← Worker manager running
```

### Monitor Forwarding Activity

**Watch for new messages:**
```bash
tail -f logs/forwarder.log | grep "LIVE ->"
```

**Watch for deletions:**
```bash
tail -f logs/forwarder.log | grep "🗑️"
```

**Watch for errors:**
```bash
tail -f logs/forwarder.log | grep -i error
```

### Check Message Counts

```bash
# Count forwarded messages today
grep "$(date +%Y-%m-%d)" logs/forwarder.log | grep "LIVE ->" | wc -l

# Last 10 forwarded messages
grep "LIVE ->" logs/forwarder.log | tail -10
```

---

## Troubleshooting

### 1. Task Shows "Error" Status

**Check task logs:**
1. Go to Tasks tab
2. Click on the failed task
3. Read error output

**Common errors:**

**"ModuleNotFoundError"**
```bash
# Reinstall dependencies
cd ~/telegram-addresser
source venv/bin/activate
pip install -r requirements.txt

# Restart task from Tasks tab
```

**"config.json not found"**
```bash
# Check if file exists
ls -la ~/telegram-addresser/config.json

# If missing, upload it via Files tab
```

**"Database is locked"**
```bash
# Stop BOTH tasks from Tasks tab
# Wait 2 minutes
# Delete journal files
cd ~/telegram-addresser
rm -f *.session-journal

# Start tasks again
```

### 2. Bot Not Responding in Telegram

**Check admin bot task:**
```bash
cd ~/telegram-addresser
tail -50 logs/forwarder.log
```

**Look for:**
```
Admin bot started successfully
Polling started...
```

**If not found:**
```bash
# Test admin bot manually
source venv/bin/activate
python3 admin_bot.py
# Press Ctrl+C after testing
```

### 3. Messages Not Forwarding

**Check worker manager logs:**
```bash
tail -100 logs/worker_manager.log
```

**Common issues:**

**"Worker X is dead"**
- Check session file exists: `ls -la *.session`
- Check channel IDs in config.json
- Verify bot is admin in channels

**"Cannot access channel"**
- Your account must be member of source channel
- Bot must be admin in target channel
- Check channel IDs are correct (negative numbers)

**"No channel pairs configured"**
- Check config.json → workers → channel_pairs
- At least one pair must have `"enabled": true`

### 4. AuthKeyDuplicatedError

**Cause:** Session used from two different locations

**Fix:**
```bash
# Stop both tasks from Tasks tab
# Wait 2-3 minutes

# Delete session files
cd ~/telegram-addresser
rm -f *.session*

# Re-authenticate
source venv/bin/activate
python3 auth_worker.py
# Follow prompts

# Start tasks from Tasks tab
```

### 5. Database Lock Loop

**Symptoms:**
```
database is locked
Worker restarting...
database is locked
Worker restarting...
(repeats forever)
```

**Fix:**
```bash
# Stop BOTH tasks
# Go to Tasks tab → Click "Stop" on both

# Wait 3 minutes (important!)

# Check no processes running
ps aux | grep python | grep telegram

# If processes found, note PIDs and kill
kill -9 <PID>

# Delete journal files
cd ~/telegram-addresser
rm -f *.session-journal

# Wait 1 more minute

# Start tasks again from Tasks tab
```

### 6. Task Stops After Few Hours

**Cause:** Free tier limitations

**Solution:** Upgrade to paid tier ($5/month minimum)

Free tier has:
- Limited CPU time
- Task auto-stop after certain runtime
- Not suitable for 24/7 operation

### 7. High CPU Usage Warning

**PythonAnywhere has CPU limits. If exceeded:**

**Reduce polling frequency:**
- Edit `bot.py` line ~315
- Change `await asyncio.sleep(5)` to `await asyncio.sleep(10)`
- Polls every 10 seconds instead of 5

**Reduce workers:**
- Disable some workers in config.json
- Set `"enabled": false` for unused workers

---

## Updates & Maintenance

### Update Bot Code

```bash
# Stop both tasks from Tasks tab first!

cd ~/telegram-addresser
source venv/bin/activate

# Backup config
cp config.json config.json.backup

# Pull latest code (if using Git)
git pull origin main

# Or upload new files via Files tab

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart tasks from Tasks tab
```

### Add New Worker

1. **Update config.json** via Files tab
2. **Authenticate new worker:**
   ```bash
   cd ~/telegram-addresser
   source venv/bin/activate
   python3 auth_worker.py
   # Choose new worker
   ```
3. **Restart worker manager task** from Tasks tab

### Change Channels

1. **Via Telegram admin bot:**
   - Send `/menu`
   - Manage Channels → Add/Remove pairs
   - No restart needed!

2. **Via config.json:**
   - Edit via Files tab
   - Restart worker manager task

### Backup Important Files

**What to backup regularly:**
```bash
# In Bash console
cd ~/telegram-addresser

# Create backup
tar -czf backup_$(date +%Y%m%d).tar.gz \
  config.json \
  *.session \
  backfill_tracking.json \
  last_processed.json \
  message_id_map.json

# Download via Files tab
# File will be in /home/YOUR_USERNAME/telegram-addresser/
```

### Clean Up Old Logs

```bash
cd ~/telegram-addresser/logs

# Delete logs older than 7 days
find . -name "*.log" -mtime +7 -delete

# Or keep only last 100 lines of each log
for log in *.log; do
  tail -100 "$log" > "$log.tmp"
  mv "$log.tmp" "$log"
done
```

---

## Best Practices

### ✅ DO:

1. **Use paid tier** ($5/month) for 24/7 reliability
2. **Monitor logs daily** - Quick check for errors
3. **Backup config.json** - Before any changes
4. **Test locally first** - Before deploying to PA
5. **Use unique session names** - One per worker
6. **Keep sessions on PA only** - Don't use from local
7. **Check task status daily** - Ensure green checkmarks
8. **Restart tasks monthly** - Prevents memory leaks
9. **Update dependencies quarterly** - Security patches
10. **Document your setup** - Save commands you used

### ❌ DON'T:

1. **Run from multiple locations** - Pick ONE (PA or local)
2. **Delete session files** - Unless re-authenticating
3. **Share config.json** - Contains sensitive credentials
4. **Create duplicate tasks** - Only TWO tasks needed
5. **Force-kill processes** - Use graceful shutdown
6. **Edit files while running** - Stop tasks first
7. **Use same session name twice** - Each worker needs unique
8. **Ignore error logs** - Check daily
9. **Skip backups** - One mistake = lost config
10. **Exceed CPU limits** - Monitor usage

### 🔒 Security:

1. **Keep credentials secret:**
   - Don't share config.json
   - Don't commit to public GitHub
   - Use .gitignore

2. **Use strong 2FA:**
   - Enable on Telegram account
   - Use password manager

3. **Limit admin users:**
   - Only trusted user IDs in config
   - Remove users who leave

4. **Monitor access:**
   - Check logs for suspicious activity
   - Watch for unauthorized channels

### 📊 Performance Tips:

1. **Optimize polling:**
   - Default: 5 seconds
   - High traffic: Keep 5s
   - Low traffic: 10-15s

2. **Limit backfill:**
   - Start with 10 messages
   - Increase if needed
   - Max recommended: 100

3. **Disable unused features:**
   - Set `backfill_count: 0` if not needed
   - Disable workers not in use

4. **Monitor CPU usage:**
   - Check Tasks tab for warnings
   - Reduce workers if hitting limits

---

## Quick Reference

### Essential Commands

```bash
# Navigate to project
cd ~/telegram-addresser

# Activate venv
source venv/bin/activate

# View logs
tail -f logs/forwarder.log
tail -f logs/worker_manager.log

# Check processes
ps aux | grep python

# Authenticate worker
python3 auth_worker.py

# Test admin bot
python3 admin_bot.py

# Test worker manager
python3 worker_manager.py
```

### File Locations

```
Project: /home/YOUR_USERNAME/telegram-addresser/
Config: /home/YOUR_USERNAME/telegram-addresser/config.json
Logs: /home/YOUR_USERNAME/telegram-addresser/logs/
Sessions: /home/YOUR_USERNAME/telegram-addresser/*.session
```

### Task Commands

```bash
# Always-on Task 1 (Admin Bot):
cd /home/YOUR_USERNAME/telegram-addresser && source venv/bin/activate && python3 admin_bot.py

# Always-on Task 2 (Worker Manager):
cd /home/YOUR_USERNAME/telegram-addresser && source venv/bin/activate && python3 worker_manager.py
```

### Useful Checks

```bash
# Config valid?
python3 -m json.tool config.json > /dev/null && echo "✅ Valid" || echo "❌ Invalid"

# Session exists?
ls -lh *.session

# Venv working?
source venv/bin/activate && python3 --version

# Dependencies installed?
pip list | grep telethon

# How many messages forwarded?
grep "LIVE ->" logs/forwarder.log | wc -l
```

---

## Summary Checklist

Before going live, verify:

- [ ] PythonAnywhere paid account active
- [ ] Project files uploaded
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `config.json` uploaded and valid
- [ ] All workers authenticated (`.session` files exist)
- [ ] Bot is admin in ALL target channels
- [ ] Account is member of ALL source channels
- [ ] Two Always-on tasks created and running
- [ ] Admin bot responds in Telegram (`/start`)
- [ ] Messages are being forwarded (check logs)
- [ ] No errors in logs for 10+ minutes
- [ ] Backups created (config + sessions)

**✅ If all checked, you're good to go!**

---

## 🆘 Getting Help

### If something's not working:

1. **Check logs first:**
   ```bash
   tail -100 logs/forwarder.log
   tail -100 logs/worker_manager.log
   ```

2. **Check this guide's Troubleshooting section**

3. **Check other documentation:**
   - `docs/TROUBLESHOOTING.md` - General issues
   - `docs/TROUBLESHOOTING_DATABASE_LOCK.md` - Lock errors
   - `docs/DELETION_SYNC_GUIDE.md` - Deletion sync

4. **Common fixes:**
   - Stop tasks → Wait 2 min → Restart
   - Delete `.session-journal` files
   - Re-authenticate workers
   - Verify config.json syntax

---

**🎉 Congratulations! Your bot is now running 24/7 on PythonAnywhere!**

Monitor it regularly and it will serve you reliably! 🚀

