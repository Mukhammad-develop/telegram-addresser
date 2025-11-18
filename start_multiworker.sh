#!/bin/bash

# Multi-Worker Telegram Forwarder Startup Script

echo "🎯 Multi-Worker Telegram Forwarder Manager"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if dependencies are installed
if ! python -c "import telethon" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
else
    echo "✅ Dependencies already installed"
fi

echo ""
echo "🎉 Starting Multi-Worker Manager..."
echo "Press Ctrl+C to stop all workers"
echo ""

# Run the worker manager
python3 worker_manager.py

