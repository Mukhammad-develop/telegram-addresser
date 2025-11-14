# 🔧 Troubleshooting Guide

Common issues and their solutions for the Telegram Forwarder Bot.

## 🚨 Common Issues

### 1. Bot Won't Start

#### Symptom
```
ValueError: API credentials not configured
```

**Solution:**
- Open `config.json`
- Ensure `api_id` is a number (not 0)
- Ensure `api_hash` is filled in (not empty string)
- Get credentials from https://my.telegram.org

#### Symptom
```
ModuleNotFoundError: No module named 'telethon'
```

**Solution:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Authentication Issues

#### Symptom
```
SessionPasswordNeededError
```

**Solution:**
- Your account has 2FA enabled
- Enter your 2FA password when prompted
- Password is not stored, only session file is created

#### Symptom
```
PhoneNumberInvalidError
```

**Solution:**
- Phone number must include country code
- Format: +1234567890 (no spaces or dashes)
- Example: +1234567890, not 123-456-7890

#### Symptom
```
FloodWaitError: A wait of X seconds is required
```

**Solution:**
- Telegram is rate limiting your account
- Bot will automatically wait and retry
- This is normal for new accounts or high traffic
- Be patient, bot handles this automatically

### 3. Forwarding Issues

#### Symptom
Messages not being forwarded

**Checklist:**
1. Check channel IDs are correct (negative numbers)
2. Verify bot account is member of source channel
3. Check if channel pair is enabled in config
4. Review filter settings (might be blocking messages)
5. Check logs: `tail -f logs/forwarder.log`

#### Symptom
```
ChannelPrivateError
```

**Solution:**
- Bot account is not a member of the channel
- Join the channel with your account
- For private channels, you must be invited

#### Symptom
```
ChatWriteForbiddenError
```

**Solution:**
- Bot account doesn't have permission to post in target channel
- Make bot account an admin in target channel
- Or enable posting permissions for all members

### 4. Permission Errors

#### Symptom
```
MessageIdInvalidError
```

**Solution:**
- Message was deleted before forwarding
- Or message ID doesn't exist
- Bot will skip and continue with next message

#### Symptom
Can't forward from specific channel

**Possible causes:**
1. Channel has forwarding disabled
2. You're not a member
3. Channel is private and you lost access
4. Channel was deleted

**Solution:**
- Verify access to channel manually
- Check channel settings
- Update channel pair in config if channel ID changed

### 5. Configuration Issues

#### Symptom
Changes to config.json not taking effect

**Solution:**
```bash
# Restart the bot
sudo systemctl restart telegram-forwarder

# Or if running manually, press Ctrl+C and restart
python bot.py
```

#### Symptom
Admin panel changes not showing in bot

**Solution:**
- Admin panel saves to config.json
- Restart bot to load new configuration
- Check if config.json was actually updated

### 6. Service/Daemon Issues

#### Symptom
```
sudo systemctl status telegram-forwarder
Failed to start telegram-forwarder.service
```

**Solution:**
```bash
# Check for errors
sudo journalctl -u telegram-forwarder -n 50

# Common issues:
# 1. Wrong paths in service file
sudo nano /etc/systemd/system/telegram-forwarder.service

# 2. Wrong permissions
sudo chown -R telegram-bot:telegram-bot /home/telegram-bot/telegram-forwarder

# 3. Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart telegram-forwarder
```

#### Symptom
Service keeps restarting

**Solution:**
```bash
# Check what's causing crashes
sudo journalctl -u telegram-forwarder -f

# Common causes:
# - Wrong Python path in service file
# - Missing dependencies
# - Invalid config.json syntax
# - Session file deleted
```

### 7. Performance Issues

#### Symptom
Bot is slow or lagging

**Check system resources:**
```bash
# Check CPU and memory
htop

# Check disk space
df -h

# Check if bot is running
ps aux | grep bot.py
```

**Solutions:**
1. **High memory usage:**
   ```bash
   # Add swap space
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

2. **High CPU usage:**
   - Reduce backfill_count in config
   - Check for error loops in logs
   - Ensure no duplicate instances running

3. **Disk full:**
   ```bash
   # Clean old logs
   rm logs/forwarder.log.*
   sudo journalctl --vacuum-time=7d
   ```

### 8. Text Replacement Not Working

#### Symptom
Text not being replaced as configured

**Checklist:**
1. Check spelling of find/replace terms
2. Verify case_sensitive setting
3. Make sure bot is restarted after config change
4. Check if text is in caption vs message text

**Debug:**
Add debug logging:
```json
{
  "settings": {
    "log_level": "DEBUG"
  }
}
```

Then check logs to see what text bot is processing.

### 9. Filter Issues

#### Symptom
All messages being filtered out

**If using whitelist:**
- Message must contain at least ONE keyword
- Check keyword spelling
- Keywords are case-insensitive by default

**If using blacklist:**
- Message will be blocked if it contains ANY keyword
- Check if keywords are too broad

**Debug filters:**
```json
{
  "filters": {
    "enabled": false
  }
}
```

Disable filters temporarily to confirm that's the issue.

### 10. Log Files Issues

#### Symptom
Log files too large

**Solution:**
```bash
# Current log rotation is 10MB per file, 5 backups
# To change, edit logger_setup.py

# Or manually clean
rm logs/forwarder.log.*

# Set up log rotation with logrotate
sudo nano /etc/logrotate.d/telegram-forwarder
```

Add:
```
/home/telegram-bot/telegram-forwarder/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 telegram-bot telegram-bot
}
```

#### Symptom
Can't find logs

**Default locations:**
- Application logs: `logs/forwarder.log`
- System logs: `sudo journalctl -u telegram-forwarder`
- Service output: `/var/log/telegram-forwarder/output.log`
- Service errors: `/var/log/telegram-forwarder/error.log`

### 11. Media/Album Issues

#### Symptom
Media groups sent as separate messages

**Note:** The current bot uses simple forwarding which preserves the original format. If albums are being split:
1. This might be a Telegram API behavior
2. Check if source message was actually an album
3. Review logs for any errors during forwarding

### 12. Network/Connection Issues

#### Symptom
```
ConnectionError / TimeoutError
```

**Solution:**
```bash
# Check internet connection
ping telegram.org

# Check if Telegram is accessible
curl https://api.telegram.org

# Restart network (if on VPS)
sudo systemctl restart networking
```

#### Symptom
Bot disconnects frequently

**Solutions:**
1. Check VPS network stability
2. Increase timeout in code if needed
3. Check firewall rules
4. Verify VPS provider isn't blocking Telegram

### 13. Backfill Issues

#### Symptom
Backfill not working

**Checklist:**
1. Check `backfill_count` is > 0
2. Verify channel has messages to backfill
3. Check logs for errors during backfill
4. Ensure bot has access to message history

#### Symptom
Duplicate messages on restart

**Explanation:**
- Backfill runs every time bot starts
- This is intentional to catch missed messages
- Set `backfill_count: 0` to disable

## 🔍 Diagnostic Commands

### Check if bot is running
```bash
ps aux | grep bot.py
sudo systemctl status telegram-forwarder
```

### View logs in real-time
```bash
tail -f logs/forwarder.log
sudo journalctl -u telegram-forwarder -f
```

### View recent errors only
```bash
grep -i error logs/forwarder.log | tail -20
sudo journalctl -u telegram-forwarder | grep -i error | tail -20
```

### Check configuration syntax
```bash
python3 -c "import json; print(json.load(open('config.json')))"
```

### Test Python imports
```bash
source venv/bin/activate
python3 -c "from telethon import TelegramClient; print('OK')"
```

### Check file permissions
```bash
ls -la config.json
ls -la *.session
ls -la logs/
```

### Monitor network connections
```bash
sudo netstat -tulpn | grep python
```

## 🆘 Emergency Procedures

### Bot is misbehaving - stop it immediately
```bash
sudo systemctl stop telegram-forwarder
pkill -9 -f bot.py
```

### Reset session (will require re-authentication)
```bash
sudo systemctl stop telegram-forwarder
rm *.session
python bot.py  # Authenticate again
sudo systemctl start telegram-forwarder
```

### Completely reset configuration
```bash
sudo systemctl stop telegram-forwarder
cp config.json config.json.emergency_backup
# Edit config.json to reset settings
sudo systemctl start telegram-forwarder
```

### Roll back to previous version
```bash
sudo systemctl stop telegram-forwarder
# Restore from backup
cp ~/backups/config_YYYYMMDD.json config.json
cp ~/backups/session_YYYYMMDD.session forwarder_session.session
sudo systemctl start telegram-forwarder
```

## 📊 Monitoring & Health Checks

### Create a health check script

Create `health_check.sh`:
```bash
#!/bin/bash

echo "=== Telegram Forwarder Health Check ==="
echo ""

# Check if service is running
if systemctl is-active --quiet telegram-forwarder; then
    echo "✅ Service: Running"
else
    echo "❌ Service: Not running"
fi

# Check process
if pgrep -f "bot.py" > /dev/null; then
    echo "✅ Process: Active"
else
    echo "❌ Process: Not found"
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "✅ Disk: ${DISK_USAGE}% used"
else
    echo "⚠️  Disk: ${DISK_USAGE}% used (high)"
fi

# Check memory
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2*100}')
echo "📊 Memory: ${MEM_USAGE}% used"

# Check log size
LOG_SIZE=$(du -sh logs/ 2>/dev/null | awk '{print $1}')
echo "📝 Log size: ${LOG_SIZE}"

# Check recent errors
ERROR_COUNT=$(grep -i error logs/forwarder.log 2>/dev/null | tail -100 | wc -l)
echo "⚠️  Recent errors (last 100 lines): ${ERROR_COUNT}"

echo ""
echo "Last 5 log entries:"
tail -5 logs/forwarder.log 2>/dev/null || echo "No logs found"
```

Run it:
```bash
chmod +x health_check.sh
./health_check.sh
```

## 📞 Still Need Help?

1. **Check logs first:**
   ```bash
   tail -100 logs/forwarder.log
   ```

2. **Verify configuration:**
   ```bash
   cat config.json
   ```

3. **Test manually:**
   ```bash
   source venv/bin/activate
   python bot.py
   ```
   Watch output for errors

4. **Search logs for specific errors:**
   ```bash
   grep -i "error\|exception\|failed" logs/forwarder.log | tail -20
   ```

5. **Enable debug logging:**
   ```json
   {
     "settings": {
       "log_level": "DEBUG"
     }
   }
   ```

---

**Most issues are related to:**
- ❌ Wrong API credentials
- ❌ Channel access permissions
- ❌ Configuration syntax errors
- ❌ Missing dependencies
- ❌ Wrong file paths in systemd service

**Always check logs first!** They contain detailed information about what went wrong.

