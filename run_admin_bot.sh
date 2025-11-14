#!/bin/bash
# Run Telegram Admin Bot

set -e

echo "🤖 Telegram Forwarder Admin Bot"
echo "================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import telebot" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "⚠️  Warning: config.json not found!"
    echo "Please create config.json with your bot token"
    exit 1
fi

echo ""
echo "🎉 Starting admin bot..."
echo "Press Ctrl+C to stop"
echo ""

python admin_bot.py

