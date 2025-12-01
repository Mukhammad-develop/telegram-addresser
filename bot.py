"""Main Telegram forwarder bot with multi-channel support."""
import asyncio
import json
import os
import shutil
import sqlite3
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
    
    def __init__(self, config_path_or_dict = "config.json"):
        """
        Initialize TelegramForwarder.
        
        Args:
            config_path_or_dict: Either a file path (str) or a config dict.
        """
        # Load configuration
        self.config_manager = ConfigManager(config_path_or_dict)
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
        
        # Track registered source channels for event handler
        self.registered_source_channels: Set[int] = set()
        
        # Track last received message ID for each channel (for heartbeat monitoring)
        self.last_received_msg_ids: Dict[int, int] = {}
        
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
        
        # Track last processed message ID for each channel (for polling mode)
        self.last_processed_file = Path("last_processed.json")
        self.last_processed_ids: Dict[int, int] = self._load_last_processed()
        
        # Track backfilled pairs to avoid re-backfilling on restart
        # Format: {"source:target": timestamp}
        self.backfill_tracking_file = Path("backfill_tracking.json")
        self.backfilled_pairs: Dict[str, float] = self._load_backfill_tracking()
        
        # Persist message ID mapping for deletion sync (survives restarts)
        self.message_id_map_file = Path("message_id_map.json")
        self.message_id_map: Dict[str, Dict[str, int]] = self._load_message_id_map()
        # Format: {"source_id:message_id": {"target_id": target_msg_id, "timestamp": 123456}}
        
        # File-based trigger for config reload (created by admin bot)
        self.config_reload_trigger_file = Path("trigger_reload.flag")
        
        # Track config file modification time for auto-reload
        self.config_file_mtime = self._get_config_mtime()
        self.last_config_check_time = time.time()
        
        self.logger.info("TelegramForwarder initialized")
    
    def _check_and_clear_session_lock(self, max_wait: int = 30) -> bool:
        """
        Check if session database is locked and wait for it to clear.
        
        Args:
            max_wait: Maximum seconds to wait for lock to clear
            
        Returns:
            True if lock is clear, False if still locked after max_wait
        """
        session_file = Path(f"{self.session_name}.session")
        if not session_file.exists():
            return True
        
        self.logger.info(f"🔍 Checking session file lock: {session_file}")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # Try to open the database in exclusive mode
                conn = sqlite3.connect(str(session_file), timeout=1.0)
                conn.execute("BEGIN EXCLUSIVE")
                conn.execute("COMMIT")
                conn.close()
                self.logger.info("✅ Session file is unlocked")
                return True
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    elapsed = time.time() - start_time
                    if elapsed < max_wait:
                        self.logger.warning(
                            f"⏳ Session file is locked, waiting... ({elapsed:.1f}s/{max_wait}s)"
                        )
                        time.sleep(2)
                    else:
                        self.logger.error(
                            f"❌ Session file still locked after {max_wait}s. "
                            f"This usually means another process is using it or a previous crash left it locked."
                        )
                        return False
                else:
                    # Other database error, assume it's OK
                    return True
            except Exception as e:
                self.logger.warning(f"Unexpected error checking session lock: {e}")
                return True
        
        return False
    
    def _load_last_processed(self) -> Dict[int, int]:
        """Load last processed message IDs from file."""
        if self.last_processed_file.exists():
            try:
                with open(self.last_processed_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to int
                    return {int(k): v for k, v in data.items()}
            except Exception as e:
                self.logger.warning(f"Failed to load last processed IDs: {e}")
        return {}
    
    def _save_last_processed(self) -> None:
        """Save last processed message IDs to file."""
        try:
            # Convert int keys to string for JSON
            data = {str(k): v for k, v in self.last_processed_ids.items()}
            with open(self.last_processed_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save last processed IDs: {e}")
    
    def _load_backfill_tracking(self) -> Dict[str, float]:
        """Load backfill tracking data from file."""
        if self.backfill_tracking_file.exists():
            try:
                with open(self.backfill_tracking_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load backfill tracking: {e}")
        return {}
    
    def _save_backfill_tracking(self) -> None:
        """Save backfill tracking data to file."""
        try:
            with open(self.backfill_tracking_file, 'w') as f:
                json.dump(self.backfilled_pairs, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save backfill tracking: {e}")
    
    def _get_pair_key(self, source: int, target: int) -> str:
        """Generate a unique key for a channel pair."""
        return f"{source}:{target}"
    
    def _get_config_mtime(self) -> float:
        """Get config file modification time."""
        try:
            if self.config_manager.config_path and os.path.exists(self.config_manager.config_path):
                return os.path.getmtime(self.config_manager.config_path)
        except Exception:
            pass
        return 0
    
    def _load_message_id_map(self) -> Dict[str, Dict[str, int]]:
        """Load message ID mapping from file."""
        if self.message_id_map_file.exists():
            try:
                with open(self.message_id_map_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load message ID map: {e}")
        return {}
    
    def _save_message_id_map(self) -> None:
        """Save message ID mapping to file."""
        try:
            with open(self.message_id_map_file, 'w') as f:
                json.dump(self.message_id_map, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save message ID map: {e}")
    
    def _store_message_mapping(self, source: int, source_msg_id: int, target: int, target_msg_id: int) -> None:
        """
        Store message ID mapping for deletion sync and reply chains.
        
        Args:
            source: Source channel ID
            source_msg_id: Source message ID
            target: Target channel ID  
            target_msg_id: Target message ID
        """
        map_key = f"{source}:{source_msg_id}"
        self.message_id_map[map_key] = {
            "target_id": target,
            "target_msg_id": target_msg_id,
            "timestamp": time.time()
        }
        
        # Clean up old mappings (keep last 5000, delete oldest 1000)
        if len(self.message_id_map) > 5000:
            # Sort by timestamp and keep only the newest 4000
            sorted_items = sorted(
                self.message_id_map.items(),
                key=lambda x: x[1].get("timestamp", 0),
                reverse=True
            )
            self.message_id_map = dict(sorted_items[:4000])
            self._save_message_id_map()
            self.logger.debug(f"Cleaned up message ID map, kept 4000 most recent entries")
    
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
    
    # Removed _run_backfill_tasks - no longer needed in polling mode
    


    async def start(self) -> None:
        """Start the bot and set up event handlers."""
        # Check for database lock before starting
        if not self._check_and_clear_session_lock():
            raise RuntimeError(
                f"Session database is locked. This usually means:\n"
                f"1. Another instance of the bot is running with the same session\n"
                f"2. A previous crash left the database locked\n"
                f"3. Multiple workers are trying to use the same session file\n\n"
                f"Solutions:\n"
                f"- Stop all running bot instances\n"
                f"- Wait a few minutes for the lock to clear\n"
                f"- If using multi-worker mode, ensure each worker has a unique session_name\n"
                f"- As a last resort, delete {self.session_name}.session and re-authenticate"
            )
        
        # Connect with retry logic for database lock errors
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                await self.client.start()
                self.logger.info("Bot started successfully")
                break
            except Exception as e:
                error_str = str(e).lower()
                if "database is locked" in error_str or "operationalerror" in error_str:
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"⚠️ Database lock detected (attempt {attempt + 1}/{max_retries}). "
                            f"Waiting {retry_delay}s before retry..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        self.logger.error(
                            f"❌ Failed to start after {max_retries} attempts due to database lock"
                        )
                        raise RuntimeError(
                            f"Session database is locked after {max_retries} attempts. "
                            f"Please stop all running instances and try again."
                        ) from e
                else:
                    # Re-raise non-lock errors immediately
                    raise
        
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
                    f"✓ Access verified: {pair['source']} ({getattr(source_entity, 'title', 'Channel')}) → "
                    f"{pair['target']} ({getattr(target_entity, 'title', 'Channel')})"
                )
            except ValueError as e:
                self.logger.error(
                    f"✗ Cannot access channels {pair['source']} → {pair['target']}. "
                    f"Make sure your account is a member of both channels. Error: {e}"
                )
                continue
        
        self.logger.info("🔄 POLLING MODE: Checking channels every 5 seconds for new messages")
        self.logger.info(f"📡 Will poll {len(source_channels)} source channel(s)")
        self.logger.info(f"📡 Channel IDs: {source_channels}")
        
        # Initialize last processed IDs for new channels
        for source_id in source_channels:
            if source_id not in self.last_processed_ids:
                # Get latest message ID to start from
                try:
                    messages = await self.client.get_messages(source_id, limit=1)
                    if messages:
                        self.last_processed_ids[source_id] = messages[0].id
                        self.logger.info(f"✓ Initialized {source_id} at message ID: {messages[0].id}")
                    else:
                        self.last_processed_ids[source_id] = 0
                        self.logger.warning(f"⚠️  No messages found in {source_id}, starting from 0")
                except Exception as e:
                    self.logger.error(f"❌ Cannot access {source_id}: {type(e).__name__}: {e}")
                    self.last_processed_ids[source_id] = 0
        
        # Save initial state
        self._save_last_processed()
        
        # Check and run backfill for channel pairs that need it
        self.logger.info("📦 Checking if backfill is needed for channel pairs...")
        for pair in channel_pairs:
            if not pair.get("enabled", True):
                continue
            
            source = pair["source"]
            target = pair["target"]
            backfill_count = pair.get("backfill_count", 0)
            pair_key = self._get_pair_key(source, target)
            
            self.logger.info(
                f"📋 Pair: {source} -> {target}, "
                f"backfill_count: {backfill_count}, "
                f"pair_key: {pair_key}"
            )
            
            # Check if this pair has been backfilled before
            if pair_key in self.backfilled_pairs:
                self.logger.info(f"⏭️  SKIPPING - Pair already backfilled: {source} -> {target}")
                continue
            
            # If backfill_count > 0, backfill now
            if backfill_count > 0:
                self.logger.info(f"🔄 BACKFILLING {backfill_count} messages: {source} -> {target}")
                await self.backfill_messages(source, target, backfill_count)
                
                # Mark as backfilled
                self.backfilled_pairs[pair_key] = time.time()
                self._save_backfill_tracking()
                self.logger.info(f"✅ Backfill complete for {source} -> {target}")
            else:
                self.logger.info(f"⏭️  SKIPPING - backfill_count is 0 for {source} -> {target}")
        
        # Register message deletion event handler for all source channels
        if source_channels:
            self.logger.info("🗑️  Registering message deletion handler for sync...")
            @self.client.on(events.MessageDeleted())
            async def handle_message_deleted(event):
                await self._handle_deletion(event)
            self.logger.info(f"✅ Deletion handler registered for {len(source_channels)} source channel(s)")
        
        self.logger.info("Bot is now running. Press Ctrl+C to stop.")
        self.logger.info("🔄 Starting polling loop (checks every 5 seconds)...")
        
        # Start polling task
        polling_task = asyncio.create_task(self._poll_channels())
        
        # Keep the bot running
        try:
            await polling_task
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
    
    async def _poll_channels(self) -> None:
        """
        Continuously poll channels for new messages (polling mode).
        Runs every 5 seconds and forwards new messages.
        """
        # Track processed media groups (to avoid sending albums multiple times)
        processed_groups_in_cycle = set()
        
        while True:
            try:
                await asyncio.sleep(5)  # Poll every 5 seconds
                
                # Check for config reload trigger file OR automatic config change detection
                should_reload = False
                reload_reason = ""
                
                if self.config_reload_trigger_file.exists():
                    should_reload = True
                    reload_reason = "admin bot trigger"
                else:
                    # Check every 2 minutes if config file has been modified
                    current_time = time.time()
                    if current_time - self.last_config_check_time >= 120:  # 120 seconds = 2 minutes
                        self.last_config_check_time = current_time
                        current_mtime = self._get_config_mtime()
                        if current_mtime > self.config_file_mtime:
                            should_reload = True
                            reload_reason = "config file modified"
                            self.config_file_mtime = current_mtime
                
                if should_reload:
                    self.logger.info(f"🔄 Config reload triggered by {reload_reason}")
                    try:
                        # Reload config
                        self.config = self.config_manager.load()
                        self.text_processor.update_rules(self.config_manager.get_replacement_rules())
                        self.logger.info("✅ Config reloaded - new rules/filters active")
                        
                        # Check for NEW channel pairs that need backfilling
                        channel_pairs = self.config_manager.get_channel_pairs()
                        for pair in channel_pairs:
                            if not pair.get("enabled", True):
                                continue
                            
                            source = pair["source"]
                            target = pair["target"]
                            backfill_count = pair.get("backfill_count", 0)
                            pair_key = self._get_pair_key(source, target)
                            
                            # If this is a new pair (not in tracking), backfill it
                            if pair_key not in self.backfilled_pairs and backfill_count > 0:
                                self.logger.info(f"🆕 New pair detected: {source} -> {target}")
                                self.logger.info(f"🔄 Backfilling {backfill_count} messages...")
                                await self.backfill_messages(source, target, backfill_count)
                                
                                # Mark as backfilled
                                self.backfilled_pairs[pair_key] = time.time()
                                self._save_backfill_tracking()
                                self.logger.info(f"✅ New pair backfilled and ready")
                            
                            # Initialize last_processed_ids for new source channels
                            if source not in self.last_processed_ids:
                                try:
                                    msgs = await self.client.get_messages(source, limit=1)
                                    if msgs:
                                        self.last_processed_ids[source] = msgs[0].id
                                        self.logger.info(f"✓ Initialized new channel {source} at message ID: {msgs[0].id}")
                                    else:
                                        self.last_processed_ids[source] = 0
                                except Exception as e:
                                    self.logger.error(f"Cannot access new channel {source}: {e}")
                                    self.last_processed_ids[source] = 0
                        
                        # Remove trigger file if it exists
                        if self.config_reload_trigger_file.exists():
                            self.config_reload_trigger_file.unlink()
                        
                        self.logger.info("✅ Config reload complete, resuming normal operation")
                        
                    except Exception as e:
                        self.logger.error(f"Error during config reload: {e}")
                
                # Clear processed groups from previous cycle
                processed_groups_in_cycle.clear()
                
                channel_pairs = self.config_manager.get_channel_pairs()
                
                for pair in channel_pairs:
                    if not pair.get("enabled", True):
                        continue
                    
                    source = pair["source"]
                    target = pair["target"]
                    
                    try:
                        # Get last processed message ID
                        last_processed = self.last_processed_ids.get(source, 0)
                        
                        # Fetch messages since last processed (up to 100)
                        messages = await self.client.get_messages(
                            source,
                            limit=100,
                            min_id=last_processed
                        )
                        
                        if not messages:
                            continue
                        
                        # Process messages in chronological order (oldest first)
                        for message in reversed(messages):
                            if message.id <= last_processed:
                                continue  # Already processed
                            
                            # Check for media group (album)
                            if message.grouped_id:
                                # Skip if we've already processed this group in this cycle
                                if message.grouped_id in processed_groups_in_cycle:
                                    # Just update last_processed, don't send again
                                    self.last_processed_ids[source] = message.id
                                    continue
                                
                                # Mark this group as processed
                                processed_groups_in_cycle.add(message.grouped_id)
                            
                            # Forward the message
                            try:
                                await self.forward_message_with_retry(
                                    message,
                                    source,
                                    target,  # Single target ID, not a list
                                    is_backfill=False
                                )
                                
                                # Update last processed
                                self.last_processed_ids[source] = message.id
                                
                            except Exception as forward_error:
                                self.logger.error(
                                    f"Failed to forward message {message.id} from {source} to {target}: {forward_error}"
                                )
                                # Continue with next message even if one fails
                        
                        # Save state after processing each channel
                        self._save_last_processed()
                        
                    except Exception as e:
                        self.logger.error(f"Error polling channel {source}: {type(e).__name__}: {e}")
                        continue
                
            except asyncio.CancelledError:
                self.logger.info("🔄 Polling loop stopped")
                break
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                # Continue polling even if one iteration fails
                await asyncio.sleep(5)
    
    async def _handle_deletion(self, event) -> None:
        """
        Handle message deletion events and sync deletions to target channels.
        
        Args:
            event: Telethon MessageDeleted event
        """
        try:
            # Get the channel where deletion occurred
            if hasattr(event, 'chat_id') and event.chat_id:
                source_channel = event.chat_id
            elif hasattr(event, 'peer') and event.peer:
                # Try to extract channel ID from peer
                source_channel = event.peer.channel_id if hasattr(event.peer, 'channel_id') else None
                if source_channel:
                    source_channel = int(f"-100{source_channel}")
            else:
                self.logger.debug("Deletion event without identifiable channel, skipping")
                return
            
            # Get deleted message IDs
            deleted_ids = event.deleted_ids if hasattr(event, 'deleted_ids') else []
            
            if not deleted_ids:
                self.logger.debug("Deletion event without message IDs, skipping")
                return
            
            self.logger.info(f"🗑️  Detected deletion of {len(deleted_ids)} message(s) in {source_channel}")
            
            # Check if this source channel is in our monitored pairs
            channel_pairs = self.config_manager.get_channel_pairs()
            target_channels = []
            for pair in channel_pairs:
                if pair["source"] == source_channel and pair.get("enabled", True):
                    target_channels.append(pair["target"])
            
            if not target_channels:
                self.logger.debug(f"Source channel {source_channel} not in monitored pairs, ignoring deletion")
                return
            
            # Delete corresponding messages in target channels
            deletion_count = 0
            for source_msg_id in deleted_ids:
                map_key = f"{source_channel}:{source_msg_id}"
                
                if map_key in self.message_id_map:
                    mapping = self.message_id_map[map_key]
                    target_channel = mapping.get("target_id")
                    target_msg_id = mapping.get("target_msg_id")
                    
                    if target_channel and target_msg_id:
                        try:
                            # Delete the message in target channel
                            await self.client.delete_messages(target_channel, target_msg_id)
                            deletion_count += 1
                            self.logger.info(
                                f"🗑️  ✅ Deleted message {target_msg_id} in {target_channel} "
                                f"(source: {source_msg_id} from {source_channel})"
                            )
                            
                            # Remove from mapping
                            del self.message_id_map[map_key]
                            self._save_message_id_map()
                            
                        except Exception as del_error:
                            self.logger.warning(
                                f"🗑️  ❌ Failed to delete message {target_msg_id} in {target_channel}: "
                                f"{type(del_error).__name__}: {del_error}"
                            )
                else:
                    self.logger.debug(
                        f"🗑️  Message {source_msg_id} from {source_channel} not found in mapping "
                        f"(may be older than map retention or never forwarded)"
                    )
            
            if deletion_count > 0:
                self.logger.info(f"🗑️  Successfully synced {deletion_count}/{len(deleted_ids)} deletion(s)")
        
        except Exception as e:
            self.logger.error(f"Error handling deletion event: {type(e).__name__}: {e}", exc_info=True)
    
    async def handle_new_message(self, event) -> None:
        """
        Handle incoming new messages and copy them (without "Forwarded from" tag).
        
        Args:
            event: Telethon NewMessage event
        """
        try:
            # Track timing for delay analysis
            import time as time_module
            start_time = time_module.time()
            
            message = event.message
            source_chat_id = event.chat_id
            
            # DEBUG: Log ALL received messages to verify event handler is working
            self.logger.info(f"🔔 [DEBUG] Event handler triggered: msg {message.id} from {source_chat_id}")
            
            # Filter: Only process messages from registered source channels
            if source_chat_id not in self.registered_source_channels:
                # Ignore messages from channels we're not monitoring
                self.logger.info(f"⏭️  [DEBUG] Skipping message from unmonitored channel: {source_chat_id}")
                return
            
            # Track this message for heartbeat monitoring
            self.last_received_msg_ids[source_chat_id] = message.id
            
            self.logger.info(f"⏱️ [TIMING] Message {message.id} received from {source_chat_id} at {start_time}")
            
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
                self.logger.debug(f"No target channel configured for source {source_chat_id}")
                return
            
            self.logger.info(f"📨 Processing message {message.id} from {source_chat_id} -> {targets}")
            
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
        
        except Exception as e:
            self.logger.error(
                f"❌ Error in handle_new_message for message {getattr(event.message, 'id', 'unknown')}: "
                f"{type(e).__name__}: {e}", 
                exc_info=True
            )
    
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
                    mapping = self.message_id_map.get(map_key)
                    if mapping:
                        reply_to = mapping.get("target_msg_id")
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
                        
                        # Store message ID mapping for reply chains and deletion sync
                        if sent_msg:
                            self._store_message_mapping(source, message.id, target, sent_msg.id)
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
                            
                            # For media groups, Telethon will auto-detect video/photo types
                            # But we can pass force_document=False to ensure proper handling
                            sent_msg = await self.client.send_file(
                                target,
                                media_files,
                                caption=group_text if group_text else None,
                                reply_to=reply_to,
                                formatting_entities=formatting_entities,
                                force_document=False
                            )
                            
                            # Store message ID mapping for reply chains and deletion sync
                            if sent_msg:
                                # For media groups, sent_msg might be a list
                                if isinstance(sent_msg, list):
                                    # Map the first message in group (which has the caption)
                                    self._store_message_mapping(source, message.id, target, sent_msg[0].id)
                                else:
                                    self._store_message_mapping(source, message.id, target, sent_msg.id)
                            
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
                        
                        # Store message ID mapping for reply chains and deletion sync
                        if sent_msg:
                            self._store_message_mapping(source, message.id, target, sent_msg.id)
                        
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
                            
                            # Extract media attributes from original message to preserve video/photo properties
                            attributes = None
                            force_document = False
                            if hasattr(message.media, 'document') and message.media.document:
                                # This is a document (video, gif, etc.) - preserve attributes
                                attributes = message.media.document.attributes
                            
                            sent_msg = await self.client.send_file(
                                target,
                                file_path,
                                caption=text if text else None,
                                reply_to=reply_to,
                                formatting_entities=formatting_entities,
                                attributes=attributes,
                                force_document=force_document
                            )
                            
                            # Store message ID mapping for reply chains and deletion sync
                            if sent_msg:
                                self._store_message_mapping(source, message.id, target, sent_msg.id)
                            
                            # Clean up downloaded file
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                self.logger.warning(f"Failed to delete {file_path}: {e}")
                        else:
                            raise Exception("Download returned None")
                    
                    except Exception as download_error:
                        # If download fails, try direct send with original media
                        self.logger.warning(f"Download failed, trying direct send: {download_error}")
                        # Preserve entities ONLY if text wasn't modified
                        formatting_entities = None
                        if not text_was_modified and hasattr(message, 'entities'):
                            formatting_entities = message.entities
                        
                        # Use send_file for better media handling instead of send_message
                        await self.client.send_file(
                            target,
                            message.media,
                            caption=text if text else None,
                            reply_to=reply_to,
                            formatting_entities=formatting_entities,
                            force_document=False
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
                    
                    # Store message ID mapping for reply chains and deletion sync
                    if sent_msg:
                        self._store_message_mapping(source, message.id, target, sent_msg.id)
                
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
    
    def mark_pair_for_backfill(self, source: int, target: int) -> None:
        """
        Mark a channel pair for backfill (removes from backfilled pairs).
        This is useful when a new pair is added and needs to be backfilled.
        
        Args:
            source: Source channel ID
            target: Target channel ID
        """
        pair_key = self._get_pair_key(source, target)
        if pair_key in self.backfilled_pairs:
            del self.backfilled_pairs[pair_key]
            self._save_backfill_tracking()
            self.logger.info(f"📍 Marked pair for backfill: {source} -> {target}")
    
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

