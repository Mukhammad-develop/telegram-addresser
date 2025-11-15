"""Main Telegram forwarder bot with multi-channel support."""
import asyncio
import time
from typing import Dict, List, Optional, Set
from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError, 
    MessageIdInvalidError, 
    ChannelPrivateError,
    ChatWriteForbiddenError,
    SlowModeWaitError,
    ChatForwardsRestrictedError
)
from telethon.tl.types import Message

from src.config_manager import ConfigManager
from src.text_processor import TextProcessor
from src.logger_setup import setup_logger, get_logger


class TelegramForwarder:
    """Main forwarder bot class."""
    
    def __init__(self, config_path: str = "config.json"):
        # Load configuration
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load()
        
        # Set up logging
        settings = self.config_manager.get_settings()
        self.logger = setup_logger(
            log_level=settings.get("log_level", "INFO"),
            log_file="logs/forwarder.log"
        )
        
        # Initialize text processor
        self.text_processor = TextProcessor(
            self.config_manager.get_replacement_rules()
        )
        
        # Get API credentials
        creds = self.config_manager.get_api_credentials()
        self.api_id = creds.get("api_id")
        self.api_hash = creds.get("api_hash")
        self.session_name = creds.get("session_name", "forwarder_session")
        
        # Validate credentials
        if not self.api_id or not self.api_hash:
            raise ValueError("API credentials not configured. Please update config.json")
        
        # Initialize Telegram client
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        
        # Track forwarded messages to avoid duplicates
        self.forwarded_messages: Set[int] = set()
        
        # Get settings
        self.retry_attempts = settings.get("retry_attempts", 5)
        self.retry_delay = settings.get("retry_delay", 5)
        self.flood_wait_extra = settings.get("flood_wait_extra_delay", 10)
        self.max_message_length = settings.get("max_message_length", 4096)
        
        self.logger.info("TelegramForwarder initialized")
    
    async def start(self) -> None:
        """Start the bot and set up event handlers."""
        await self.client.start()
        self.logger.info("Bot started successfully")
        
        # Get source channels
        channel_pairs = self.config_manager.get_channel_pairs()
        source_channels = [pair["source"] for pair in channel_pairs]
        
        if not source_channels:
            self.logger.warning("No channel pairs configured. Bot is running but not forwarding anything.")
        else:
            self.logger.info(f"Monitoring {len(source_channels)} source channel(s)")
        
        # Verify access to all channels before starting
        for pair in channel_pairs:
            try:
                source_entity = await self.client.get_entity(pair["source"])
                target_entity = await self.client.get_entity(pair["target"])
                self.logger.info(
                    f"✓ Access verified: {getattr(source_entity, 'title', 'Channel')} → "
                    f"{getattr(target_entity, 'title', 'Channel')}"
                )
            except ValueError as e:
                self.logger.error(
                    f"✗ Cannot access channels {pair['source']} → {pair['target']}. "
                    f"Make sure your account is a member of both channels. Error: {e}"
                )
                continue
        
        # Register event handler for new messages
        @self.client.on(events.NewMessage(chats=source_channels))
        async def handler(event):
            await self.handle_new_message(event)
        
        # Backfill recent messages for each channel pair
        for pair in channel_pairs:
            backfill_count = pair.get("backfill_count", 0)
            if backfill_count > 0:
                await self.backfill_messages(pair["source"], pair["target"], backfill_count)
        
        self.logger.info("Bot is now running. Press Ctrl+C to stop.")
        
        # Keep the bot running
        await self.client.run_until_disconnected()
    
    async def handle_new_message(self, event) -> None:
        """
        Handle incoming new messages and copy them (without "Forwarded from" tag).
        
        Args:
            event: Telethon NewMessage event
        """
        message = event.message
        source_chat_id = event.chat_id
        
        # Find target channel(s) for this source
        channel_pairs = self.config_manager.get_channel_pairs()
        targets = [
            pair["target"] 
            for pair in channel_pairs 
            if pair["source"] == source_chat_id
        ]
        
        if not targets:
            return
        
        # Get message text (from message or caption)
        text = message.text or message.message or ""
        
        # Check filters
        filters = self.config_manager.get_filters()
        if not self.text_processor.should_forward_message(text, filters):
            self.logger.debug(f"Message {message.id} filtered out")
            return
        
        # Forward to all target channels
        for target in targets:
            await self.forward_message_with_retry(message, source_chat_id, target)
    
    async def forward_message_with_retry(
        self, 
        message: Message, 
        source: int, 
        target: int,
        is_backfill: bool = False
    ) -> bool:
        """
        Copy and send a message without "Forwarded from" metadata.
        
        Args:
            message: Message to copy
            source: Source channel ID
            target: Target channel ID
            is_backfill: Whether this is a backfill operation
            
        Returns:
            True if successful, False otherwise
        """
        attempt = 0
        prefix = "BACKFILL" if is_backfill else "LIVE"
        
        while attempt < self.retry_attempts:
            try:
                # Get message text/caption and apply replacements
                text = message.text or message.message or ""
                if text:
                    text = self.text_processor.process_text(text)
                
                # Handle message with media (bypass content protection by downloading first)
                if message.media:
                    try:
                        # Download media to memory
                        media_file = await self.client.download_media(message, file=bytes)
                        
                        # Re-upload as new message with processed caption
                        await self.client.send_file(
                            target,
                            media_file,
                            caption=text if text else None
                        )
                    except Exception as download_error:
                        # If download fails, try direct send (might work for some media)
                        self.logger.warning(f"Download failed, trying direct send: {download_error}")
                        await self.client.send_message(
                            target,
                            text if text else None,
                            file=message.media
                        )
                else:
                    # Send text-only message
                    await self.client.send_message(target, text)
                
                self.logger.info(
                    f"{prefix} -> Copied message {message.id} "
                    f"from {source} to {target}"
                )
                return True
                
            except FloodWaitError as e:
                wait_time = e.seconds + self.flood_wait_extra
                self.logger.warning(
                    f"FloodWaitError: Waiting {wait_time} seconds before retry"
                )
                await asyncio.sleep(wait_time)
                attempt += 1
                
            except SlowModeWaitError as e:
                wait_time = e.seconds + 1
                self.logger.warning(
                    f"SlowModeWaitError: Waiting {wait_time} seconds before retry"
                )
                await asyncio.sleep(wait_time)
                attempt += 1
                
            except MessageIdInvalidError:
                self.logger.error(
                    f"Invalid message ID {message.id} - skipping"
                )
                return False
                
            except ChannelPrivateError:
                self.logger.error(
                    f"Cannot access channel {target} - it's private or you're not a member"
                )
                return False
                
            except ChatWriteForbiddenError:
                self.logger.error(
                    f"Cannot write to channel {target} - insufficient permissions"
                )
                return False
                
            except ChatForwardsRestrictedError:
                self.logger.error(
                    f"Cannot copy messages from {source} - channel has forwarding restrictions enabled. "
                    f"The admin must disable 'Restrict saving content' in channel settings."
                )
                return False
                
            except Exception as e:
                self.logger.error(
                    f"Error copying message {message.id} "
                    f"from {source} to {target}: {type(e).__name__}: {e}"
                )
                
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    attempt += 1
                else:
                    return False
        
        self.logger.error(
            f"Failed to copy message {message.id} after {self.retry_attempts} attempts"
        )
        return False
    
    async def backfill_messages(
        self, 
        source: int, 
        target: int, 
        count: int
    ) -> None:
        """
        Backfill recent messages from source to target (copies without "Forwarded from").
        
        Args:
            source: Source channel ID
            target: Target channel ID
            count: Number of recent messages to backfill
        """
        if count <= 0:
            return
        
        try:
            self.logger.info(
                f"Backfilling last {count} messages from {source} to {target}"
            )
            
            # Get channel entities first (important for Telethon)
            try:
                source_entity = await self.client.get_entity(source)
                target_entity = await self.client.get_entity(target)
            except ValueError as e:
                self.logger.error(
                    f"Cannot access channel - make sure your account is a member of both channels. "
                    f"Source: {source}, Target: {target}. Error: {e}"
                )
                return
            
            # Get recent messages
            messages = await self.client.get_messages(source_entity, limit=count)
            
            # Copy in chronological order (oldest first)
            for message in reversed(messages):
                # Check filters
                text = message.text or message.message or ""
                filters = self.config_manager.get_filters()
                
                if not self.text_processor.should_forward_message(text, filters):
                    self.logger.debug(f"Backfill message {message.id} filtered out")
                    continue
                
                # Copy with retry
                await self.forward_message_with_retry(message, source, target, is_backfill=True)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(1)
            
            self.logger.info(f"Backfill completed for {source} -> {target}")
            
        except Exception as e:
            self.logger.error(
                f"Error during backfill from {source} to {target}: {type(e).__name__}: {e}"
            )
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self.logger.info("Reloading configuration...")
        self.config = self.config_manager.load()
        self.text_processor.update_rules(self.config_manager.get_replacement_rules())
        self.logger.info("Configuration reloaded")
    
    async def stop(self) -> None:
        """Stop the bot gracefully."""
        self.logger.info("Stopping bot...")
        await self.client.disconnect()
        self.logger.info("Bot stopped")


async def main():
    """Main entry point."""
    bot = TelegramForwarder()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal. Shutting down gracefully...")
    except Exception as e:
        logger = get_logger()
        logger.critical(f"Fatal error: {type(e).__name__}: {e}", exc_info=True)
        raise
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

