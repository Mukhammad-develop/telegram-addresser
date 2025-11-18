"""Main Telegram forwarder bot with multi-channel support."""
import asyncio
import json
import os
import shutil
import time
from pathlib import Path
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
from telethon.tl.types import Message, MessageMediaDocument, DocumentAttributeSticker, DocumentAttributeAnimated

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
        
        # Track processed media groups to avoid duplicates
        self.processed_groups: Set[int] = set()
        
        # Map source message IDs to target message IDs for reply preservation
        # Key: f"{source_channel_id}:{source_msg_id}" -> Value: target_msg_id
        self.message_id_map: Dict[str, int] = {}
        
        # Get settings
        self.retry_attempts = settings.get("retry_attempts", 5)
        self.retry_delay = settings.get("retry_delay", 5)
        self.flood_wait_extra = settings.get("flood_wait_extra_delay", 10)
        self.max_message_length = settings.get("max_message_length", 4096)
        self.add_source_link = settings.get("add_source_link", False)
        self.source_link_text = settings.get("source_link_text", "\n\n🔗 Source: {link}")
        
        # Create temp directory for media downloads
        self.temp_media_dir = Path("temp_media")
        self.temp_media_dir.mkdir(exist_ok=True)
        
        # Track which channel pairs have been backfilled to avoid duplicates
        self.backfill_tracking_file = Path("backfill_tracking.json")
        self.backfilled_pairs: Set[str] = self._load_backfill_tracking()
        
        # File-based trigger for auto-backfill (created by admin bot)
        self.backfill_trigger_file = Path("trigger_backfill.flag")
        
        self.logger.info("TelegramForwarder initialized")
    
    def _load_backfill_tracking(self) -> Set[str]:
        """Load backfill tracking from file."""
        if self.backfill_tracking_file.exists():
            try:
                with open(self.backfill_tracking_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get("backfilled_pairs", []))
            except Exception as e:
                self.logger.warning(f"Failed to load backfill tracking: {e}")
        return set()
    
    def _save_backfill_tracking(self) -> None:
        """Save backfill tracking to file."""
        try:
            with open(self.backfill_tracking_file, 'w') as f:
                json.dump({"backfilled_pairs": list(self.backfilled_pairs)}, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save backfill tracking: {e}")
    
    def _get_pair_key(self, source: int, target: int) -> str:
        """Generate a unique key for a channel pair."""
        return f"{source}:{target}"
    
    def _is_sticker_or_animated(self, message: Message) -> bool:
        """Check if message contains a sticker or animated sticker."""
        if not message.media or not isinstance(message.media, MessageMediaDocument):
            return False
        
        # Check document attributes for sticker or animated
        if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
            for attr in message.media.document.attributes:
                if isinstance(attr, (DocumentAttributeSticker, DocumentAttributeAnimated)):
                    return True
        return False
    
    async def _check_and_backfill_new_pairs(self) -> None:
        """Check for new channel pairs and backfill them automatically."""
        try:
            # Reload config to get latest pairs
            self.config_manager.load()
            channel_pairs = self.config_manager.get_channel_pairs()
            
            new_pairs_found = False
            
            for pair in channel_pairs:
                backfill_count = pair.get("backfill_count", 0)
                if backfill_count > 0:
                    pair_key = self._get_pair_key(pair["source"], pair["target"])
                    
                    # Check if this is a new pair that hasn't been backfilled
                    if pair_key not in self.backfilled_pairs:
                        new_pairs_found = True
                        self.logger.info(f"🆕 Auto-detected NEW pair, starting backfill: {pair['source']} -> {pair['target']}")
                        
                        # Backfill the new pair
                        await self.backfill_messages(pair["source"], pair["target"], backfill_count)
                        
                        # Mark as backfilled
                        self.backfilled_pairs.add(pair_key)
                        self._save_backfill_tracking()
                        
                        self.logger.info(f"✅ Auto-backfill completed for: {pair['source']} -> {pair['target']}")
            
            if not new_pairs_found:
                self.logger.info("ℹ️ No new pairs detected for backfill")
                
        except Exception as e:
            self.logger.error(f"Error during auto-backfill check: {e}")
    
    async def _monitor_backfill_trigger(self) -> None:
        """Monitor for backfill trigger file and process new pairs automatically."""
        while True:
            try:
                # Check every 5 seconds
                await asyncio.sleep(5)
                
                # Check if trigger file exists
                if self.backfill_trigger_file.exists():
                    self.logger.info("🔔 Backfill trigger detected! Checking for new pairs...")
                    
                    # Process new pairs
                    await self._check_and_backfill_new_pairs()
                    
                    # Remove trigger file
                    try:
                        self.backfill_trigger_file.unlink()
                        self.logger.info("🗑️ Trigger file removed")
                    except Exception as e:
                        self.logger.warning(f"Failed to remove trigger file: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in backfill trigger monitor: {e}")
    
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
        
        # Backfill recent messages for NEW channel pairs only (to avoid duplicates)
        self.logger.info(f"📋 Checking backfill status for {len(channel_pairs)} channel pair(s)")
        self.logger.info(f"📋 Currently tracked as backfilled: {list(self.backfilled_pairs)}")
        
        for pair in channel_pairs:
            backfill_count = pair.get("backfill_count", 0)
            pair_key = self._get_pair_key(pair["source"], pair["target"])
            
            self.logger.info(f"📋 Pair: {pair['source']} -> {pair['target']}, backfill_count: {backfill_count}, pair_key: {pair_key}")
            
            if backfill_count > 0:
                if pair_key not in self.backfilled_pairs:
                    self.logger.info(f"🔄 NEW PAIR DETECTED - Starting backfill: {pair['source']} -> {pair['target']}")
                    await self.backfill_messages(pair["source"], pair["target"], backfill_count)
                    # Mark as backfilled
                    self.backfilled_pairs.add(pair_key)
                    self._save_backfill_tracking()
                    self.logger.info(f"✅ Backfill completed and tracked for: {pair_key}")
                else:
                    self.logger.info(f"⏭️  SKIPPING - Pair already backfilled: {pair['source']} -> {pair['target']}")
            else:
                self.logger.info(f"⏭️  SKIPPING - backfill_count is 0 for: {pair['source']} -> {pair['target']}")
        
        self.logger.info("Bot is now running. Press Ctrl+C to stop.")
        
        # Start background task to monitor for backfill triggers
        self.logger.info("🔍 Starting auto-backfill monitor (checks every 5 seconds)")
        monitor_task = asyncio.create_task(self._monitor_backfill_trigger())
        
        # Keep the bot running
        try:
            await self.client.run_until_disconnected()
        finally:
            # Cancel monitor task on shutdown
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
    
    async def handle_new_message(self, event) -> None:
        """
        Handle incoming new messages and copy them (without "Forwarded from" tag).
        
        Args:
            event: Telethon NewMessage event
        """
        # Track timing for delay analysis
        import time as time_module
        start_time = time_module.time()
        
        message = event.message
        source_chat_id = event.chat_id
        
        self.logger.info(f"⏱️ [TIMING] Message {message.id} received at {start_time}")
        
        # Check if this message is part of a media group we've already processed
        if message.grouped_id:
            if message.grouped_id in self.processed_groups:
                self.logger.debug(
                    f"Skipping message {message.id} - already processed as part of group {message.grouped_id}"
                )
                return
            # Mark this group as processed
            self.processed_groups.add(message.grouped_id)
            
            # Clean up old group IDs (keep only last 100)
            if len(self.processed_groups) > 100:
                # Remove oldest entries
                sorted_groups = sorted(self.processed_groups)
                self.processed_groups = set(sorted_groups[-100:])
        
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
            forward_start = time_module.time()
            await self.forward_message_with_retry(message, source_chat_id, target)
            forward_end = time_module.time()
            forward_duration = forward_end - start_time
            self.logger.info(f"⏱️ [TIMING] Message {message.id} forwarded in {forward_duration:.2f}s (processing time: {forward_end - forward_start:.2f}s)")
    
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
                # Get message text/caption - use message.message for plain text (not .text which adds markdown)
                original_text = message.message or ""
                text = original_text
                
                # Track if text was modified (modifications break entity offsets)
                text_was_modified = False
                
                # Apply replacement rules
                if text:
                    processed_text = self.text_processor.process_text(text)
                    if processed_text != text:
                        text = processed_text
                        text_was_modified = True
                
                # Add source link if enabled (for testing/verification)
                # Note: Adding text at the END doesn't break entity offsets at the start
                if self.add_source_link:
                    # Convert channel ID to link format (remove -100 prefix)
                    channel_id = str(source).replace("-100", "")
                    message_link = f"https://t.me/c/{channel_id}/{message.id}"
                    link_text = self.source_link_text.format(link=message_link)
                    text = (text or "") + link_text
                    # Don't set text_was_modified here since we only append at the end
                
                # Get reply_to_msg_id if this is a reply
                reply_to = None
                if message.reply_to and message.reply_to.reply_to_msg_id:
                    # Map the source reply ID to target reply ID
                    source_reply_id = message.reply_to.reply_to_msg_id
                    map_key = f"{source}:{source_reply_id}"
                    reply_to = self.message_id_map.get(map_key)
                    if not reply_to:
                        self.logger.debug(
                            f"Reply target message {source_reply_id} not found in map, reply chain will break"
                        )
                
                # Check if message is forwarded from another channel
                if message.forward:
                    # This message was forwarded from somewhere, so forward it to target
                    # Try to forward from the ORIGINAL source to preserve "Forwarded from" metadata
                    try:
                        # Debug: Log forward object attributes (using INFO to ensure visibility)
                        self.logger.info(f"🔍 DEBUG - Forward object type: {type(message.forward)}")
                        self.logger.info(f"🔍 DEBUG - Forward attributes: {[attr for attr in dir(message.forward) if not attr.startswith('_')]}")
                        self.logger.info(
                            f"🔍 DEBUG - from_id: {getattr(message.forward, 'from_id', 'NOT FOUND')}, "
                            f"from_name: {getattr(message.forward, 'from_name', 'NOT FOUND')}, "
                            f"channel_post: {getattr(message.forward, 'channel_post', 'NOT FOUND')}, "
                            f"chat_id: {getattr(message.forward, 'chat_id', 'NOT FOUND')}, "
                            f"saved_from_peer: {getattr(message.forward, 'saved_from_peer', 'NOT FOUND')}, "
                            f"saved_from_msg_id: {getattr(message.forward, 'saved_from_msg_id', 'NOT FOUND')}"
                        )
                        
                        # Check if we have the original channel and message ID
                        original_channel = None
                        original_msg_id = None
                        
                        # Get original channel from forward info (use chat_id, not from_id)
                        if hasattr(message.forward, 'chat_id') and message.forward.chat_id:
                            original_channel = message.forward.chat_id
                        
                        # Get original message ID from forward info
                        if hasattr(message.forward, 'channel_post') and message.forward.channel_post:
                            original_msg_id = message.forward.channel_post
                        
                        self.logger.info(
                            f"🔍 Detected forwarded message - Original channel: {original_channel}, "
                            f"Original message: {original_msg_id}"
                        )
                        
                        sent_msg = None
                        
                        # Try to forward from original channel (best option - preserves "Forwarded from")
                        if original_channel and original_msg_id:
                            try:
                                self.logger.info(
                                    f"🔄 Attempting to forward from ORIGINAL channel {original_channel}, "
                                    f"message {original_msg_id} to target {target}"
                                )
                                sent_msg = await self.client.forward_messages(
                                    target, 
                                    original_msg_id, 
                                    original_channel
                                )
                                self.logger.info(
                                    f"✅ {prefix} -> Successfully forwarded from ORIGINAL channel "
                                    f"{original_channel} (msg {original_msg_id}) to {target}"
                                )
                            except Exception as original_forward_error:
                                self.logger.warning(
                                    f"❌ Could not forward from ORIGINAL channel {original_channel}: "
                                    f"{type(original_forward_error).__name__}: {original_forward_error}"
                                )
                                self.logger.info(f"🔄 Trying fallback: forwarding from source channel...")
                                # Fall through to try forwarding from source channel
                        
                        # If forwarding from original failed, try from source channel
                        if not sent_msg:
                            try:
                                self.logger.info(f"🔄 Trying to forward from SOURCE channel {source}...")
                                sent_msg = await self.client.forward_messages(target, message)
                                self.logger.info(
                                    f"✅ {prefix} -> Forwarded message {message.id} from SOURCE {source} to {target}"
                                )
                            except Exception as source_forward_error:
                                self.logger.warning(
                                    f"❌ Could not forward from SOURCE channel either: "
                                    f"{type(source_forward_error).__name__}: {source_forward_error}"
                                )
                                self.logger.info(f"📋 Final fallback: Will copy message content instead")
                                # Fall through to copying method
                        
                        # Store message ID mapping for reply chains
                        if sent_msg:
                            map_key = f"{source}:{message.id}"
                            self.message_id_map[map_key] = sent_msg.id
                            # Clean up old mappings (keep last 1000)
                            if len(self.message_id_map) > 1000:
                                # Remove oldest 200 entries
                                keys_to_remove = list(self.message_id_map.keys())[:200]
                                for key in keys_to_remove:
                                    del self.message_id_map[key]
                            return True
                        
                    except Exception as forward_error:
                        self.logger.warning(f"Forward handling failed: {forward_error}, will copy instead")
                        # Fall through to copying method
                
                # Handle media groups (albums with multiple photos/videos)
                if message.grouped_id:
                    # This is part of a media group/album
                    # Get all messages in this group
                    media_files = []
                    try:
                        messages_in_group = await self.client.get_messages(
                            source,
                            limit=10,
                            min_id=message.id - 10,
                            max_id=message.id + 10
                        )
                        
                        # Filter messages with same grouped_id
                        group_messages = [
                            m for m in messages_in_group
                            if m.grouped_id == message.grouped_id
                        ]
                        
                        # Sort by ID to get correct order
                        sorted_group = sorted(group_messages, key=lambda x: x.id)
                        
                        # Extract caption from ANY message in group that has text
                        # (caption could be on any photo, not necessarily the first one)
                        group_text = ""
                        caption_msg = None
                        group_text_was_modified = False
                        
                        if sorted_group:
                            # Try to find a message with text/caption
                            for msg in sorted_group:
                                msg_text = msg.message or ""  # Use .message not .text to avoid markdown
                                if msg_text:
                                    group_text = msg_text
                                    caption_msg = msg
                                    break
                            
                            # If we found a caption, process it
                            if group_text:
                                processed_group_text = self.text_processor.process_text(group_text)
                                if processed_group_text != group_text:
                                    group_text = processed_group_text
                                    group_text_was_modified = True
                            
                            # Add source link (use first message ID for link)
                            if self.add_source_link:
                                channel_id = str(source).replace("-100", "")
                                # Use the message with caption if found, otherwise first message
                                link_msg = caption_msg if caption_msg else sorted_group[0]
                                message_link = f"https://t.me/c/{channel_id}/{link_msg.id}"
                                link_text = self.source_link_text.format(link=message_link)
                                group_text = (group_text or "") + link_text
                        
                        # Download all media in the group
                        for msg in sorted_group:
                            if msg.media:
                                # Download to temp directory
                                file_path = await self.client.download_media(
                                    msg,
                                    file=self.temp_media_dir
                                )
                                if file_path:
                                    media_files.append(file_path)
                        
                        # Send all media together with caption from first message
                        if media_files:
                            # Preserve entities (including custom emojis) ONLY if text wasn't modified
                            formatting_entities = None
                            if not group_text_was_modified and caption_msg and hasattr(caption_msg, 'entities'):
                                formatting_entities = caption_msg.entities
                            
                            sent_msg = await self.client.send_file(
                                target,
                                media_files,
                                caption=group_text if group_text else None,
                                reply_to=reply_to,
                                formatting_entities=formatting_entities
                            )
                            
                            # Store message ID mapping for reply chains
                            if sent_msg:
                                # For media groups, sent_msg might be a list
                                if isinstance(sent_msg, list):
                                    # Map the first message in group (which has the caption)
                                    map_key = f"{source}:{message.id}"
                                    self.message_id_map[map_key] = sent_msg[0].id
                                else:
                                    map_key = f"{source}:{message.id}"
                                    self.message_id_map[map_key] = sent_msg.id
                                
                                # Clean up old mappings (keep last 1000)
                                if len(self.message_id_map) > 1000:
                                    keys_to_remove = list(self.message_id_map.keys())[:200]
                                    for key in keys_to_remove:
                                        del self.message_id_map[key]
                            
                            self.logger.info(
                                f"{prefix} -> Sent media group with {len(media_files)} items "
                                f"from {source} to {target}"
                            )
                            
                            # Clean up downloaded files
                            for file_path in media_files:
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    self.logger.warning(f"Failed to delete {file_path}: {e}")
                            
                            return True
                    except Exception as group_error:
                        self.logger.warning(f"Media group handling failed: {group_error}, trying single message")
                        # Clean up any downloaded files
                        for file_path in media_files:
                            try:
                                os.remove(file_path)
                            except:
                                pass
                        # Fall through to single message handling
                
                # Handle single media message
                if message.media:
                    # Check if it's a sticker or animated sticker - send directly without downloading
                    if self._is_sticker_or_animated(message):
                        self.logger.debug(f"Detected sticker/animated emoji, sending directly without download")
                        # Preserve entities ONLY if text wasn't modified
                        formatting_entities = None
                        if not text_was_modified and hasattr(message, 'entities'):
                            formatting_entities = message.entities
                        
                        sent_msg = await self.client.send_file(
                            target,
                            message.media,
                            caption=text if text else None,
                            reply_to=reply_to,
                            formatting_entities=formatting_entities
                        )
                        
                        # Store message ID mapping for reply chains
                        if sent_msg:
                            map_key = f"{source}:{message.id}"
                            self.message_id_map[map_key] = sent_msg.id
                            # Clean up old mappings (keep last 1000)
                            if len(self.message_id_map) > 1000:
                                keys_to_remove = list(self.message_id_map.keys())[:200]
                                for key in keys_to_remove:
                                    del self.message_id_map[key]
                        
                        self.logger.info(f"{prefix} -> Sent sticker/emoji {message.id} from {source} to {target}")
                        return True
                    
                    # For non-stickers, download and re-upload
                    file_path = None
                    try:
                        # Download media to temp directory
                        file_path = await self.client.download_media(
                            message,
                            file=self.temp_media_dir
                        )
                        
                        if file_path:
                            # Re-upload with processed caption
                            # Preserve entities (including custom emojis) ONLY if text wasn't modified
                            formatting_entities = None
                            if not text_was_modified and hasattr(message, 'entities'):
                                formatting_entities = message.entities
                            
                            sent_msg = await self.client.send_file(
                                target,
                                file_path,
                                caption=text if text else None,
                                reply_to=reply_to,
                                formatting_entities=formatting_entities
                            )
                            
                            # Store message ID mapping for reply chains
                            if sent_msg:
                                map_key = f"{source}:{message.id}"
                                self.message_id_map[map_key] = sent_msg.id
                                # Clean up old mappings (keep last 1000)
                                if len(self.message_id_map) > 1000:
                                    keys_to_remove = list(self.message_id_map.keys())[:200]
                                    for key in keys_to_remove:
                                        del self.message_id_map[key]
                            
                            # Clean up downloaded file
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                self.logger.warning(f"Failed to delete {file_path}: {e}")
                        else:
                            raise Exception("Download returned None")
                    
                    except Exception as download_error:
                        # If download fails, try direct send
                        self.logger.warning(f"Download failed, trying direct send: {download_error}")
                        # Preserve entities ONLY if text wasn't modified
                        formatting_entities = None
                        if not text_was_modified and hasattr(message, 'entities'):
                            formatting_entities = message.entities
                        
                        await self.client.send_message(
                            target,
                            text if text else None,
                            file=message.media,
                            reply_to=reply_to,
                            formatting_entities=formatting_entities
                        )
                    finally:
                        # Ensure cleanup even if send fails
                        if file_path and os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except:
                                pass
                else:
                    # Send text-only message
                    # Preserve entities (including custom emojis) ONLY if text wasn't modified
                    formatting_entities = None
                    if not text_was_modified and hasattr(message, 'entities'):
                        formatting_entities = message.entities
                    
                    sent_msg = await self.client.send_message(
                        target, 
                        text,
                        reply_to=reply_to,
                        formatting_entities=formatting_entities
                    )
                    
                    # Store message ID mapping for reply chains
                    if sent_msg:
                        map_key = f"{source}:{message.id}"
                        self.message_id_map[map_key] = sent_msg.id
                        # Clean up old mappings (keep last 1000)
                        if len(self.message_id_map) > 1000:
                            keys_to_remove = list(self.message_id_map.keys())[:200]
                            for key in keys_to_remove:
                                del self.message_id_map[key]
                
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
            
            # Track processed groups during backfill
            backfill_processed_groups = set()
            
            # Copy in chronological order (oldest first)
            for message in reversed(messages):
                # Skip if this message is part of an already-processed media group
                if message.grouped_id:
                    if message.grouped_id in backfill_processed_groups:
                        self.logger.debug(
                            f"Backfill: Skipping message {message.id} - already processed as part of group {message.grouped_id}"
                        )
                        continue
                    # Mark this group as processed
                    backfill_processed_groups.add(message.grouped_id)
                
                # Check filters
                text = message.text or message.message or ""
                filters = self.config_manager.get_filters()
                
                if not self.text_processor.should_forward_message(text, filters):
                    self.logger.debug(f"Backfill message {message.id} filtered out")
                    continue
                
                # Copy with retry (no delay - let retry logic handle rate limits)
                await self.forward_message_with_retry(message, source, target, is_backfill=True)
            
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
        
        # Clean up temp media directory
        if self.temp_media_dir.exists():
            try:
                shutil.rmtree(self.temp_media_dir)
                self.logger.info("Cleaned up temp media directory")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temp directory: {e}")
        
        await self.client.disconnect()
        self.logger.info("Bot stopped")


async def main():
    """Main entry point."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Telegram Forwarder Bot')
    parser.add_argument('--config', type=str, default='config.json',
                       help='Path to configuration file')
    parser.add_argument('--auth-only', action='store_true',
                       help='Only perform authentication, then exit')
    args = parser.parse_args()
    
    # Check if config is multi-worker format
    try:
        with open(args.config, 'r') as f:
            config_data = json.load(f)
        
        if "workers" in config_data and isinstance(config_data.get("workers"), list):
            # Multi-worker config detected
            print("\n" + "="*60)
            print("⚠️  MULTI-WORKER CONFIG DETECTED")
            print("="*60)
            print("\n❌ You're trying to run bot.py directly with a multi-worker config.")
            print("\n📝 To use multi-worker mode:\n")
            print("   ./start.sh")
            print("\n📝 To authenticate a specific worker:\n")
            print("   1. Find the worker's session name in config.json")
            print(f"   2. Create a temporary single-worker config")
            print("   3. Or use the admin bot to manage workers")
            print("\n💡 Your workers:")
            for worker in config_data.get("workers", []):
                worker_id = worker.get("worker_id", "unknown")
                session = worker.get("session_name", "unknown")
                api_id = worker.get("api_id", "N/A")
                print(f"   • {worker_id}: session={session}, api_id={api_id}")
            print("\n📚 See docs/V0.6_FEATURES.md for more info")
            print("="*60 + "\n")
            return
    except FileNotFoundError:
        print(f"❌ Config file not found: {args.config}")
        return
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in config file: {args.config}")
        return
    
    # Single-worker mode - proceed normally
    try:
        bot = TelegramForwarder(args.config)
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        return
    
    try:
        if args.auth_only:
            print("\n🔐 Authentication Mode")
            print("This will only authenticate and create the session file.\n")
            await bot.client.start()
            print(f"\n✅ Authentication successful!")
            print(f"📁 Session file created: {bot.session_name}.session")
            print(f"🎉 You can now start the bot normally.\n")
            await bot.client.disconnect()
        else:
            await bot.start()
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal. Shutting down gracefully...")
    except Exception as e:
        logger = get_logger()
        logger.critical(f"Fatal error: {type(e).__name__}: {e}", exc_info=True)
        raise
    finally:
        if not args.auth_only:
            await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())

