# 🚀 Contabo VPS Deployment Guide

Step-by-step guide to deploy Telegram Forwarder Bot on Contabo VPS.

## 📋 VPS Information

- **Provider:** Contabo
- **Email:** tomassadko@gmail.com
- **Password:** VhuoT7S9mBfX
- **Login:** https://contabo.com

## 🔐 Step 1: Get VPS IP Address

1. Go to https://contabo.com
2. Login with: `tomassadko@gmail.com` / `VhuoT7S9mBfX`
3. Go to **VPS** section
4. Find your VPS server
5. **Copy the IP address** (e.g., `123.45.67.89`)

## 💻 Step 2: Connect to VPS via SSH

### On Windows:
1. Download **PuTTY** or use **Windows Terminal**
2. Open terminal/command prompt
3. Run:
```bash
ssh root@YOUR_VPS_IP
```
or if you have a username:
```bash
ssh username@YOUR_VPS_IP
```

### On Mac/Linux:
```bash
ssh root@YOUR_VPS_IP
```

**First time connection:** Type `yes` when asked to accept the fingerprint.

**Enter password:** The VPS root password (may be different from Contabo account password)

### ⚠️ SSH Password Issues?

If you get "Permission denied", try these solutions:

#### Solution 1: Get Root Password from Contabo Panel
1. Login to https://contabo.com
2. Go to **VPS** section
3. Click on your VPS server
4. Look for **"Root Password"** or **"Reset Password"** option
5. Contabo usually sends the root password via email when VPS is created
6. Check your email (tomassadko@gmail.com) for VPS setup email

#### Solution 2: Reset Root Password via Contabo Panel
1. Login to Contabo control panel
2. Go to **VPS** → Your server
3. Look for **"Reset Password"** or **"Change Root Password"** button
4. Set a new password
5. Wait 2-3 minutes for it to apply
6. Try SSH again with new password

#### Solution 3: Use VNC Access (If SSH doesn't work)
1. In Contabo panel, find **VNC** section
2. Click **"Open VNC Console"** or use VNC details:
   - **VNC Address:** `38.242.158.108:63101` (from your screenshot)
3. Connect via VNC client (TightVNC, RealVNC, or browser)
4. Login with root and password
5. Reset SSH password from inside the server:
   ```bash
   passwd root
   # Enter new password twice
   ```

#### Solution 4: Check if SSH is Enabled
Some Contabo VPS might have SSH disabled initially. Use VNC to enable it:
```bash
# Via VNC, login and run:
systemctl status ssh
# If disabled:
systemctl enable ssh
systemctl start ssh
```

## 📦 Step 3: Install Required Software

Once connected to VPS, run these commands:

```bash
# Update system
apt update && apt upgrade -y

# Install Python and Git
apt install -y python3 python3-pip python3-venv git

# Verify installation
python3 --version
git --version
```

## 📥 Step 4: Clone the Project

```bash
# Create a directory for projects
mkdir -p ~/projects
cd ~/projects

# Clone the repository
git clone https://github.com/Mukhammad-develop/telegram-addresser.git
cd telegram-addresser

# Switch to v0.6 branch
git checkout v0.6
```

## 🔧 Step 5: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Step 6: Configure the Bot

### Option A: Upload config.json from your computer

**On your local computer:**
```bash
# Use SCP to copy config.json to VPS
scp config.json root@YOUR_VPS_IP:~/projects/telegram-addresser/
```

**Or use SFTP client** (FileZilla, WinSCP):
- Host: `YOUR_VPS_IP`
- Username: `root`
- Password: `VhuoT7S9mBfX`
- Upload `config.json` to `/root/projects/telegram-addresser/`

### Option B: Create config.json on VPS

```bash
# Copy example config
cp config.example.json config.json

# Edit with nano
nano config.json
```

**Fill in:**
- `admin_bot_token`: Your Telegram bot token
- `admin_user_ids`: Your Telegram user ID
- `api_id` and `api_hash`: From https://my.telegram.org/apps
- `channel_pairs`: Your source → target channel pairs

**Save:** Press `Ctrl+X`, then `Y`, then `Enter`

## 🔐 Step 7: Authenticate Workers

For each worker in your config:

```bash
# Make sure you're in the project directory
cd ~/projects/telegram-addresser

# Activate virtual environment
source venv/bin/activate

# Authenticate worker_1
python3 auth_worker.py worker_1

# Follow prompts:
# 1. Enter phone number (with country code, e.g., +421907975101)
# 2. Enter verification code from Telegram
# 3. Enter 2FA password (if enabled)
```

**Repeat for each worker** if you have multiple workers.

## 🚀 Step 8: Test Run

```bash
# Make start.sh executable
chmod +x start.sh

# Test run (press Ctrl+C to stop)
./start.sh
```

**Check if workers start successfully!**

## 🔄 Step 9: Run as Background Service (24/7)

### Option A: Using screen (Simple)

```bash
# Install screen
apt install -y screen

# Start a screen session
screen -S telegram-bot

# Run the bot
cd ~/projects/telegram-addresser
source venv/bin/activate
./start.sh

# Detach from screen: Press Ctrl+A, then D
# Reattach later: screen -r telegram-bot
```

### Option B: Using systemd (Recommended for production)

```bash
# Copy systemd service file
cp systemd/telegram-forwarder.service /etc/systemd/system/

# Edit the service file
nano /etc/systemd/system/telegram-forwarder.service
```

**Update these paths in the service file:**
- `WorkingDirectory=/root/projects/telegram-addresser`
- `ExecStart=/root/projects/telegram-addresser/venv/bin/python3 /root/projects/telegram-addresser/worker_manager.py`
- `User=root` (or your username)

**Save and enable:**
```bash
# Reload systemd
systemctl daemon-reload

# Enable service (start on boot)
systemctl enable telegram-forwarder

# Start service
systemctl start telegram-forwarder

# Check status
systemctl status telegram-forwarder

# View logs
journalctl -u telegram-forwarder -f
```

## 📊 Step 10: Monitor the Bot

### Check if it's running:
```bash
# If using screen
screen -r telegram-bot

# If using systemd
systemctl status telegram-forwarder
journalctl -u telegram-forwarder -n 50
```

### View logs:
```bash
# Logs are in the project directory
cd ~/projects/telegram-addresser
tail -f logs/forwarder.log
```

## 🛠️ Useful Commands

### Stop the bot:
```bash
# If using screen
screen -r telegram-bot
# Press Ctrl+C

# If using systemd
systemctl stop telegram-forwarder
```

### Restart the bot:
```bash
# If using systemd
systemctl restart telegram-forwarder
```

### Update the bot:
```bash
cd ~/projects/telegram-addresser
git pull origin v0.6
source venv/bin/activate
pip install -r requirements.txt
systemctl restart telegram-forwarder
```

## 🔒 Security Notes

⚠️ **IMPORTANT:**
1. Change the default SSH password after first login
2. Use SSH keys instead of password authentication
3. Keep your `config.json` secure (contains API keys)
4. Don't share your VPS credentials publicly

## 🆘 Troubleshooting

### Bot not starting:
```bash
# Check logs
tail -f logs/forwarder.log

# Check if Python is correct version
python3 --version  # Should be 3.8+

# Check if dependencies installed
pip list | grep telethon
```

### Authentication fails:
```bash
# Delete old session and re-authenticate
rm -f *.session*
python3 auth_worker.py worker_1
```

### Can't access channels:
- Make sure your Telegram account is a member of all source channels
- Check channel IDs are correct (use @userinfobot)

## 📞 Support

If you encounter issues:
1. Check logs: `tail -f logs/forwarder.log`
2. Check systemd status: `systemctl status telegram-forwarder`
3. Share error messages for help

---

**🎉 Your bot is now running 24/7 on VPS!**

