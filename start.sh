#!/bin/bash
# Unified Start Script - Auto-detects single or multi-worker mode

set -e

echo "🚀 Telegram Forwarder Bot"
echo "=========================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment found"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import telethon" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "⚠️  Warning: config.json not found!"
    echo "Please create config.json from config.example.json"
    exit 1
fi

# Create logs directory
mkdir -p logs

echo ""

# Auto-detect mode from SQLite-backed config
MODE_INFO=$(python3 - <<'PY'
from src.config_manager import ConfigManager

config = ConfigManager().load()
if "workers" in config:
    enabled = [w for w in config.get("workers", []) if w.get("enabled", True)]
    print(f"multi {len(enabled)}")
else:
    print("single 0")
PY
)

MODE=$(echo "$MODE_INFO" | awk '{print $1}')
WORKER_COUNT=$(echo "$MODE_INFO" | awk '{print $2}')

if [ "$MODE" = "multi" ]; then
    
    if [ "$WORKER_COUNT" -eq "0" ]; then
        echo "⚠️  Warning: No enabled workers found in config!"
        echo "Please enable at least one worker or use single-worker config."
        exit 1
    fi
    
    echo "🎯 Multi-Worker Mode Detected"
    echo "📊 Active workers: $WORKER_COUNT"
    echo ""
    echo "🎉 Starting Worker Manager..."
    echo "Press Ctrl+C to stop all workers"
    echo ""
    python3 worker_manager.py
else
    # Single-worker mode (backward compatibility)
    echo "📡 Single-Worker Mode Detected"
    echo ""
    echo "🎉 Starting bot..."
    echo "Press Ctrl+C to stop"
    echo ""
    python3 bot.py
fi
