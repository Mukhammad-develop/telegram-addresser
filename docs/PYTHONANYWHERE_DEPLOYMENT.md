# 🚀 PythonAnywhere Deployment Guide

Step-by-step guide to deploy Telegram Forwarder Bot on PythonAnywhere.

## 📋 Prerequisites

- PythonAnywhere account (Free tier works, but **Paid tier recommended** for 24/7 operation)
- Telegram API credentials
- Admin bot token

> ⚠️ **Important:** Free tier has limitations:
> - Tasks can only run for a few hours
> - Limited CPU time
> - **Paid tier ($5/month)** recommended for 24/7 operation

## 🔐 Step 1: Create PythonAnywhere Account

1. Go to https://www.pythonanywhere.com
2. Sign up for an account (or login if you have one)
3. Choose **Beginner** or **Hacker** plan (Hacker recommended)

## 💻 Step 2: Access Bash Console

1. Login to PythonAnywhere dashboard
2. Click **"Consoles"** tab in the top menu
3. Click **"Bash"** to open a new console
4. You'll see a terminal prompt like: `username@username:~$`

## 📦 Step 3: Install Git and Clone Repository

```bash
# Update package list
sudo apt-get update

# Install git (if not already installed)
sudo apt-get install -y git

# Navigate to your home directory
cd ~

# Clone the repository
git clone https://github.com/Mukhammad-develop/telegram-addresser.git

# Navigate into project directory
cd telegram-addresser

# Switch to main branch
git checkout main
```

## 🐍 Step 4: Set Up Python Environment

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

> **Note:** PythonAnywhere uses Python 3.10 by default. If you need a different version, use `python3.9` or `python3.11` instead.

## ⚙️ Step 5: Configure the Bot

### Option A: Upload config.json via Files Tab

1. In PythonAnywhere dashboard, click **"Files"** tab
2. Navigate to: `/home/yourusername/telegram-addresser/`
3. Click **"Upload a file"**
4. Upload your `config.json` file

### Option B: Create config.json in Console

```bash
# Make sure you're in project directory
cd ~/telegram-addresser

# Copy example config
cp config.example.json config.json

# Edit config.json (use nano editor)
nano config.json
```

**Fill in your credentials:**
- `admin_bot_token`: Your Telegram bot token
- `admin_user_ids`: Your Telegram user ID
- `api_id` and `api_hash`: From https://my.telegram.org/apps
- `channel_pairs`: Your source → target channel pairs

**Save:** Press `Ctrl+X`, then `Y`, then `Enter`

## 🔐 Step 6: Authenticate Workers

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Authenticate worker_1
python3 auth_worker.py worker_1

# Follow prompts:
# 1. Enter phone number (with country code, e.g., +421907975101)
# 2. Enter verification code from Telegram
# 3. Enter 2FA password (if enabled)
```

**Repeat for each worker** if you have multiple workers.

## 🚀 Step 7: Test Run

```bash
# Make start.sh executable
chmod +x start.sh

# Test run (this will run in foreground)
./start.sh
```

**Check if workers start successfully!** Press `Ctrl+C` to stop.

## ⏰ Step 8: Set Up Scheduled Task (24/7 Operation)

PythonAnywhere uses **Scheduled Tasks** for long-running processes.

### Method 1: Using Scheduled Task (Recommended)

1. In PythonAnywhere dashboard, click **"Tasks"** tab
2. Click **"Create a new task"**
3. Fill in:
   - **Command:**
     ```bash
     cd /home/yourusername/telegram-addresser && source venv/bin/activate && python3 worker_manager.py
     ```
   - **Hour:** `*` (every hour)
   - **Minute:** `0` (at minute 0)
   - **Enabled:** ✅ Check this box
4. Click **"Create"**

> ⚠️ **Note:** This will restart the bot every hour. For continuous operation, use Method 2.

### Method 2: Using Always-On Task (Paid Tier Only)

1. In PythonAnywhere dashboard, click **"Tasks"** tab
2. Click **"Create a new always-on task"**
3. Fill in:
   - **Command:**
     ```bash
     cd /home/yourusername/telegram-addresser && source venv/bin/activate && python3 worker_manager.py
     ```
   - **Enabled:** ✅ Check this box
4. Click **"Create"**

This will keep the bot running 24/7 without restarting.

### Method 3: Using Web App (Alternative)

1. Click **"Web"** tab
2. Click **"Add a new web app"**
3. Choose **Flask** or **Manual configuration**
4. Set **Source code:** `/home/yourusername/telegram-addresser`
5. Set **Working directory:** `/home/yourusername/telegram-addresser`
6. In **WSGI configuration file**, add:
   ```python
   import sys
   path = '/home/yourusername/telegram-addresser'
   if path not in sys.path:
       sys.path.append(path)
   
   # Start the bot
   import subprocess
   subprocess.Popen(['bash', '-c', 'cd /home/yourusername/telegram-addresser && source venv/bin/activate && python3 worker_manager.py'])
   ```

## 📊 Step 9: Monitor the Bot

### View Logs

```bash
# In console, navigate to project directory
cd ~/telegram-addresser

# View logs
tail -f logs/forwarder.log
```

### Check Task Status

1. Go to **"Tasks"** tab
2. Check if your task is **"Running"** (green) or **"Error"** (red)
3. Click on task to see output/logs

### Check Console Output

1. Go to **"Consoles"** tab
2. Click on your console to see real-time output

## 🛠️ Useful Commands

### Stop the bot:
```bash
# Find and kill the process
ps aux | grep worker_manager.py
kill <PID>
```

### Restart the bot:
1. Go to **"Tasks"** tab
2. Click **"Reload"** on your task

### Update the bot:
```bash
cd ~/telegram-addresser
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# Then reload task in Tasks tab
```

### View running processes:
```bash
ps aux | grep python
```

## 🔒 Security Notes

⚠️ **IMPORTANT:**
1. Keep your `config.json` secure (contains API keys)
2. Don't share your PythonAnywhere credentials
3. Use environment variables for sensitive data (optional)

## 🆘 Troubleshooting

### Bot not starting:
```bash
# Check logs
tail -f logs/forwarder.log

# Check Python version
python3 --version

# Check if dependencies installed
pip list | grep telethon
```

### Task keeps stopping:
- **Free tier:** Tasks stop after a few hours. Upgrade to paid tier for 24/7.
- **Check logs:** Look for errors in task output
- **Check CPU time:** Free tier has limited CPU time

### Authentication fails:
```bash
# Delete old session and re-authenticate
rm -f *.session*
source venv/bin/activate
python3 auth_worker.py worker_1
```

### Can't access channels:
- Make sure your Telegram account is a member of all source channels
- Check channel IDs are correct (use @userinfobot)

## 📝 Quick Reference

### Project Location:
```
/home/yourusername/telegram-addresser/
```

### Virtual Environment:
```
/home/yourusername/telegram-addresser/venv/
```

### Logs:
```
/home/yourusername/telegram-addresser/logs/forwarder.log
```

### Start Command:
```bash
cd /home/yourusername/telegram-addresser && source venv/bin/activate && python3 worker_manager.py
```

## 💡 Tips

1. **Use paid tier** ($5/month) for reliable 24/7 operation
2. **Monitor logs regularly** to catch errors early
3. **Set up email alerts** in PythonAnywhere for task failures
4. **Keep backups** of your config.json
5. **Test in console first** before setting up scheduled task

---

**🎉 Your bot is now running on PythonAnywhere!**

