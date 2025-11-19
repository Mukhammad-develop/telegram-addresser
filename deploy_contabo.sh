#!/bin/bash

# Quick deployment script for Contabo VPS
# Run this on your VPS after connecting via SSH

echo "🚀 Telegram Forwarder Bot - Contabo VPS Deployment"
echo "=================================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run as root or use sudo"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "📦 Installing Python, pip, git..."
apt install -y python3 python3-pip python3-venv git screen

# Create project directory
echo "📁 Creating project directory..."
mkdir -p ~/projects
cd ~/projects

# Clone repository
if [ -d "telegram-addresser" ]; then
    echo "📥 Updating existing repository..."
    cd telegram-addresser
    git checkout main
    git pull origin main
else
    echo "📥 Cloning repository..."
    git clone https://github.com/Mukhammad-develop/telegram-addresser.git
    cd telegram-addresser
    git checkout main
fi

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Make scripts executable
chmod +x start.sh
chmod +x auth_worker.py

# Setup config.json
echo "⚙️  Setting up configuration..."
if [ ! -f "config.json" ]; then
    echo "📝 Creating config.json from example..."
    cp config.example.json config.json
    echo "⚠️  IMPORTANT: Edit config.json with your credentials before starting!"
    echo "   Run: nano config.json"
    echo "   Or upload your own config.json file"
else
    echo "✅ config.json already exists"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 IMPORTANT: Configure before starting!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  Edit config.json with your credentials:"
echo "   cd ~/projects/telegram-addresser"
echo "   nano config.json"
echo ""
echo "   Or upload your config.json from your computer:"
echo "   scp config.json root@YOUR_VPS_IP:~/projects/telegram-addresser/"
echo ""
echo "2️⃣  Authenticate workers (after config is ready):"
echo "   source venv/bin/activate"
echo "   python3 auth_worker.py worker_1"
echo ""
echo "3️⃣  Start the bot (only after config and auth are done):"
echo "   ./start.sh"
echo ""
echo "💡 To run in background:"
echo "   screen -S telegram-bot"
echo "   ./start.sh"
echo "   Press Ctrl+A, then D to detach"
echo "   screen -r telegram-bot to reattach"
echo ""
echo "⚠️  The bot will NOT start automatically!"
echo "   You must configure config.json and authenticate first."
echo ""

