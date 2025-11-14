# 🚀 Deployment Guide - Telegram Forwarder Bot

This guide will help you deploy the Telegram Forwarder Bot on a VPS for 24/7 operation.

## 📋 Prerequisites

- A VPS or dedicated server (Ubuntu 20.04+ or Debian 10+ recommended)
- SSH access to your server
- At least 512MB RAM and 1GB disk space
- Python 3.8 or higher
- Telegram API credentials

## 🖥️ Recommended VPS Providers

- **DigitalOcean** - Starting at $4/month
- **Linode** - Starting at $5/month
- **Vultr** - Starting at $3.50/month
- **Hetzner** - Starting at €3.79/month
- **AWS Lightsail** - Starting at $3.50/month

## 📦 Step-by-Step Deployment

### Step 1: Set Up Your VPS

#### 1.1 Connect to your VPS

```bash
ssh root@YOUR_SERVER_IP
```

or with a specific user:
```bash
ssh username@YOUR_SERVER_IP
```

#### 1.2 Update system packages

```bash
sudo apt update && sudo apt upgrade -y
```

#### 1.3 Install required system packages

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

#### 1.4 Create a dedicated user (recommended)

```bash
sudo adduser telegram-bot
sudo usermod -aG sudo telegram-bot
sudo su - telegram-bot
```

### Step 2: Download and Install the Bot

#### 2.1 Upload files to server

**Option A: Using SCP (from your local machine)**

```bash
# Navigate to where your files are locally
cd /path/to/telegram-addresser

# Upload to server
scp -r * username@YOUR_SERVER_IP:/home/telegram-bot/telegram-forwarder/
```

**Option B: Using Git**

```bash
# If you have it in a Git repository
cd /home/telegram-bot
git clone YOUR_REPOSITORY_URL telegram-forwarder
cd telegram-forwarder
```

**Option C: Using SFTP**

Use an SFTP client like FileZilla to upload all files.

#### 2.2 Set up Python environment

```bash
cd /home/telegram-bot/telegram-forwarder

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure the Bot

#### 3.1 Edit configuration file

```bash
nano config.json
```

Update with your settings:
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
  ]
}
```

Save with `Ctrl+X`, then `Y`, then `Enter`.

### Step 4: First-Time Authentication

#### 4.1 Run the bot for the first time

```bash
source venv/bin/activate
python bot.py
```

#### 4.2 Complete authentication

You'll be prompted to:
1. Enter your phone number (with country code, e.g., +1234567890)
2. Enter the verification code sent to your Telegram
3. Enter 2FA password if enabled

After successful authentication, press `Ctrl+C` to stop.

#### 4.3 Verify session file was created

```bash
ls -la | grep session
```

You should see `forwarder_session.session` file.

### Step 5: Set Up as a System Service

#### 5.1 Create log directory

```bash
sudo mkdir -p /var/log/telegram-forwarder
sudo chown telegram-bot:telegram-bot /var/log/telegram-forwarder
```

#### 5.2 Edit the systemd service file

```bash
nano systemd/telegram-forwarder.service
```

Update the following fields:
- Replace `YOUR_USERNAME` with your actual username (e.g., `telegram-bot`)
- Replace `/path/to/telegram-addresser` with actual path (e.g., `/home/telegram-bot/telegram-forwarder`)

Example:
```ini
[Unit]
Description=Telegram Multi-Channel Forwarder Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=telegram-bot
WorkingDirectory=/home/telegram-bot/telegram-forwarder
Environment="PATH=/home/telegram-bot/telegram-forwarder/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/telegram-bot/telegram-forwarder/venv/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/telegram-forwarder/output.log
StandardError=append:/var/log/telegram-forwarder/error.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### 5.3 Install the service

```bash
sudo cp systemd/telegram-forwarder.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-forwarder
```

#### 5.4 Start the service

```bash
sudo systemctl start telegram-forwarder
```

#### 5.5 Check status

```bash
sudo systemctl status telegram-forwarder
```

You should see "active (running)" in green.

### Step 6: Verify It's Working

#### 6.1 Check logs

```bash
# Bot logs
tail -f logs/forwarder.log

# System logs
sudo journalctl -u telegram-forwarder -f

# Output logs
tail -f /var/log/telegram-forwarder/output.log
```

#### 6.2 Send a test message

Send a message to one of your source channels and verify it gets forwarded.

## 🎛️ Optional: Set Up Admin Panel

### Option 1: Local Access Only (Recommended)

```bash
# Run admin panel
source venv/bin/activate
python admin_panel.py
```

Access via SSH tunnel from your local machine:
```bash
# On your local machine
ssh -L 5000:localhost:5000 username@YOUR_SERVER_IP
```

Then open http://localhost:5000 in your browser.

### Option 2: Public Access (Less Secure)

⚠️ **Warning**: Only do this if you understand the security implications!

```bash
# Edit admin_panel.py to listen on all interfaces
nano admin_panel.py
```

Change the last line to:
```python
run_admin_panel(host='0.0.0.0', port=5000)
```

Set up firewall:
```bash
sudo ufw allow 5000/tcp
```

Access via http://YOUR_SERVER_IP:5000

**Better Option**: Use nginx as reverse proxy with SSL and authentication.

## 🛠️ Service Management Commands

### Check status
```bash
sudo systemctl status telegram-forwarder
```

### Stop the bot
```bash
sudo systemctl stop telegram-forwarder
```

### Start the bot
```bash
sudo systemctl start telegram-forwarder
```

### Restart the bot
```bash
sudo systemctl restart telegram-forwarder
```

### View logs (live)
```bash
sudo journalctl -u telegram-forwarder -f
```

### View logs (last 100 lines)
```bash
sudo journalctl -u telegram-forwarder -n 100
```

### Disable auto-start
```bash
sudo systemctl disable telegram-forwarder
```

### Enable auto-start
```bash
sudo systemctl enable telegram-forwarder
```

## 📊 Monitoring

### Check if bot is running

```bash
ps aux | grep bot.py
```

### Monitor resource usage

```bash
htop
```

or

```bash
top
```

### Check disk space

```bash
df -h
```

### View log sizes

```bash
du -sh logs/
du -sh /var/log/telegram-forwarder/
```

## 🔄 Updating the Bot

### 1. Stop the service

```bash
sudo systemctl stop telegram-forwarder
```

### 2. Backup configuration

```bash
cp config.json config.json.backup
cp forwarder_session.session forwarder_session.session.backup
```

### 3. Update files

Upload new files via SCP or Git pull:

```bash
# If using Git
git pull origin main

# If using SCP, upload from local machine
scp -r * username@YOUR_SERVER_IP:/home/telegram-bot/telegram-forwarder/
```

### 4. Update dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### 5. Restore configuration

```bash
cp config.json.backup config.json
```

### 6. Restart service

```bash
sudo systemctl start telegram-forwarder
sudo systemctl status telegram-forwarder
```

## 🔒 Security Best Practices

### 1. Set up firewall

```bash
# Install UFW
sudo apt install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### 2. Secure SSH

Edit SSH config:
```bash
sudo nano /etc/ssh/sshd_config
```

Recommended settings:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Restart SSH:
```bash
sudo systemctl restart sshd
```

### 3. Set proper file permissions

```bash
chmod 600 config.json
chmod 600 *.session
chmod 700 logs/
```

### 4. Enable automatic security updates

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 5. Set up fail2ban

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 🚨 Troubleshooting

### Bot keeps restarting

Check logs:
```bash
sudo journalctl -u telegram-forwarder -n 100
```

Common issues:
- Wrong API credentials
- Missing permissions in channels
- Python dependencies not installed

### Out of memory

Check memory usage:
```bash
free -h
```

Add swap if needed:
```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Can't connect to channels

- Verify channel IDs are correct
- Check if account has access to channels
- Look for `ChannelPrivateError` in logs

### Session expired

If you see authentication errors:
1. Stop the bot
2. Delete the session file: `rm forwarder_session.session`
3. Run `python bot.py` manually to re-authenticate
4. Restart the service

### Disk space full

Clean up old logs:
```bash
# Rotate logs manually
sudo logrotate /etc/logrotate.conf --force

# Or delete old logs
rm logs/forwarder.log.*
```

## 📈 Performance Optimization

### For heavy traffic (100+ messages/minute)

1. **Increase log rotation frequency**

Edit `logger_setup.py`:
```python
max_bytes=5 * 1024 * 1024  # 5MB instead of 10MB
backup_count=10  # More backup files
```

2. **Adjust retry settings**

In `config.json`:
```json
{
  "settings": {
    "retry_attempts": 3,
    "retry_delay": 3,
    "flood_wait_extra_delay": 5
  }
}
```

3. **Disable backfill for busy channels**

```json
{
  "channel_pairs": [
    {
      "backfill_count": 0
    }
  ]
}
```

## 🔄 Backup Strategy

### Automated backup script

Create `/home/telegram-bot/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/telegram-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup config and session
cp /home/telegram-bot/telegram-forwarder/config.json $BACKUP_DIR/config_$DATE.json
cp /home/telegram-bot/telegram-forwarder/*.session $BACKUP_DIR/session_$DATE.session

# Keep only last 7 days
find $BACKUP_DIR -name "*.json" -mtime +7 -delete
find $BACKUP_DIR -name "*.session" -mtime +7 -delete
```

Make executable:
```bash
chmod +x /home/telegram-bot/backup.sh
```

Add to crontab:
```bash
crontab -e
```

Add line:
```
0 2 * * * /home/telegram-bot/backup.sh
```

## ✅ Deployment Checklist

- [ ] VPS purchased and accessible via SSH
- [ ] System packages updated
- [ ] Python 3.8+ installed
- [ ] Bot files uploaded
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] config.json configured with correct credentials
- [ ] First-time authentication completed
- [ ] Session file created and backed up
- [ ] Systemd service configured and installed
- [ ] Service started and enabled
- [ ] Logs verified - bot running successfully
- [ ] Test message forwarded successfully
- [ ] Firewall configured
- [ ] SSH secured
- [ ] Backup strategy implemented
- [ ] Monitoring set up

## 📞 Post-Deployment

After successful deployment:

1. **Monitor for 24 hours** - Check logs regularly
2. **Test all channel pairs** - Send test messages to each source
3. **Verify replacement rules** - Ensure text is being modified correctly
4. **Test filters** - Confirm filtering works as expected
5. **Document your setup** - Note any custom configurations
6. **Share credentials securely** - If working with a team

## 🎉 Success!

Your bot is now running 24/7! It will:
- Auto-start on server reboot
- Auto-restart on crashes
- Handle rate limits automatically
- Log all activity
- Forward messages in real-time

For any issues, check logs first:
```bash
tail -f logs/forwarder.log
sudo journalctl -u telegram-forwarder -f
```

---

**Need help? Check the main README.md for troubleshooting tips.**

