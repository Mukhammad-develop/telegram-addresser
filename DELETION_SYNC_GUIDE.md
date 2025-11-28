# 🗑️ Message Deletion Synchronization

## ✅ Feature Overview

When a message is **deleted in the source channel**, the bot automatically **deletes the corresponding message in the target channel**.

This keeps your target channels in sync with source channels, removing posts that were deleted by the original channel admins.

---

## 🎯 How It Works

### 1. **Message Forwarding** (tracks mapping)
When the bot forwards/copies a message from source → target:
- Stores mapping: `source_channel:source_msg_id` → `target_channel:target_msg_id`
- Saves to `message_id_map.json` (persists across restarts)
- Includes timestamp for cleanup of old entries

### 2. **Message Deletion** (syncs deletion)
When a message is deleted in the source channel:
- Bot receives `MessageDeleted` event from Telegram
- Looks up the target message ID from the mapping
- Deletes the corresponding message in the target channel
- Removes the mapping entry (no longer needed)

---

## 📋 Example Flow

**Scenario:** Source channel admin deletes a post

```
1. Source channel: Message 12345 is deleted
2. Bot receives deletion event for message 12345
3. Bot checks message_id_map.json:
   "-1001234567890:12345" → {
     "target_id": -1009876543210,
     "target_msg_id": 67890,
     "timestamp": 1700000000
   }
4. Bot deletes message 67890 in target channel -1009876543210
5. Bot removes mapping from file
6. ✅ Deletion synced!
```

---

## 📁 Files Used

### `message_id_map.json`
Stores the mapping between source and target message IDs.

**Format:**
```json
{
  "-1001234567890:12345": {
    "target_id": -1009876543210,
    "target_msg_id": 67890,
    "timestamp": 1700000000.0
  },
  "-1001234567890:12346": {
    "target_id": -1009876543210,
    "target_msg_id": 67891,
    "timestamp": 1700000001.0
  }
}
```

- **Key:** `"source_channel_id:source_message_id"`
- **Value:** Object with `target_id`, `target_msg_id`, and `timestamp`

### Automatic Cleanup
- Keeps the latest **5000** message mappings
- When limit reached, deletes oldest **1000** entries
- Ensures file doesn't grow infinitely
- Older messages unlikely to be deleted anyway

---

## 🔧 Configuration

### ⚠️ **Important: Bot Permissions**

The bot MUST have **DELETE_MESSAGES** permission in target channels for this feature to work.

**How to grant permission:**
1. Add your bot account as **admin** to the target channel
2. In channel settings → Administrators → Your bot → Edit
3. Enable: ✅ **Delete messages**
4. Save

Without this permission, deletion events will be logged but deletions will fail.

---

## 📊 Log Examples

### Successful Deletion
```
🗑️  Detected deletion of 3 message(s) in -1001234567890
🗑️  ✅ Deleted message 67890 in -1009876543210 (source: 12345 from -1001234567890)
🗑️  ✅ Deleted message 67891 in -1009876543210 (source: 12346 from -1001234567890)
🗑️  ✅ Deleted message 67892 in -1009876543210 (source: 12347 from -1001234567890)
🗑️  Successfully synced 3/3 deletion(s)
```

### Failed Deletion (No Permission)
```
🗑️  Detected deletion of 1 message(s) in -1001234567890
🗑️  ❌ Failed to delete message 67890 in -1009876543210: ChatAdminRequiredError: You must be an admin to delete messages
```

### Message Not in Mapping
```
🗑️  Detected deletion of 1 message(s) in -1001234567890
🗑️  Message 99999 from -1001234567890 not found in mapping (may be older than map retention or never forwarded)
```

---

## 🚨 Edge Cases & Handling

### 1. **Message Already Deleted**
- Bot tries to delete but target message doesn't exist
- Logs warning, continues processing other deletions
- Removes mapping entry anyway

### 2. **No Delete Permission**
- Bot logs error: `ChatAdminRequiredError` or similar
- Does NOT retry (would fail again)
- Keeps mapping (in case permissions granted later)

### 3. **Message Not in Mapping**
- Source message was sent before bot started tracking
- Or message was filtered out (didn't forward)
- Or mapping was cleaned up (too old)
- Bot logs debug message, skips deletion

### 4. **Bot Restarted After Deletion**
- Mapping persists in `message_id_map.json`
- Deletion events received after restart still work
- No data loss from restarts

### 5. **Bulk Deletions**
- Source admin deletes 100 messages at once
- Bot receives all deletion IDs in one event
- Processes each deletion sequentially
- Logs summary: "Successfully synced X/Y deletion(s)"

---

## 🛠️ Troubleshooting

### Problem: Deletions not syncing

**Possible causes:**
1. **Bot doesn't have delete permission** in target channel
   - Fix: Add bot as admin with "Delete messages" permission
   
2. **Message not in mapping** (too old or never forwarded)
   - Check: `message_id_map.json` for the source message ID
   - If missing: Deletion can't be synced (mapping lost)
   
3. **Bot not receiving deletion events**
   - Check: Bot must be running (not stopped)
   - Check: Bot must be member of source channel
   - Check logs for "Detected deletion" messages

---

### Problem: `message_id_map.json` getting very large

**Cause:** Lots of messages being forwarded, file grows over time.

**Solution:** This is normal and handled automatically:
- Bot keeps only latest 5000 mappings
- Older mappings are cleaned up automatically
- File size typically stays under 500KB

**Manual cleanup (if needed):**
```bash
# Stop bot
./stop.sh

# Backup and clear mapping
cp message_id_map.json message_id_map.json.backup
echo '{}' > message_id_map.json

# Start bot
./start.sh
```

**Note:** After clearing, old messages can't be deletion-synced anymore.

---

### Problem: Bot deletes wrong messages

**This should NEVER happen** - the mapping is precise.

If it does:
1. Stop bot immediately: `./stop.sh`
2. Check `message_id_map.json` for corrupted data
3. Restore from backup if available
4. Report bug with logs

---

## 🔍 Monitoring

### Check Mapping File
```bash
cat message_id_map.json | python3 -m json.tool | head -50
```

Shows first 50 lines of formatted JSON.

### Count Mappings
```bash
cat message_id_map.json | python3 -c "import json, sys; print(len(json.load(sys.stdin)))"
```

Outputs number of message mappings stored.

### Watch Deletion Events (Real-time)
```bash
tail -f logs/forwarder.log | grep "🗑️"
```

Shows only deletion-related log lines.

### Find Specific Mapping
```bash
grep "12345" message_id_map.json
```

Searches for source message ID 12345.

---

## ⚙️ Advanced Configuration

### Disable Deletion Sync (Not Recommended)

If you want messages to stay in target even when deleted from source:

**Option 1:** Remove bot's delete permission in target channel
- Bot will try to delete but fail silently
- Logs will show permission errors

**Option 2:** Comment out event handler (code change)
- Edit `bot.py` line ~404
- Comment out the `@self.client.on(events.MessageDeleted())` registration
- Restart bot

---

## 🎯 Use Cases

### ✅ **Good Use Cases:**

1. **Mirroring Channels**
   - Keep target channel identical to source
   - Deletions should be reflected

2. **Compliance / Legal**
   - Content removed from source must be removed from copies
   - Automatic compliance with takedown requests

3. **Curated Content**
   - Admin reviews and deletes bad posts in source
   - Target stays clean automatically

### ⚠️ **Avoid If:**

1. **Archive Channel**
   - Want to keep all messages even if source deletes
   - Disable delete permission in target

2. **Selective Forwarding**
   - Already filtering messages heavily
   - Deletions may not apply to subset in target

---

## 📈 Performance

### Impact on Bot
- **CPU:** Minimal (<1% increase)
- **Memory:** ~1MB for 5000 mappings
- **Disk I/O:** Writes to file after each deletion
- **Network:** One API call per deleted message

### Scalability
- Handles bulk deletions (100+ at once) efficiently
- Processes deletions in parallel per target channel
- No performance degradation with large mapping files

---

## ✅ Best Practices

### ✅ DO:
- Grant bot delete permission in target channels
- Monitor logs for deletion sync confirmations
- Keep `message_id_map.json` backed up
- Let bot manage mapping cleanup automatically

### ❌ DON'T:
- Manually edit `message_id_map.json` (can corrupt data)
- Delete the mapping file unless intentional
- Grant delete permission if you want permanent archives
- Worry about file size (auto-cleanup handles it)

---

## 🔒 Security & Privacy

### Data Stored
- **What:** Source message IDs, target message IDs, channel IDs, timestamps
- **Where:** `message_id_map.json` (local file)
- **Sensitive:** Channel IDs are sensitive (don't share publicly)

### Permissions Required
- **Source Channel:** Read messages, read history
- **Target Channel:** Send messages, delete messages, read history
- **Bot Account:** Must be admin in target with delete permission

### Who Can Delete
- Source channel admins delete → Bot syncs to target
- Target channel admins can delete independently (won't affect source)
- Bot account can delete (it's admin in target)

---

## 🆘 Support

### Check Deletion Sync Status
```bash
# Recent deletions in logs
grep "🗑️" logs/forwarder.log | tail -20

# Count total mappings
cat message_id_map.json | python3 -c "import json, sys; print(len(json.load(sys.stdin)))"

# Check bot has delete permission
# Open Telegram → Target Channel → Administrators → Your Bot → Should see "Delete messages" ✅
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `ChatAdminRequiredError` | No delete permission | Add bot as admin with delete permission |
| `MessageIdInvalidError` | Message already deleted | Normal, ignore |
| `ChannelPrivateError` | Bot removed from channel | Re-add bot to channel |
| `not found in mapping` | Message too old or never forwarded | Normal, can't delete |

---

## 🎓 Summary

- ✅ **Automatic:** Deletions synced in real-time (within seconds)
- ✅ **Persistent:** Mapping survives bot restarts
- ✅ **Efficient:** Auto-cleanup prevents file bloat
- ✅ **Reliable:** Handles bulk deletions and edge cases
- ✅ **Permission-aware:** Gracefully handles permission errors
- ⚠️ **Requires:** Delete permission in target channels
- 📝 **Logged:** All deletion events logged for audit

**Result:** Target channels stay perfectly synced with source, including deletions! 🎉

