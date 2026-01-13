#!/usr/bin/env python3
"""Helper script to authenticate a specific worker in multi-worker mode."""
import json
import sys
import asyncio
from telethon import TelegramClient
from src.config_manager import ConfigManager


async def authenticate_worker(worker_id: str, config_path: str = "config.json"):
    """Authenticate a specific worker."""
    # Load config
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.load()
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return False
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in config file: {config_path}")
        return False
    
    # Find worker
    workers = config.get("workers", [])
    worker = next((w for w in workers if w["worker_id"] == worker_id), None)
    
    if not worker:
        print(f"❌ Worker '{worker_id}' not found in config")
        print("\n💡 Available workers:")
        for w in workers:
            print(f"   • {w['worker_id']}")
        return False
    
    # Get worker credentials
    api_id = worker.get("api_id")
    api_hash = worker.get("api_hash")
    session_name = worker.get("session_name")
    
    if not api_id or not api_hash or not session_name:
        print(f"❌ Worker '{worker_id}' is missing API credentials")
        return False
    
    print(f"\n🔐 Authenticating Worker: {worker_id}")
    print(f"📱 API ID: {api_id}")
    print(f"📁 Session: {session_name}")
    print("="*60)
    
    # Create Telegram client
    client = TelegramClient(session_name, api_id, api_hash)
    
    try:
        print("\n⏳ Connecting to Telegram...")
        await client.start()
        
        # Get authenticated user info
        me = await client.get_me()
        
        print(f"\n✅ Authentication successful!")
        print(f"👤 Logged in as: {me.first_name}")
        if me.username:
            print(f"🔗 Username: @{me.username}")
        print(f"📞 Phone: {me.phone}")
        print(f"\n📁 Session file created: {session_name}.session")
        print(f"\n🎉 Worker '{worker_id}' is now authenticated!")
        print(f"💡 You can now start the bot: ./start.sh\n")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        await client.disconnect()
        return False


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("\n📋 Worker Authentication Helper")
        print("="*60)
        print("\nUsage: python auth_worker.py <worker_id>")
        print("\nExample: python auth_worker.py worker_lupin")
        print("\nThis script will:")
        print("  1. Read the worker's API credentials from config.db")
        print("  2. Prompt you for phone number and verification code")
        print("  3. Create the session file for this worker")
        print("  4. After authentication, you can start the bot normally")
        print("\n" + "="*60)
        
        # List available workers
        try:
            config = ConfigManager("config.json").load()
            
            workers = config.get("workers", [])
            if workers:
                print("\n💡 Available workers in config.db:")
                for w in workers:
                    worker_id = w.get("worker_id", "unknown")
                    session = w.get("session_name", "unknown")
                    print(f"   • {worker_id} (session: {session})")
                print()
        except:
            pass
        
        sys.exit(1)
    
    worker_id = sys.argv[1]
    success = await authenticate_worker(worker_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
