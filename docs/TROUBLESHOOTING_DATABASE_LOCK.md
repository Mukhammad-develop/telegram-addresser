# Database Lock Error Troubleshooting

## Error: `sqlite3.OperationalError: database is locked`

### What This Means

This error occurs when Telethon's session file (`.session`) is locked by another process or a previous crash. The session file is a SQLite database that stores authentication and connection state.

### Common Causes

1. **Multiple processes using the same session file**
   - Running multiple bot instances with the same `session_name`
   - Multiple workers sharing the same session file in multi-worker mode

2. **Previous crash left the database locked**
   - Bot crashed without properly closing the database connection
   - System crash or forced termination

3. **Connection reset by peer**
   - Network issues causing abrupt disconnection
   - Server closing the connection unexpectedly

### Symptoms

- Worker crashes immediately after starting
- Error messages like:
  - `Cannot get difference since the account is likely misusing the session: database is locked`
  - `sqlite3.OperationalError: database is locked`
- Worker enters a crash loop (restarting repeatedly)
- Worker stops after 5 failed restart attempts

### Solutions

#### Immediate Fix (PythonAnywhere)

1. **Stop all running workers:**
   ```bash
   # In PythonAnywhere console, find and kill the process
   pkill -f worker_manager.py
   pkill -f bot.py
   ```

2. **Wait 1-2 minutes** for the database lock to automatically clear

3. **Check for duplicate processes:**
   ```bash
   ps aux | grep -E "(worker_manager|bot.py)"
   ```

4. **Restart the worker:**
   - Via admin bot: Use "🔄 Restart" button for the worker
   - Or manually restart the always-on task

#### Permanent Fix

**For Multi-Worker Mode:**

Ensure each worker has a **unique** `session_name` in `config.json`:

```json
{
  "workers": [
    {
      "worker_id": "worker_1",
      "session_name": "worker_1_session",  // ✅ Unique
      ...
    },
    {
      "worker_id": "worker_2",
      "session_name": "worker_2_session",  // ✅ Unique
      ...
    }
  ]
}
```

**Never use the same `session_name` for multiple workers!**

#### If Lock Persists

If the lock doesn't clear after waiting:

1. **Stop all processes:**
   ```bash
   pkill -f worker_manager.py
   pkill -f bot.py
   ```

2. **Wait 5 minutes** for SQLite to release the lock

3. **As a last resort, delete and re-authenticate:**
   ```bash
   # Backup the session file first!
   cp worker_1_session.session worker_1_session.session.backup
   
   # Delete the locked session
   rm worker_1_session.session
   rm worker_1_session.session-journal  # If exists
   
   # Re-authenticate via admin bot
   # Go to Workers → Worker Details → 🔐 Authenticate
   ```

### Prevention

The code now includes:

1. **Automatic lock detection** - Checks for locks before starting
2. **Retry logic** - Waits and retries if lock is detected
3. **Better error messages** - Clear instructions when lock is detected
4. **Longer wait time** - 30-second delay before restarting crashed workers

### Technical Details

- SQLite uses file-level locking on the session database
- Locks are automatically released when the process closes the connection
- If a process crashes, the lock may persist until SQLite's timeout (usually 5 seconds)
- Multiple processes cannot safely access the same SQLite database simultaneously

### Related Files

- `bot.py` - Contains lock detection and retry logic
- `worker_manager.py` - Handles worker restart logic with longer delays for lock issues
- `*.session` - SQLite database files (one per worker)

