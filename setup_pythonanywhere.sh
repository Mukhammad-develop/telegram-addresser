#!/bin/bash

# Quick setup script for PythonAnywhere
# Run this in PythonAnywhere Bash console

echo "🚀 Telegram Forwarder Bot - PythonAnywhere Setup"
echo "=================================================="
echo ""

# Check if we're in PythonAnywhere
if [ -z "$USER" ]; then
    echo "⚠️  This script is designed for PythonAnywhere"
    echo "   Run this in PythonAnywhere Bash console"
    exit 1
fi

# Get username
USERNAME=$(whoami)
PROJECT_DIR="$HOME/telegram-addresser"

echo "📁 Setting up in: $PROJECT_DIR"
echo ""

# Install git if needed
if ! command -v git &> /dev/null; then
    echo "📦 Installing git..."
    sudo apt-get update
    sudo apt-get install -y git
fi

# Create project directory
echo "📁 Creating project directory..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# Clone or update repository
if [ -d ".git" ]; then
    echo "📥 Updating existing repository..."
    git checkout main
    git pull origin main
else
    echo "📥 Cloning repository..."
    git clone https://github.com/Mukhammad-develop/telegram-addresser.git .
    git checkout main
fi

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3.10 -m venv venv
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
    echo "   Or upload your own config.json file via Files tab"
else
    echo "✅ config.json already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 IMPORTANT: Configure before starting!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  Edit config.json with your credentials:"
echo "   cd $PROJECT_DIR"
echo "   nano config.json"
echo ""
echo "   Or upload your config.json via Files tab:"
echo "   Navigate to: $PROJECT_DIR"
echo ""
echo "2️⃣  Authenticate workers (after config is ready):"
echo "   source venv/bin/activate"
echo "   python3 auth_worker.py worker_1"
echo ""
echo "3️⃣  Test run (in console):"
echo "   ./start.sh"
echo ""
echo "4️⃣  Set up scheduled task (for 24/7 operation):"
echo "   Go to Tasks tab → Create a new always-on task"
echo "   Command: cd $PROJECT_DIR && source venv/bin/activate && python3 worker_manager.py"
echo ""
echo "💡 Project location: $PROJECT_DIR"
echo "💡 Logs location: $PROJECT_DIR/logs/forwarder.log"
echo ""
echo "⚠️  Free tier has limitations (tasks stop after a few hours)"
echo "   Paid tier ($5/month) recommended for 24/7 operation"
echo ""

