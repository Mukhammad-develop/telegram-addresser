# 📁 Project Structure

This document explains the organized file structure of the Telegram Forwarder Bot.

## 📂 Directory Layout

```
telegram-addresser/
├── 📄 bot.py                    # Main bot application (entry point)
├── 📄 admin_panel.py            # Web admin interface (entry point)
├── 📄 config.json               # Active configuration
├── 📄 config.example.json       # Configuration template
├── 📄 requirements.txt          # Python dependencies
├── 📄 start.sh                  # Quick start script
├── 📄 .gitignore               # Git ignore rules
│
├── 📁 src/                      # Source code modules
│   ├── __init__.py             # Package initialization
│   ├── config_manager.py       # Configuration management
│   ├── text_processor.py       # Text replacement & filtering
│   └── logger_setup.py         # Logging system
│
├── 📁 docs/                     # Documentation
│   ├── START_HERE.md           # 👈 Read this first!
│   ├── QUICK_START.md          # 5-minute setup guide
│   ├── README.md               # Complete user manual
│   ├── DEPLOYMENT.md           # VPS deployment guide
│   ├── TROUBLESHOOTING.md      # Problem solving
│   ├── PROJECT_OVERVIEW.md     # Technical overview
│   └── PROJECT_STRUCTURE.md    # This file
│
├── 📁 logs/                     # Application logs
│   └── forwarder.log           # Main log file (auto-created)
│
└── 📁 systemd/                  # System service files
    └── telegram-forwarder.service  # Systemd service config
```

## 📄 File Descriptions

### Root Level (Entry Points & Config)

| File | Purpose | When to Edit |
|------|---------|--------------|
| `bot.py` | Main forwarder bot application | Only if extending functionality |
| `admin_panel.py` | Web-based configuration interface | Only if customizing UI |
| `config.json` | Your active configuration | Edit to add channels/rules |
| `config.example.json` | Template for new setups | Reference only |
| `requirements.txt` | Python package dependencies | When adding new libraries |
| `start.sh` | Quick start script | Rarely (already configured) |
| `.gitignore` | Git ignore patterns | When adding new file types |

### `src/` - Source Code Modules

| File | Purpose | Contains |
|------|---------|----------|
| `__init__.py` | Package initialization | Module exports |
| `config_manager.py` | Configuration management | ConfigManager class |
| `text_processor.py` | Text processing | TextProcessor class |
| `logger_setup.py` | Logging setup | Logger configuration |

**Why separate?**
- Keeps code organized
- Makes imports cleaner
- Easier to maintain
- Better for testing

### `docs/` - Documentation

| File | Purpose | Read When |
|------|---------|-----------|
| `START_HERE.md` | Quick orientation | First time setup |
| `QUICK_START.md` | 5-minute guide | Getting started |
| `README.md` | Complete manual | Learning all features |
| `DEPLOYMENT.md` | VPS deployment | Going to production |
| `TROUBLESHOOTING.md` | Problem solving | Having issues |
| `PROJECT_OVERVIEW.md` | Technical details | Understanding architecture |
| `PROJECT_STRUCTURE.md` | This file | Understanding layout |

### `logs/` - Application Logs

- Auto-created on first run
- Contains rotating log files
- Max 10MB per file, 5 backups
- Check here for debugging

### `systemd/` - System Service

- Service configuration for 24/7 operation
- Used when deploying to Linux server
- Enables auto-start on boot

## 🔄 Import Structure

### How imports work now:

**In bot.py and admin_panel.py:**
```python
from src.config_manager import ConfigManager
from src.text_processor import TextProcessor
from src.logger_setup import setup_logger
```

**Or alternatively:**
```python
from src import ConfigManager, TextProcessor, setup_logger
```

Both work thanks to `src/__init__.py`

## 📦 What Gets Generated

These files/directories are auto-created during operation:

```
├── logs/                        # Created on first run
│   ├── forwarder.log           # Current log
│   ├── forwarder.log.1         # Rotated log
│   └── ...                     # Up to 5 backups
│
├── *.session                    # Created after authentication
│   └── forwarder_session.session
│
└── __pycache__/                # Python cache (auto-generated)
    └── ...
```

**Don't commit these to git!** (Already in `.gitignore`)

## 🗂️ Configuration Files

### `config.json` - Main Configuration
- Your API credentials
- Channel pairs
- Replacement rules
- Filter settings
- Advanced settings

**Location:** Root directory  
**Edit with:** Text editor or admin panel  
**Backup:** Yes, regularly!

### `config.example.json` - Template
- Example configuration
- Shows all available options
- Use as reference

**Location:** Root directory  
**Edit with:** Don't edit, use as reference  
**Backup:** Not necessary

## 📝 Session Files

### `*.session` - Telegram Session
- Created after first authentication
- Contains encrypted session data
- Prevents re-authentication

**Location:** Root directory  
**Format:** SQLite database  
**Backup:** Yes! Important!  
**Share:** Never! Contains auth tokens

## 🔧 Working with the Structure

### Adding a new Python module

1. Create file in `src/`:
```bash
touch src/my_module.py
```

2. Add to `src/__init__.py`:
```python
from .my_module import MyClass

__all__ = [..., 'MyClass']
```

3. Import in bot.py:
```python
from src.my_module import MyClass
```

### Adding new documentation

1. Create `.md` file in `docs/`:
```bash
touch docs/MY_GUIDE.md
```

2. Reference it in other docs:
```markdown
See [MY_GUIDE.md](docs/MY_GUIDE.md)
```

### Adding new configuration options

1. Edit `src/config_manager.py` - add getter/setter
2. Edit `config.example.json` - add example
3. Update `docs/README.md` - document the option

## 🎯 Benefits of This Structure

### ✅ Clean Organization
- Clear separation of concerns
- Easy to find files
- Professional structure

### ✅ Better Maintainability
- Modules are isolated
- Documentation is centralized
- Configs are separate from code

### ✅ Easier Collaboration
- Clear file purposes
- Logical grouping
- Standard Python package layout

### ✅ Scalability
- Easy to add new modules
- Easy to add new docs
- Room for growth

## 🚀 Quick Navigation

### I want to...

**Configure channels**
→ Edit `config.json` or use `admin_panel.py`

**Read documentation**
→ Check `docs/` directory

**View logs**
→ Check `logs/forwarder.log`

**Modify bot behavior**
→ Edit `bot.py` (main logic)

**Change text processing**
→ Edit `src/text_processor.py`

**Adjust logging**
→ Edit `src/logger_setup.py`

**Deploy to server**
→ Use `systemd/telegram-forwarder.service`

## 📊 File Sizes (Approximate)

| Component | Lines | Size |
|-----------|-------|------|
| `bot.py` | ~300 | ~10KB |
| `admin_panel.py` | ~450 | ~17KB |
| `src/` modules | ~400 | ~15KB |
| Documentation | ~2700 | ~100KB |
| **Total** | **~3900** | **~150KB** |

## 🔒 Security Notes

### Files to protect:
- ✅ `config.json` - Contains API credentials
- ✅ `*.session` - Contains auth tokens
- ✅ `logs/` - May contain sensitive data

### Files safe to share:
- ✅ `.py` files (source code)
- ✅ `.md` files (documentation)
- ✅ `requirements.txt`
- ✅ `config.example.json` (no real credentials)

### Already protected by `.gitignore`:
- Session files
- Logs
- Config backups
- Python cache

## 📚 Further Reading

- **Understanding the code:** See `docs/PROJECT_OVERVIEW.md`
- **Using the bot:** See `docs/README.md`
- **Deploying to server:** See `docs/DEPLOYMENT.md`
- **Solving problems:** See `docs/TROUBLESHOOTING.md`

---

**This organized structure makes the project:**
- 📁 Easy to navigate
- 🔧 Simple to maintain
- 📚 Well documented
- 🚀 Ready to scale

Enjoy your clean, organized codebase! ✨

