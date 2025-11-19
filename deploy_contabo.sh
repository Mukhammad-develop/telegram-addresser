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
    git checkout v0.6
    git pull origin v0.6
else
    echo "📥 Cloning repository..."
    git clone https://github.com/Mukhammad-develop/telegram-addresser.git
    cd telegram-addresser
    git checkout v0.6
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

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Copy your config.json to: ~/projects/telegram-addresser/"
echo "2. Authenticate workers: python3 auth_worker.py worker_1"
echo "3. Start the bot: ./start.sh"
echo ""
echo "💡 To run in background, use: screen -S telegram-bot"
echo "💡 To detach: Press Ctrl+A, then D"
echo "💡 To reattach: screen -r telegram-bot"
echo ""

