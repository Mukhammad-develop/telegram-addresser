#!/bin/bash
# Quick start script for Telegram Forwarder Bot

set -e

echo "🚀 Telegram Forwarder Bot - Quick Start"
echo "========================================"
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
    echo "Please create config.json with your API credentials."
    exit 1
fi

# Create logs directory
mkdir -p logs

echo ""
echo "🎉 Starting bot..."
echo "Press Ctrl+C to stop"
echo ""

python bot.py

