#!/usr/bin/env python3
"""
Test script to run a single worker WITHOUT multiprocessing.
This will help diagnose if the issue is with multiprocessing or Telethon itself.
"""
import asyncio
import json
from bot import TelegramForwarder

async def main():
    # Load config
    with open('config.json') as f:
        config = json.load(f)
    
    # Get first worker
    worker = config['workers'][0]
    
    print(f"\n🧪 Testing worker: {worker['worker_id']}")
    print(f"📋 Channels: {len(worker['channel_pairs'])}")
    print(f"🔑 Session: {worker['session_name']}")
    print("\n" + "=" * 60)
    print("🚀 Starting bot WITHOUT multiprocessing...")
    print("=" * 60 + "\n")
    
    # Build single-worker config
    test_config = {
        'api_credentials': {
            'api_id': worker['api_id'],
            'api_hash': worker['api_hash'],
            'session_name': worker['session_name']
        },
        'channel_pairs': worker['channel_pairs'][:2],  # Just first 2 pairs for testing
        'replacement_rules': worker.get('replacement_rules', []),
        'filters': worker.get('filters', {'enabled': False}),
        'settings': worker.get('settings', {
            'log_level': 'INFO',
            'retry_attempts': 5,
            'retry_delay': 5,
            'add_source_link': False
        })
    }
    
    # Run bot
    bot = TelegramForwarder(test_config)
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())

