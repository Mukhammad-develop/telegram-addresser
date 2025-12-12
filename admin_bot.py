"""Telegram Bot Admin Panel for managing the forwarder configuration."""
import telebot
from telebot import types
import json
import os
import time
import asyncio
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError, PhoneMigrateError
from src.config_manager import ConfigManager
from worker_manager import WorkerManager, WorkerProcess

# Load configuration
config_manager = ConfigManager()
config = config_manager.load()

# Get bot token from config or environment
ADMIN_BOT_TOKEN = config.get("admin_bot_token", "") or os.getenv("ADMIN_BOT_TOKEN", "")
ADMIN_USER_IDS = config.get("admin_user_ids", [])

# Validate token
if not ADMIN_BOT_TOKEN or ADMIN_BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
    print("\n" + "="*60)
    print("⚠️  ADMIN BOT TOKEN NOT CONFIGURED")
    print("="*60)
    print("\n📝 To set up the admin bot:\n")
    print("1. Message @BotFather on Telegram")
    print("2. Send /newbot")
    print("3. Follow instructions and get your token")
    print("4. Add to config.json:")
    print('   "admin_bot_token": "YOUR_TOKEN_HERE",')
    print('   "admin_user_ids": [YOUR_USER_ID]')
    print("\n5. Get your user ID from @userinfobot")
    print("\n📖 See docs/TELEGRAM_ADMIN_BOT.md for full guide")
    print("="*60 + "\n")
    exit(1)

# Initialize bot
bot = telebot.TeleBot(ADMIN_BOT_TOKEN)

# Temporary storage for multi-step operations (chat_id -> data)
temp_storage = {}

# Global worker manager instance (created on demand)
worker_manager_instance = None

def get_worker_manager():
    """Get or create worker manager instance."""
    global worker_manager_instance
    if worker_manager_instance is None:
        worker_manager_instance = WorkerManager()
        worker_manager_instance.load_workers_from_config()
    return worker_manager_instance

if not ADMIN_USER_IDS:
    print("\n⚠️  WARNING: No admin users configured!")
    print("Please add your Telegram user ID to config.json:")
    print('"admin_user_ids": [YOUR_USER_ID]')
    print("\nTo get your user ID, message @userinfobot on Telegram")


def is_admin(user_id):
    """Check if user is admin."""
    return user_id in ADMIN_USER_IDS or len(ADMIN_USER_IDS) == 0


def main_menu_keyboard():
    """Create main menu keyboard."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📡 Channel Pairs", callback_data="menu_channels"),
        types.InlineKeyboardButton("🔄 Replacement Rules", callback_data="menu_rules"),
        types.InlineKeyboardButton("🔍 Filters", callback_data="menu_filters"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        types.InlineKeyboardButton("👷 Workers", callback_data="menu_workers"),
        types.InlineKeyboardButton("📊 Status", callback_data="menu_status"),
        types.InlineKeyboardButton("🔄 Reload Config", callback_data="reload_config")
    )
    return markup


@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    """Send welcome message with main menu."""
    # Clear any pending step handlers first (cancel ongoing operations)
    bot.clear_step_handler_by_chat_id(message.chat.id)
    
    # Clear any temporary storage for this user
    if message.chat.id in temp_storage:
        temp_storage.pop(message.chat.id)
    
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ You are not authorized to use this bot.")
        return
    
    welcome_text = """
🚀 <b>Telegram Forwarder Admin Panel</b>

Welcome! Use the buttons below to manage your forwarder bot.

<b>Available Commands:</b>
/start - Show this menu (also cancels ongoing operations)
/status - Check bot status
/help - Get help
    """
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main(call):
    """Return to main menu."""
    bot.edit_message_text(
        "🚀 <b>Main Menu</b>\n\nSelect an option:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )


# ========== CHANNEL PAIRS ==========

@bot.callback_query_handler(func=lambda call: call.data == "menu_channels")
def show_channels(call):
    """Show channel pairs - check if multi-worker mode first."""
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    # Multi-worker mode: ask which worker
    if workers_config:
        text = "📡 <b>Channel Pairs</b>\n\n"
        text += "Select a worker to manage its channel pairs:\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for worker_cfg in workers_config:
            worker_id = worker_cfg["worker_id"]
            pairs_count = len(worker_cfg.get("channel_pairs", []))
            button_text = f"👷 {worker_id} ({pairs_count} pairs)"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f"channels_worker_{worker_id}"))
        
        markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        return
    
    # Single-worker mode: show global pairs
    pairs = config_manager.get_all_channel_pairs()
    
    text = "📡 <b>Channel Pairs</b>\n\n"
    
    if pairs:
        for i, pair in enumerate(pairs):
            status = "✅" if pair.get("enabled", True) else "❌"
            text += f"{status} <b>Pair {i+1}</b>\n"
            text += f"  Source: <code>{pair['source']}</code>\n"
            text += f"  Target: <code>{pair['target']}</code>\n"
            text += f"  Backfill: {pair.get('backfill_count', 0)}\n\n"
    else:
        text += "No channel pairs configured yet.\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Pair", callback_data="add_channel_pair"),
        types.InlineKeyboardButton("🗑️ Remove Pair", callback_data="remove_channel_pair")
    )
    if pairs:
        markup.add(types.InlineKeyboardButton("🔄 Toggle Pair", callback_data="toggle_channel_pair"))
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("channels_worker_"))
def show_worker_channels(call):
    """Show channel pairs for a specific worker."""
    worker_id = call.data.replace("channels_worker_", "")
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
    
    if not worker_cfg:
        bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
        return
    
    # Store selected worker in temp storage
    temp_storage[call.message.chat.id] = {"selected_worker_id": worker_id}
    
    pairs = worker_cfg.get("channel_pairs", [])
    
    text = f"📡 <b>Channel Pairs - {worker_id}</b>\n\n"
    
    if pairs:
        for i, pair in enumerate(pairs):
            status = "✅" if pair.get("enabled", True) else "❌"
            text += f"{status} <b>Pair {i+1}</b>\n"
            text += f"  Source: <code>{pair['source']}</code>\n"
            text += f"  Target: <code>{pair['target']}</code>\n"
            text += f"  Backfill: {pair.get('backfill_count', 0)}\n\n"
    else:
        text += "No channel pairs configured yet.\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Pair", callback_data="add_channel_pair"),
        types.InlineKeyboardButton("🗑️ Remove Pair", callback_data="remove_channel_pair")
    )
    if pairs:
        markup.add(types.InlineKeyboardButton("🔄 Toggle Pair", callback_data="toggle_channel_pair"))
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="menu_channels"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "add_channel_pair")
def add_channel_pair_start(call):
    """Start adding channel pair."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_channels"))
    
    bot.edit_message_text(
        "📡 <b>Add Channel Pair</b>\n\n"
        "Please send channel IDs in this format:\n"
        "<code>source_id target_id backfill_count</code>\n\n"
        "Example:\n"
        "<code>-1001234567890 -1009876543210 10</code>\n\n"
        "To get channel IDs, forward a message from the channel to @userinfobot\n\n"
        "💡 Tip: Send /start to cancel",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.register_next_step_handler(call.message, process_add_channel_pair)


def process_add_channel_pair(message):
    """Process channel pair addition."""
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Invalid format. Please send: source_id target_id [backfill_count]")
            return
        
        source = int(parts[0])
        target = int(parts[1])
        backfill = int(parts[2]) if len(parts) > 2 else 10
        
        # Auto-fix: Ensure channel IDs have -100 prefix for supergroups/channels
        if source > 0:
            source = int(f"-100{source}")
        elif source < 0 and not str(source).startswith("-100"):
            source = int(f"-100{abs(source)}")
        
        if target > 0:
            target = int(f"-100{target}")
        elif target < 0 and not str(target).startswith("-100"):
            target = int(f"-100{abs(target)}")
        
        # Check if multi-worker mode
        config_manager.load()
        config = config_manager.config
        workers_config = config.get("workers", [])
        
        if workers_config:
            # Multi-worker mode: add to selected worker
            selected_worker_id = temp_storage.get(message.chat.id, {}).get("selected_worker_id")
            
            if not selected_worker_id:
                bot.reply_to(message, "❌ Error: No worker selected. Please try again from the menu.")
                return
            
            # Find worker and add pair
            worker_found = False
            for worker in workers_config:
                if worker["worker_id"] == selected_worker_id:
                    if "channel_pairs" not in worker:
                        worker["channel_pairs"] = []
                    worker["channel_pairs"].append({
                        "source": source,
                        "target": target,
                        "enabled": True,
                        "backfill_count": backfill
                    })
                    worker_found = True
                    break
            
            if not worker_found:
                bot.reply_to(message, f"❌ Worker '{selected_worker_id}' not found.")
                return
            
            config_manager.config = config
            config_manager.save()
            
            # Mark pair for backfill by removing it from backfill_tracking.json
            backfill_tracking_file = Path("backfill_tracking.json")
            try:
                if backfill_tracking_file.exists():
                    with open(backfill_tracking_file, 'r') as f:
                        backfill_tracking = json.load(f)
                else:
                    backfill_tracking = {}
                
                # Remove the pair key if it exists (to trigger backfill)
                pair_key = f"{source}:{target}"
                if pair_key in backfill_tracking:
                    del backfill_tracking[pair_key]
                    
                    with open(backfill_tracking_file, 'w') as f:
                        json.dump(backfill_tracking, f, indent=2)
            except Exception as e:
                logger.warning(f"Could not update backfill tracking: {e}")
            
            worker_msg = f" to <b>{selected_worker_id}</b>"
        else:
            # Single-worker mode: use old method
            config_manager.add_channel_pair(source, target, backfill)
            worker_msg = ""
        
        # Create trigger file to reload config
        trigger_file = Path("trigger_reload.flag")
        try:
            trigger_file.touch()
            auto_backfill_msg = "🔔 <b>Config reloaded!</b> The bot will detect the new pair within 5 seconds and start forwarding messages automatically."
        except Exception as e:
            auto_backfill_msg = f"⚠️ Could not create trigger file. Please restart: <code>./start.sh</code>"
        
        bot.reply_to(
            message,
            f"✅ <b>Channel pair added{worker_msg}!</b>\n\n"
            f"Source: <code>{source}</code>\n"
            f"Target: <code>{target}</code>\n"
            f"Backfill: {backfill}\n\n"
            f"{auto_backfill_msg}",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    except ValueError:
        bot.reply_to(message, "❌ Invalid channel IDs. They must be numbers.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "remove_channel_pair")
def remove_channel_pair_start(call):
    """Start removing channel pair."""
    config_manager.load()
    config = config_manager.config
    
    # Check if multi-worker mode
    is_multiworker = "workers" in config and isinstance(config.get("workers"), list)
    
    if is_multiworker:
        # Get selected worker from temp storage
        data = temp_storage.get(call.message.chat.id, {})
        worker_id = data.get("selected_worker_id")
        
        if not worker_id:
            bot.answer_callback_query(call.id, "⚠️ No worker selected", show_alert=True)
            return
        
        # Get worker's channel pairs
        workers_config = config.get("workers", [])
        worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
        
        if not worker_cfg:
            bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
            return
        
        pairs = worker_cfg.get("channel_pairs", [])
        worker_msg = f" for {worker_id}"
    else:
        # Single-worker mode
        pairs = config_manager.get_all_channel_pairs()
        worker_msg = ""
    
    if not pairs:
        bot.answer_callback_query(call.id, "No pairs to remove!")
        return
    
    text = f"🗑️ <b>Remove Channel Pair{worker_msg}</b>\n\n"
    text += "Send the pair number to remove:\n\n"
    
    for i, pair in enumerate(pairs):
        text += f"{i+1}. {pair['source']} → {pair['target']}\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.register_next_step_handler(call.message, process_remove_channel_pair)


def process_remove_channel_pair(message):
    """Process channel pair removal."""
    try:
        index = int(message.text.strip()) - 1
        
        config_manager.load()
        config = config_manager.config
        
        # Check if multi-worker mode
        is_multiworker = "workers" in config and isinstance(config.get("workers"), list)
        
        if is_multiworker:
            # Get selected worker from temp storage
            data = temp_storage.get(message.chat.id, {})
            worker_id = data.get("selected_worker_id")
            
            if not worker_id:
                bot.reply_to(message, "❌ Session expired. Please try again.")
                return
            
            # Get worker's channel pairs
            workers_config = config.get("workers", [])
            worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
            
            if not worker_cfg:
                bot.reply_to(message, "❌ Worker not found")
                return
            
            pairs = worker_cfg.get("channel_pairs", [])
            
            if index < 0 or index >= len(pairs):
                bot.reply_to(message, "❌ Invalid pair number")
                return
            
            # Remove the pair
            removed_pair = pairs.pop(index)
            worker_cfg["channel_pairs"] = pairs
            config_manager.config = config
            config_manager.save()
            
            worker_msg = f" from {worker_id}"
        else:
            # Single-worker mode
            config_manager.remove_channel_pair(index)
            worker_msg = ""
        
        bot.reply_to(
            message,
            f"✅ Channel pair removed{worker_msg}! Restart the forwarder bot to apply changes.",
            reply_markup=main_menu_keyboard()
        )
    except ValueError:
        bot.reply_to(message, "❌ Invalid number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "toggle_channel_pair")
def toggle_channel_pair_start(call):
    """Start toggling channel pair."""
    config_manager.load()
    config = config_manager.config
    
    # Check if multi-worker mode
    is_multiworker = "workers" in config and isinstance(config.get("workers"), list)
    
    if is_multiworker:
        # Get selected worker from temp storage
        data = temp_storage.get(call.message.chat.id, {})
        worker_id = data.get("selected_worker_id")
        
        if not worker_id:
            bot.answer_callback_query(call.id, "⚠️ No worker selected", show_alert=True)
            return
        
        # Get worker's channel pairs
        workers_config = config.get("workers", [])
        worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
        
        if not worker_cfg:
            bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
            return
        
        pairs = worker_cfg.get("channel_pairs", [])
        worker_msg = f" for {worker_id}"
    else:
        # Single-worker mode
        pairs = config_manager.get_all_channel_pairs()
        worker_msg = ""
    
    text = f"🔄 <b>Toggle Channel Pair{worker_msg}</b>\n\n"
    text += "Send the pair number to toggle:\n\n"
    
    for i, pair in enumerate(pairs):
        status = "✅ Enabled" if pair.get("enabled", True) else "❌ Disabled"
        text += f"{i+1}. {pair['source']} → {pair['target']} ({status})\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.register_next_step_handler(call.message, process_toggle_channel_pair)


def process_toggle_channel_pair(message):
    """Process channel pair toggle."""
    try:
        index = int(message.text.strip()) - 1
        
        config_manager.load()
        config = config_manager.config
        
        # Check if multi-worker mode
        is_multiworker = "workers" in config and isinstance(config.get("workers"), list)
        
        if is_multiworker:
            # Get selected worker from temp storage
            data = temp_storage.get(message.chat.id, {})
            worker_id = data.get("selected_worker_id")
            
            if not worker_id:
                bot.reply_to(message, "❌ Session expired. Please try again.")
                return
            
            # Get worker's channel pairs
            workers_config = config.get("workers", [])
            worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
            
            if not worker_cfg:
                bot.reply_to(message, "❌ Worker not found")
                return
            
            pairs = worker_cfg.get("channel_pairs", [])
            
            if index < 0 or index >= len(pairs):
                bot.reply_to(message, "❌ Invalid pair number")
                return
            
            # Toggle the pair
            current = pairs[index].get("enabled", True)
            pairs[index]["enabled"] = not current
            worker_cfg["channel_pairs"] = pairs
            config_manager.config = config
            config_manager.save()
            
            worker_msg = f" in {worker_id}"
        else:
            # Single-worker mode
            pairs = config_manager.get_all_channel_pairs()
            current = pairs[index].get("enabled", True)
            config_manager.update_channel_pair(index, enabled=not current)
            worker_msg = ""
        
        status = "disabled" if current else "enabled"
        bot.reply_to(
            message,
            f"✅ Channel pair {status}{worker_msg}! Restart the forwarder bot to apply changes.",
            reply_markup=main_menu_keyboard()
        )
    except (ValueError, IndexError):
        bot.reply_to(message, "❌ Invalid pair number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


# ========== REPLACEMENT RULES ==========

@bot.callback_query_handler(func=lambda call: call.data == "menu_rules")
def show_rules(call):
    """Show replacement rules - check if multi-worker mode first."""
    # Clear any temporary storage when navigating to menu
    if call.message.chat.id in temp_storage:
        temp_storage.pop(call.message.chat.id)
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    # Multi-worker mode: ask which worker
    if workers_config:
        text = "🔄 <b>Replacement Rules</b>\n\n"
        text += "Select a worker to manage its replacement rules:\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for worker_cfg in workers_config:
            worker_id = worker_cfg["worker_id"]
            rules_count = len(worker_cfg.get("replacement_rules", []))
            button_text = f"👷 {worker_id} ({rules_count} rules)"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f"rules_worker_{worker_id}"))
        
        markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        return
    
    # Single-worker mode
    rules = config_manager.get_replacement_rules()
    
    text = "🔄 <b>Replacement Rules</b>\n\n"
    
    if rules:
        for i, rule in enumerate(rules):
            case = "Case-sensitive" if rule.get("case_sensitive") else "Case-insensitive"
            regex = " | 🔣 Regex" if rule.get("is_regex") else ""
            text += f"<b>Rule {i+1}</b> ({case}{regex})\n"
            text += f"  Find: <code>{rule['find']}</code>\n"
            text += f"  Replace: <code>{rule['replace']}</code>\n\n"
    else:
        text += "No replacement rules configured.\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Rule", callback_data="add_rule"),
        types.InlineKeyboardButton("🗑️ Remove Rule", callback_data="remove_rule")
    )
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("rules_worker_"))
def show_worker_rules(call):
    """Show replacement rules for a specific worker."""
    try:
        worker_id = call.data.replace("rules_worker_", "")
        
        config_manager.load()
        config = config_manager.config
        workers_config = config.get("workers", [])
        
        worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
        
        if not worker_cfg:
            bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
            return
        
        # Store selected worker in temp storage
        temp_storage[call.message.chat.id] = {"selected_worker_id": worker_id}
        
        rules = worker_cfg.get("replacement_rules", [])
        
        text = f"🔄 <b>Replacement Rules - {worker_id}</b>\n\n"
        
        if rules:
            for i, rule in enumerate(rules):
                case = "Case-sensitive" if rule.get("case_sensitive") else "Case-insensitive"
                regex = " | 🔣 Regex" if rule.get("is_regex") else ""
                text += f"<b>Rule {i+1}</b> ({case}{regex})\n"
                text += f"  Find: <code>{rule['find']}</code>\n"
                text += f"  Replace: <code>{rule['replace']}</code>\n\n"
        else:
            text += "No replacement rules configured.\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ Add Rule", callback_data="add_rule"),
            types.InlineKeyboardButton("🗑️ Remove Rule", callback_data="remove_rule")
        )
        markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="menu_rules"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)  # Acknowledge button click
    except Exception as e:
        import traceback
        print(f"ERROR in show_worker_rules: {e}")
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "add_rule")
def add_rule_start(call):
    """Start adding replacement rule - step 1: ask for find text."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_rules"))
    
    bot.edit_message_text(
        "🔄 <b>Add Replacement Rule - Step 1/4</b>\n\n"
        "What text should I <b>find</b> in messages?\n\n"
        "Example: <code>Elite</code> or <code>https://old.com</code>\n"
        "Regex example: <code>https://t\\.me/c/123/\\d+</code>\n\n"
        "Send the text you want to find:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    bot.register_next_step_handler(call.message, process_add_rule_step1)


def process_add_rule_step1(message):
    """Process step 1: got find text, ask for replace text."""
    try:
        print(f"\n[STEP 1] User {message.chat.id} sent: {message.text}")
        
        if message.text.startswith('/'):
            # User sent a command, don't process
            print(f"[STEP 1] Ignoring command: {message.text}")
            return
        
        find_text = message.text.strip()
        if not find_text:
            print(f"[STEP 1] Empty text received")
            bot.reply_to(message, "❌ Text cannot be empty. Try again.", reply_markup=main_menu_keyboard())
            return
        
        print(f"[STEP 1] Find text stored: '{find_text}'")
        
        # Store in a temporary way - using message
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_rules"))
        
        msg = bot.send_message(
            message.chat.id,
            f"🔄 <b>Add Replacement Rule - Step 2/4</b>\n\n"
            f"Find: <code>{find_text}</code>\n\n"
            f"What text should I <b>replace</b> it with?\n\n"
            f"Example: <code>Premium</code> or <code>https://new.com</code>\n\n"
            f"Send the replacement text:",
            parse_mode='HTML',
            reply_markup=markup
        )
        
        print(f"[STEP 1] Moving to step 2, waiting for replacement text...")
        
        # Pass find_text to next step
        bot.register_next_step_handler(msg, process_add_rule_step2, find_text)
    except Exception as e:
        print(f"[STEP 1] ERROR: {str(e)}")
        bot.reply_to(message, f"❌ Error: {str(e)}", reply_markup=main_menu_keyboard())


def process_add_rule_step2(message, find_text):
    """Process step 2: got replace text, ask for case sensitivity."""
    try:
        print(f"\n[STEP 2] User {message.chat.id} sent: {message.text}")
        print(f"[STEP 2] Find text from step 1: '{find_text}'")
        
        if message.text.startswith('/'):
            print(f"[STEP 2] Ignoring command: {message.text}")
            return
        
        replace_text = message.text.strip()
        if not replace_text:
            print(f"[STEP 2] Empty text received")
            bot.reply_to(message, "❌ Text cannot be empty. Try again.", reply_markup=main_menu_keyboard())
            return
        
        print(f"[STEP 2] Replace text: '{replace_text}'")
        
        # Store data temporarily for this chat
        temp_storage[message.chat.id] = {
            'find_text': find_text,
            'replace_text': replace_text
        }
        
        print(f"[STEP 2] Stored in temp_storage for chat {message.chat.id}")
        print(f"[STEP 2] temp_storage contents: {temp_storage}")
        
        # Ask for case sensitivity with buttons (simple callback data now)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Yes", callback_data="rule_case_yes"),
            types.InlineKeyboardButton("❌ No", callback_data="rule_case_no")
        )
        markup.add(types.InlineKeyboardButton("🔙 Cancel", callback_data="menu_rules"))
        
        bot.send_message(
            message.chat.id,
            f"🔄 <b>Add Replacement Rule - Step 3/4</b>\n\n"
            f"Find: <code>{find_text}</code>\n"
            f"Replace: <code>{replace_text}</code>\n\n"
            f"Should matching be <b>case-sensitive</b>?\n\n"
            f"• <b>Yes</b> = 'Elite' matches only 'Elite'\n"
            f"• <b>No</b> = 'Elite' matches 'elite', 'ELITE', etc.",
            parse_mode='HTML',
            reply_markup=markup
        )
        
        print(f"[STEP 2] Waiting for Yes/No button click...")
    except Exception as e:
        print(f"[STEP 2] ERROR: {str(e)}")
        bot.reply_to(message, f"❌ Error: {str(e)}", reply_markup=main_menu_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith("rule_case_"))
def ask_regex(call):
    """Ask if the rule is a regex pattern."""
    try:
        print(f"\n[STEP 3] Button clicked: {call.data}")
        print(f"[STEP 3] User: {call.message.chat.id}")
        
        # Get stored data for this chat
        chat_id = call.message.chat.id
        
        print(f"[STEP 3] Checking temp_storage...")
        print(f"[STEP 3] Current temp_storage: {temp_storage}")
        
        if chat_id not in temp_storage:
            print(f"[STEP 3] ERROR: No data in temp_storage for chat {chat_id}")
            bot.answer_callback_query(call.id, "❌ Session expired. Please start again.")
            return
        
        # Store case sensitivity in temp storage
        temp_storage[chat_id]['case_sensitive'] = (call.data == "rule_case_yes")
        
        find_text = temp_storage[chat_id]['find_text']
        replace_text = temp_storage[chat_id]['replace_text']
        case_sensitive = temp_storage[chat_id]['case_sensitive']
        
        print(f"[STEP 3] Current data:")
        print(f"  - Find: '{find_text}'")
        print(f"  - Replace: '{replace_text}'")
        print(f"  - Case-sensitive: {case_sensitive}")
        
        # Ask for regex with buttons
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Yes (Regex)", callback_data="rule_regex_yes"),
            types.InlineKeyboardButton("❌ No (Exact)", callback_data="rule_regex_no")
        )
        markup.add(types.InlineKeyboardButton("🔙 Cancel", callback_data="menu_rules"))
        
        bot.edit_message_text(
            f"🔄 <b>Add Replacement Rule - Step 4/4</b>\n\n"
            f"Find: <code>{find_text}</code>\n"
            f"Replace: <code>{replace_text}</code>\n"
            f"Case-sensitive: {'Yes' if case_sensitive else 'No'}\n\n"
            f"Is this a <b>regex pattern</b>?\n\n"
            f"• <b>Yes (Regex)</b> = Pattern like <code>https://t\\.me/c/123/\\d+</code>\n"
            f"• <b>No (Exact)</b> = Exact text like <code>hello world</code>\n\n"
            f"⚠️ <i>Note: Regex replacements may break emoji/formatting</i>",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
        print(f"[STEP 3] Waiting for regex Yes/No button click...")
    except Exception as e:
        print(f"[STEP 3] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
        # Clean up storage on error
        if call.message.chat.id in temp_storage:
            temp_storage.pop(call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("rule_regex_"))
def finish_add_rule(call):
    """Finish adding rule with regex choice."""
    try:
        print(f"\n[STEP 4] Button clicked: {call.data}")
        print(f"[STEP 4] User: {call.message.chat.id}")
        
        # Get stored data for this chat
        chat_id = call.message.chat.id
        
        print(f"[STEP 4] Checking temp_storage...")
        print(f"[STEP 4] Current temp_storage: {temp_storage}")
        
        if chat_id not in temp_storage:
            print(f"[STEP 4] ERROR: No data in temp_storage for chat {chat_id}")
            bot.answer_callback_query(call.id, "❌ Session expired. Please start again.")
            return
        
        data = temp_storage.pop(chat_id)  # Get and remove from storage
        find_text = data['find_text']
        replace_text = data['replace_text']
        case_sensitive = data['case_sensitive']
        is_regex = call.data == "rule_regex_yes"
        
        print(f"[STEP 4] Retrieved data:")
        print(f"  - Find: '{find_text}'")
        print(f"  - Replace: '{replace_text}'")
        print(f"  - Case-sensitive: {case_sensitive}")
        print(f"  - Is regex: {is_regex}")
        
        print(f"[STEP 4] Saving rule to config...")
        # Get selected worker_id if in multi-worker mode
        worker_id = data.get("selected_worker_id")
        config_manager.add_replacement_rule(find_text, replace_text, case_sensitive, is_regex, worker_id=worker_id)
        print(f"[STEP 4] Rule saved successfully! Worker: {worker_id if worker_id else 'single-worker'}")
        
        # Verify it was saved
        config_manager.load()
        rules = config_manager.get_replacement_rules()
        print(f"[STEP 4] Total rules in config now: {len(rules)}")
        print(f"[STEP 4] Last rule: {rules[-1] if rules else 'None'}")
        
        bot.edit_message_text(
            f"✅ <b>Replacement rule added successfully!</b>\n\n"
            f"Find: <code>{find_text}</code>\n"
            f"Replace: <code>{replace_text}</code>\n"
            f"Case-sensitive: {'Yes' if case_sensitive else 'No'}\n"
            f"Regex: {'Yes' if is_regex else 'No'}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
        bot.answer_callback_query(call.id, "✅ Rule added!")
        print(f"[STEP 4] Complete!\n")
    except Exception as e:
        print(f"[STEP 4] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
        # Clean up storage on error
        if call.message.chat.id in temp_storage:
            temp_storage.pop(call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == "remove_rule")
def remove_rule_start(call):
    """Start removing rule."""
    try:
        config_manager.load()
        config = config_manager.config
        
        # Check if multi-worker mode
        is_multiworker = "workers" in config and isinstance(config.get("workers"), list)
        
        if is_multiworker:
            # Get selected worker from temp storage
            data = temp_storage.get(call.message.chat.id, {})
            worker_id = data.get("selected_worker_id")
            
            if not worker_id:
                bot.answer_callback_query(call.id, "⚠️ No worker selected", show_alert=True)
                return
            
            # Get worker's rules
            workers_config = config.get("workers", [])
            worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
            
            if not worker_cfg:
                bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
                return
            
            rules = worker_cfg.get("replacement_rules", [])
            worker_msg = f" for {worker_id}"
        else:
            rules = config_manager.get_replacement_rules()
            worker_id = None
            worker_msg = ""
        
        if not rules:
            bot.answer_callback_query(call.id, "No rules to remove!")
            return
        
        text = f"🗑️ <b>Remove Replacement Rule{worker_msg}</b>\n\n"
        text += "Send the rule number to remove:\n\n"
        
        for i, rule in enumerate(rules):
            text += f"{i+1}. {rule['find']} → {rule['replace']}\n"
        
        # Store worker_id in temp storage for process_remove_rule
        if is_multiworker:
            if call.message.chat.id not in temp_storage:
                temp_storage[call.message.chat.id] = {}
            temp_storage[call.message.chat.id]["selected_worker_id"] = worker_id
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
        bot.register_next_step_handler(call.message, process_remove_rule)
        bot.answer_callback_query(call.id)
    except Exception as e:
        import traceback
        print(f"ERROR in remove_rule_start: {e}")
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


def process_remove_rule(message):
    """Process rule removal."""
    try:
        index = int(message.text.strip()) - 1
        
        config_manager.load()
        config = config_manager.config
        
        # Check if multi-worker mode
        is_multiworker = "workers" in config and isinstance(config.get("workers"), list)
        
        if is_multiworker:
            # Get selected worker from temp storage
            data = temp_storage.get(message.chat.id, {})
            worker_id = data.get("selected_worker_id")
            
            if not worker_id:
                bot.reply_to(message, "❌ Session expired. Please try again.")
                return
            
            config_manager.remove_replacement_rule(index, worker_id=worker_id)
            worker_msg = f" from {worker_id}"
        else:
            config_manager.remove_replacement_rule(index)
            worker_msg = ""
        
        bot.reply_to(message, f"✅ Replacement rule removed{worker_msg}!", reply_markup=main_menu_keyboard())
        
        # Create trigger file to reload config
        trigger_file = Path("trigger_reload.flag")
        try:
            trigger_file.touch()
        except:
            pass
    except (ValueError, IndexError):
        bot.reply_to(message, "❌ Invalid rule number.")
    except Exception as e:
        import traceback
        print(f"ERROR in process_remove_rule: {e}")
        traceback.print_exc()
        bot.reply_to(message, f"❌ Error: {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


# ========== FILTERS ==========

@bot.callback_query_handler(func=lambda call: call.data == "menu_filters")
def show_filters(call):
    """Show filter settings - check if multi-worker mode first."""
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    # Multi-worker mode: ask which worker
    if workers_config:
        text = "🔍 <b>Message Filters</b>\n\n"
        text += "Select a worker to manage its filters:\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for worker_cfg in workers_config:
            worker_id = worker_cfg["worker_id"]
            filters = worker_cfg.get("filters", {})
            enabled_status = "✅" if filters.get("enabled") else "❌"
            button_text = f"👷 {worker_id} ({enabled_status} filters)"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f"filters_worker_{worker_id}"))
        
        markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        return
    
    # Single-worker mode
    filters = config_manager.get_filters()
    
    enabled = "✅ Enabled" if filters.get("enabled") else "❌ Disabled"
    mode = filters.get("mode", "whitelist").capitalize()
    keywords = filters.get("keywords", [])
    
    text = f"🔍 <b>Message Filters</b>\n\n"
    text += f"Status: {enabled}\n"
    text += f"Mode: <b>{mode}</b>\n\n"
    
    if keywords:
        text += "<b>Keywords:</b>\n"
        for kw in keywords:
            text += f"  • {kw}\n"
    else:
        text += "No keywords configured.\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Toggle", callback_data="toggle_filters"),
        types.InlineKeyboardButton("📝 Change Mode", callback_data="change_filter_mode")
    )
    markup.add(
        types.InlineKeyboardButton("➕ Add Keyword", callback_data="add_keyword"),
        types.InlineKeyboardButton("🗑️ Clear Keywords", callback_data="clear_keywords")
    )
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))


@bot.callback_query_handler(func=lambda call: call.data.startswith("filters_worker_"))
def show_worker_filters(call):
    """Show filters for a specific worker."""
    worker_id = call.data.replace("filters_worker_", "")
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
    
    if not worker_cfg:
        bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
        return
    
    # Store selected worker in temp storage
    temp_storage[call.message.chat.id] = {"selected_worker_id": worker_id}
    
    filters = worker_cfg.get("filters", {})
    
    enabled = "✅ Enabled" if filters.get("enabled") else "❌ Disabled"
    mode = filters.get("mode", "whitelist").capitalize()
    keywords = filters.get("keywords", [])
    
    text = f"🔍 <b>Message Filters - {worker_id}</b>\n\n"
    text += f"Status: {enabled}\n"
    text += f"Mode: <b>{mode}</b>\n\n"
    
    if keywords:
        text += "<b>Keywords:</b>\n"
        for kw in keywords:
            text += f"  • {kw}\n"
    else:
        text += "No keywords configured.\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 Toggle", callback_data="toggle_filters"),
        types.InlineKeyboardButton("📝 Change Mode", callback_data="change_filter_mode")
    )
    markup.add(
        types.InlineKeyboardButton("➕ Add Keyword", callback_data="add_keyword"),
        types.InlineKeyboardButton("🗑️ Clear Keywords", callback_data="clear_keywords")
    )
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="menu_filters"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "toggle_filters")
def toggle_filters(call):
    """Toggle filter enabled/disabled."""
    filters = config_manager.get_filters()
    current = filters.get("enabled", False)
    config_manager.update_filters(enabled=not current)
    
    status = "enabled" if not current else "disabled"
    bot.answer_callback_query(call.id, f"Filters {status}!")
    show_filters(call)


@bot.callback_query_handler(func=lambda call: call.data == "change_filter_mode")
def change_filter_mode(call):
    """Change filter mode."""
    filters = config_manager.get_filters()
    current_mode = filters.get("mode", "whitelist")
    new_mode = "blacklist" if current_mode == "whitelist" else "whitelist"
    
    config_manager.update_filters(mode=new_mode)
    bot.answer_callback_query(call.id, f"Mode changed to {new_mode}!")
    show_filters(call)


@bot.callback_query_handler(func=lambda call: call.data == "add_keyword")
def add_keyword_start(call):
    """Start adding keyword."""
    bot.edit_message_text(
        "➕ <b>Add Keywords</b>\n\n"
        "Send keywords (one per line or separated by commas):\n\n"
        "Example:\n"
        "<code>GOLD\nSIGNAL\nBUY</code>\n\n"
        "or\n\n"
        "<code>GOLD, SIGNAL, BUY</code>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.register_next_step_handler(call.message, process_add_keyword)


def process_add_keyword(message):
    """Process keyword addition."""
    try:
        filters = config_manager.get_filters()
        current_keywords = filters.get("keywords", [])
        
        # Parse keywords (support both newline and comma separation)
        new_keywords = []
        for line in message.text.split('\n'):
            for kw in line.split(','):
                kw = kw.strip()
                if kw and kw not in current_keywords:
                    new_keywords.append(kw)
        
        current_keywords.extend(new_keywords)
        config_manager.update_filters(keywords=current_keywords)
        
        bot.reply_to(
            message,
            f"✅ Added {len(new_keywords)} keyword(s)!",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == "clear_keywords")
def clear_keywords(call):
    """Clear all keywords."""
    config_manager.update_filters(keywords=[])
    bot.answer_callback_query(call.id, "All keywords cleared!")
    show_filters(call)


# ========== SETTINGS ==========

@bot.callback_query_handler(func=lambda call: call.data == "menu_settings")
def show_settings(call):
    """Show settings - check if multi-worker mode first."""
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    # Multi-worker mode: ask which worker
    if workers_config:
        text = "⚙️ <b>Bot Settings</b>\n\n"
        text += "Select a worker to view its settings:\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for worker_cfg in workers_config:
            worker_id = worker_cfg["worker_id"]
            button_text = f"👷 {worker_id}"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f"settings_worker_{worker_id}"))
        
        markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        return
    
    # Single-worker mode
    settings = config_manager.get_settings()
    
    text = "⚙️ <b>Bot Settings</b>\n\n"
    text += f"Retry Attempts: <code>{settings.get('retry_attempts', 5)}</code>\n"
    text += f"Retry Delay: <code>{settings.get('retry_delay', 5)}s</code>\n"
    text += f"Flood Wait Extra: <code>{settings.get('flood_wait_extra_delay', 10)}s</code>\n"
    text += f"Max Message Length: <code>{settings.get('max_message_length', 4096)}</code>\n"
    text += f"Log Level: <code>{settings.get('log_level', 'INFO')}</code>\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("settings_worker_"))
def show_worker_settings(call):
    """Show settings for a specific worker."""
    worker_id = call.data.replace("settings_worker_", "")
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
    
    if not worker_cfg:
        bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
        return
    
    # Store selected worker in temp storage
    temp_storage[call.message.chat.id] = {"selected_worker_id": worker_id}
    
    settings = worker_cfg.get("settings", {})
    
    text = f"⚙️ <b>Bot Settings - {worker_id}</b>\n\n"
    text += f"Retry Attempts: <code>{settings.get('retry_attempts', 5)}</code>\n"
    text += f"Retry Delay: <code>{settings.get('retry_delay', 5)}s</code>\n"
    text += f"Flood Wait Extra: <code>{settings.get('flood_wait_extra_delay', 10)}s</code>\n"
    text += f"Max Message Length: <code>{settings.get('max_message_length', 4096)}</code>\n"
    text += f"Log Level: <code>{settings.get('log_level', 'INFO')}</code>\n"
    text += f"Add Source Link: <code>{settings.get('add_source_link', False)}</code>\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="menu_settings"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


# ========== WORKERS ==========

@bot.callback_query_handler(func=lambda call: call.data == "menu_workers")
def show_workers(call):
    """Show workers management menu."""
    config_manager.load()
    config = config_manager.config
    
    # Check if multi-worker mode is configured
    workers_config = config.get("workers", [])
    
    if not workers_config:
        text = "👷 <b>Workers</b>\n\n"
        text += "⚠️ Multi-worker mode is not configured.\n\n"
        text += "Your bot is running in <b>single-worker mode</b>.\n\n"
        text += "To enable multi-worker mode:\n"
        text += "1. Edit config.json\n"
        text += "2. Add 'workers' array (see config.example.json)\n"
        text += "3. Restart the bot\n\n"
        text += "Single-worker mode is simpler and works great for most users!"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        return
    
    # Multi-worker mode - show worker status
    try:
        manager = get_worker_manager()
        status = manager.get_status()
        
        text = "👷 <b>Workers Management</b>\n\n"
        text += f"<b>Total Workers:</b> {len(workers_config)}\n"
        text += f"<b>Running:</b> {sum(1 for s in status.values() if s['alive'])}\n\n"
        
        for worker_cfg in workers_config:
            worker_id = worker_cfg["worker_id"]
            enabled = worker_cfg.get("enabled", True)
            
            if worker_id in status:
                s = status[worker_id]
                uptime_mins = int(s['uptime'] / 60)
                
                text += f"<b>🔹 {worker_id}</b>\n"
                text += f"   Status: {'✅ Running' if s['alive'] else '❌ Stopped'}\n"
                if s['alive']:
                    text += f"   PID: {s['pid']}\n"
                    text += f"   Uptime: {uptime_mins} min\n"
                    text += f"   Restarts: {s['restart_count']}\n"
                text += f"   Channels: {len(worker_cfg.get('channel_pairs', []))}\n"
            else:
                text += f"<b>🔹 {worker_id}</b>\n"
                text += f"   Status: {'⏸️ Disabled' if not enabled else '❌ Not Started'}\n"
                text += f"   Channels: {len(worker_cfg.get('channel_pairs', []))}\n"
            text += "\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚀 Start All", callback_data="workers_start_all"),
            types.InlineKeyboardButton("🛑 Stop All", callback_data="workers_stop_all"),
            types.InlineKeyboardButton("🔄 Restart All", callback_data="workers_restart_all"),
            types.InlineKeyboardButton("➕ Add Worker", callback_data="workers_add"),
            types.InlineKeyboardButton("🔍 Worker Details", callback_data="workers_details"),
            types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        )
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "workers_start_all")
def start_all_workers(call):
    """Start all configured workers."""
    try:
        manager = get_worker_manager()
        manager.start_all_workers()
        
        bot.answer_callback_query(call.id, "✅ All workers started!", show_alert=True)
        # Refresh the workers menu
        show_workers(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "workers_stop_all")
def stop_all_workers(call):
    """Stop all running workers."""
    try:
        manager = get_worker_manager()
        manager.stop_all_workers()
        
        bot.answer_callback_query(call.id, "✅ All workers stopped!", show_alert=True)
        # Refresh the workers menu
        show_workers(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "workers_restart_all")
def restart_all_workers(call):
    """Restart all workers."""
    try:
        manager = get_worker_manager()
        manager.stop_all_workers()
        time.sleep(2)
        manager.start_all_workers()
        
        bot.answer_callback_query(call.id, "✅ All workers restarted!", show_alert=True)
        # Refresh the workers menu
        show_workers(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "workers_details")
def show_worker_details(call):
    """Show individual worker controls."""
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    if not workers_config:
        bot.answer_callback_query(call.id, "⚠️ No workers configured", show_alert=True)
        return
    
    text = "🔍 <b>Worker Details</b>\n\n"
    text += "Select a worker to manage:\n\n"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for worker_cfg in workers_config:
        worker_id = worker_cfg["worker_id"]
        channels_count = len(worker_cfg.get("channel_pairs", []))
        button_text = f"🔹 {worker_id} ({channels_count} channels)"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"worker_view_{worker_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_workers"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_view_"))
def view_worker_detail(call):
    """View details of a specific worker."""
    worker_id = call.data.replace("worker_view_", "")
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
    
    if not worker_cfg:
        bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
        return
    
    try:
        manager = get_worker_manager()
        status = manager.get_status()
        
        text = f"👷 <b>Worker: {worker_id}</b>\n\n"
        
        if worker_id in status:
            s = status[worker_id]
            uptime_mins = int(s['uptime'] / 60)
            uptime_hours = uptime_mins // 60
            uptime_mins_remainder = uptime_mins % 60
            
            text += f"<b>Status:</b> {'✅ Running' if s['alive'] else '❌ Stopped'}\n"
            if s['alive']:
                text += f"<b>PID:</b> {s['pid']}\n"
                if uptime_hours > 0:
                    text += f"<b>Uptime:</b> {uptime_hours}h {uptime_mins_remainder}m\n"
                else:
                    text += f"<b>Uptime:</b> {uptime_mins}m\n"
                text += f"<b>Restarts:</b> {s['restart_count']}\n"
        else:
            text += f"<b>Status:</b> ❌ Not Started\n"
        
        # Check authentication status
        session_file = Path(f"{worker_cfg.get('session_name', 'unknown')}.session")
        auth_status = "✅ Authenticated" if session_file.exists() else "❌ Not Authenticated"
        
        text += f"\n<b>Configuration:</b>\n"
        text += f"• API ID: {worker_cfg.get('api_id', 'N/A')}\n"
        text += f"• Session: {worker_cfg.get('session_name', 'N/A')}\n"
        text += f"• Authentication: {auth_status}\n"
        text += f"• Channel Pairs: {len(worker_cfg.get('channel_pairs', []))}\n"
        text += f"• Replacement Rules: {len(worker_cfg.get('replacement_rules', []))}\n"
        text += f"• Enabled: {'✅ Yes' if worker_cfg.get('enabled', True) else '❌ No'}\n"
        
        # Check if session file exists
        session_file = Path(f"{worker_cfg.get('session_name', 'unknown')}.session")
        needs_auth = not session_file.exists()
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        if needs_auth:
            # Show Authenticate button prominently if not authenticated
            markup.add(
                types.InlineKeyboardButton("🔐 Authenticate", callback_data=f"worker_auth_{worker_id}")
            )
            markup.add(
                types.InlineKeyboardButton("🚀 Start", callback_data=f"worker_start_{worker_id}"),
                types.InlineKeyboardButton("🛑 Stop", callback_data=f"worker_stop_{worker_id}"),
                types.InlineKeyboardButton("🔄 Restart", callback_data=f"worker_restart_{worker_id}"),
                types.InlineKeyboardButton("🔑 Edit API", callback_data=f"worker_edit_api_{worker_id}"),
                types.InlineKeyboardButton("❌ Remove", callback_data=f"worker_remove_{worker_id}"),
                types.InlineKeyboardButton("🔙 Back", callback_data="workers_details")
            )
        else:
            # Normal buttons if already authenticated
            markup.add(
                types.InlineKeyboardButton("🚀 Start", callback_data=f"worker_start_{worker_id}"),
                types.InlineKeyboardButton("🛑 Stop", callback_data=f"worker_stop_{worker_id}"),
                types.InlineKeyboardButton("🔄 Restart", callback_data=f"worker_restart_{worker_id}"),
                types.InlineKeyboardButton("🔑 Edit API", callback_data=f"worker_edit_api_{worker_id}"),
                types.InlineKeyboardButton("🔐 Re-Auth", callback_data=f"worker_auth_{worker_id}"),
                types.InlineKeyboardButton("❌ Remove", callback_data=f"worker_remove_{worker_id}"),
                types.InlineKeyboardButton("🔙 Back", callback_data="workers_details")
            )
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_start_"))
def start_worker(call):
    """Start a specific worker."""
    worker_id = call.data.replace("worker_start_", "")
    
    try:
        manager = get_worker_manager()
        if worker_id in manager.workers:
            worker = manager.workers[worker_id]
            if not worker.is_alive():
                worker.start()
                bot.answer_callback_query(call.id, f"✅ Worker {worker_id} started!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, f"⚠️ Worker {worker_id} is already running", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"❌ Worker {worker_id} not found", show_alert=True)
        
        # Refresh view
        view_worker_detail(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_stop_"))
def stop_worker(call):
    """Stop a specific worker."""
    worker_id = call.data.replace("worker_stop_", "")
    
    try:
        manager = get_worker_manager()
        if worker_id in manager.workers:
            worker = manager.workers[worker_id]
            if worker.is_alive():
                worker.stop()
                bot.answer_callback_query(call.id, f"✅ Worker {worker_id} stopped!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, f"⚠️ Worker {worker_id} is not running", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"❌ Worker {worker_id} not found", show_alert=True)
        
        # Refresh view
        view_worker_detail(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_restart_"))
def restart_worker(call):
    """Restart a specific worker."""
    worker_id = call.data.replace("worker_restart_", "")
    
    try:
        manager = get_worker_manager()
        if worker_id in manager.workers:
            worker = manager.workers[worker_id]
            worker.restart()
            bot.answer_callback_query(call.id, f"✅ Worker {worker_id} restarted!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"❌ Worker {worker_id} not found", show_alert=True)
        
        # Refresh view
        view_worker_detail(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_remove_") and not call.data.startswith("worker_remove_confirm_"))
def remove_worker(call):
    """Remove a worker from configuration."""
    worker_id = call.data.replace("worker_remove_", "")
    
    # Confirmation step
    text = f"⚠️ <b>Remove Worker?</b>\n\n"
    text += f"Are you sure you want to remove worker <b>{worker_id}</b>?\n\n"
    text += "This will:\n"
    text += "• Stop the worker if running\n"
    text += "• Remove it from config.json\n"
    text += "• This action cannot be undone!\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Yes, Remove", callback_data=f"confirm_remove_{worker_id}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"worker_view_{worker_id}")
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_remove_"))
def confirm_remove_worker(call):
    """Confirm and remove worker."""
    worker_id = call.data.replace("confirm_remove_", "")
    
    try:
        # Get worker config before removing (to get session_name)
        config_manager.load()
        config = config_manager.config
        workers_config = config.get("workers", [])
        
        worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
        session_name = worker_cfg.get("session_name", "") if worker_cfg else ""
        
        # Stop worker if running
        manager = get_worker_manager()
        if worker_id in manager.workers:
            worker = manager.workers[worker_id]
            if worker.is_alive():
                worker.stop()
        
        # Remove from config
        workers_config = [w for w in workers_config if w["worker_id"] != worker_id]
        config["workers"] = workers_config
        config_manager.config = config
        config_manager.save()
        
        # Delete worker files
        files_deleted = []
        
        # 1. Delete session files
        if session_name:
            session_file = Path(f"{session_name}.session")
            session_journal = Path(f"{session_name}.session-journal")
            
            if session_file.exists():
                session_file.unlink()
                files_deleted.append(f"{session_name}.session")
            
            if session_journal.exists():
                session_journal.unlink()
                files_deleted.append(f"{session_name}.session-journal")
        
        # 2. Delete temp worker config (no longer created, but check for old files)
        temp_config = Path(f"worker_{worker_id}_config.json")
        if temp_config.exists():
            temp_config.unlink()
            files_deleted.append(f"worker_{worker_id}_config.json")
        
        # Reload worker manager
        global worker_manager_instance
        worker_manager_instance = None
        
        # Success message with details
        msg = f"✅ Worker {worker_id} removed!"
        if files_deleted:
            msg += f"\n\n🗑️ Deleted files:\n"
            for f in files_deleted:
                msg += f"• {f}\n"
        
        bot.answer_callback_query(call.id, msg, show_alert=True)
        
        # Go back to workers menu
        show_workers(call)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "workers_add")
def add_worker_start(call):
    """Start the add worker process."""
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    
    # Clear temp storage
    if call.message.chat.id in temp_storage:
        temp_storage.pop(call.message.chat.id)
    
    text = "➕ <b>Add New Worker</b>\n\n"
    text += "Please enter a unique <b>worker ID</b>\n"
    text += "Example: worker_2, backup_worker, etc.\n\n"
    text += "Send /cancel to abort"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_workers"))
    
    msg = bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(msg, process_worker_id)


def process_worker_id(message):
    """Process worker ID input."""
    if message.text == "/cancel":
        bot.send_message(message.chat.id, "❌ Cancelled")
        return
    
    worker_id = message.text.strip()
    
    # Validate worker ID
    if not worker_id or " " in worker_id:
        bot.send_message(message.chat.id, "❌ Invalid worker ID. Please use a single word without spaces.")
        bot.register_next_step_handler(message, process_worker_id)
        return
    
    # Check if worker ID already exists
    config_manager.load()
    workers_config = config_manager.config.get("workers", [])
    if any(w["worker_id"] == worker_id for w in workers_config):
        bot.send_message(message.chat.id, f"❌ Worker ID '{worker_id}' already exists. Please choose a different ID.")
        bot.register_next_step_handler(message, process_worker_id)
        return
    
    # Store worker ID
    temp_storage[message.chat.id] = {"worker_id": worker_id}
    
    text = f"✅ Worker ID: <b>{worker_id}</b>\n\n"
    text += "Now enter the <b>API ID</b> (number)\n"
    text += "Get it from https://my.telegram.org\n\n"
    text += "Send /cancel to abort"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')
    bot.register_next_step_handler(message, process_api_id)


def process_api_id(message):
    """Process API ID input."""
    if message.text == "/cancel":
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Cancelled")
        return
    
    try:
        api_id = int(message.text.strip())
        temp_storage[message.chat.id]["api_id"] = api_id
        
        text = f"✅ API ID: <b>{api_id}</b>\n\n"
        text += "Now enter the <b>API Hash</b> (string)\n"
        text += "Get it from https://my.telegram.org\n\n"
        text += "Send /cancel to abort"
        
        bot.send_message(message.chat.id, text, parse_mode='HTML')
        bot.register_next_step_handler(message, process_api_hash)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid API ID. Please enter a number.")
        bot.register_next_step_handler(message, process_api_id)


def process_api_hash(message):
    """Process API Hash input."""
    if message.text == "/cancel":
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Cancelled")
        return
    
    api_hash = message.text.strip()
    temp_storage[message.chat.id]["api_hash"] = api_hash
    
    worker_id = temp_storage[message.chat.id]["worker_id"]
    
    text = f"✅ API Hash saved\n\n"
    text += "Now enter the <b>session name</b>\n"
    text += f"Example: {worker_id}_session\n\n"
    text += "Send /cancel to abort"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')
    bot.register_next_step_handler(message, process_session_name)


def process_session_name(message):
    """Process session name and complete worker addition."""
    if message.text == "/cancel":
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Cancelled")
        return
    
    session_name = message.text.strip()
    
    # Get all data from temp storage
    data = temp_storage.pop(message.chat.id)
    worker_id = data["worker_id"]
    api_id = data["api_id"]
    api_hash = data["api_hash"]
    
    # Create new worker config
    new_worker = {
        "worker_id": worker_id,
        "api_id": api_id,
        "api_hash": api_hash,
        "session_name": session_name,
        "enabled": True,
        "channel_pairs": [],
        "replacement_rules": [],
        "filters": {
            "enabled": False,
            "mode": "whitelist",
            "keywords": []
        },
        "settings": {
            "retry_attempts": 5,
            "retry_delay": 5,
            "flood_wait_extra_delay": 10,
            "max_message_length": 4096,
            "log_level": "INFO",
            "add_source_link": False,
            "source_link_text": "\n\n🔗 Source: {link}"
        }
    }
    
    # Add to config
    config_manager.load()
    config = config_manager.config
    
    if "workers" not in config:
        config["workers"] = []
    
    config["workers"].append(new_worker)
    config_manager.config = config
    config_manager.save()
    
    # Reload worker manager
    global worker_manager_instance
    worker_manager_instance = None
    
    text = f"✅ <b>Worker Added Successfully!</b>\n\n"
    text += f"<b>Worker ID:</b> {worker_id}\n"
    text += f"<b>API ID:</b> {api_id}\n"
    text += f"<b>Session:</b> {session_name}\n\n"
    text += "⚠️ <b>Important:</b>\n"
    text += "• You need to authenticate this worker\n"
    text += "• Run: python bot.py --config config.json\n"
    text += "• Enter phone number for this account\n"
    text += "• No channels assigned yet\n"
    text += "• Use 'Assign Channels' to add channel pairs\n"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')


# ========== EDIT WORKER API CREDENTIALS ==========

@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_edit_api_"))
def edit_worker_api_start(call):
    """Start editing worker API credentials."""
    worker_id = call.data.replace("worker_edit_api_", "")
    
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    
    # Clear temp storage
    if call.message.chat.id in temp_storage:
        temp_storage.pop(call.message.chat.id)
    
    # Store worker ID
    temp_storage[call.message.chat.id] = {"edit_worker_id": worker_id}
    
    text = f"🔑 <b>Edit API Credentials - {worker_id}</b>\n\n"
    text += "⚠️ <b>Important:</b> Changing API credentials will require re-authentication!\n\n"
    text += "Please enter the new <b>API ID</b> (number)\n"
    text += "Get it from https://my.telegram.org\n\n"
    text += "Send /cancel to abort"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data=f"worker_view_{worker_id}"))
    
    msg = bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(msg, process_edit_api_id)


def process_edit_api_id(message):
    """Process new API ID input."""
    if message.text == "/cancel":
        worker_id = temp_storage.get(message.chat.id, {}).get("edit_worker_id")
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Cancelled")
        return
    
    try:
        api_id = int(message.text.strip())
        temp_storage[message.chat.id]["new_api_id"] = api_id
        
        worker_id = temp_storage[message.chat.id]["edit_worker_id"]
        
        text = f"✅ API ID: <b>{api_id}</b>\n\n"
        text += "Now enter the new <b>API Hash</b> (string)\n"
        text += "Get it from https://my.telegram.org\n\n"
        text += "Send /cancel to abort"
        
        bot.send_message(message.chat.id, text, parse_mode='HTML')
        bot.register_next_step_handler(message, process_edit_api_hash)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid API ID. Please enter a number.")
        bot.register_next_step_handler(message, process_edit_api_id)


def process_edit_api_hash(message):
    """Process new API Hash and complete the update."""
    if message.text == "/cancel":
        worker_id = temp_storage.get(message.chat.id, {}).get("edit_worker_id")
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Cancelled")
        return
    
    api_hash = message.text.strip()
    
    # Get all data from temp storage
    data = temp_storage.pop(message.chat.id)
    worker_id = data["edit_worker_id"]
    new_api_id = data["new_api_id"]
    
    # Update config
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_found = False
    old_api_id = None
    old_session = None
    
    for worker in workers_config:
        if worker["worker_id"] == worker_id:
            old_api_id = worker.get("api_id")
            old_session = worker.get("session_name")
            worker["api_id"] = new_api_id
            worker["api_hash"] = api_hash
            worker_found = True
            break
    
    if not worker_found:
        bot.send_message(message.chat.id, f"❌ Worker '{worker_id}' not found.")
        return
    
    config_manager.config = config
    config_manager.save()
    
    # Reload worker manager
    global worker_manager_instance
    worker_manager_instance = None
    
    text = f"✅ <b>API Credentials Updated!</b>\n\n"
    text += f"<b>Worker:</b> {worker_id}\n"
    text += f"<b>Old API ID:</b> {old_api_id}\n"
    text += f"<b>New API ID:</b> {new_api_id}\n"
    text += f"<b>New API Hash:</b> {api_hash[:20]}...\n\n"
    text += "⚠️ <b>Important Next Steps:</b>\n"
    text += "1. Stop the worker if it's running\n"
    text += f"2. Delete the old session file: <code>{old_session}.session</code>\n"
    text += "3. Restart the bot: <code>./start.sh</code>\n"
    text += "4. Re-authenticate with the new account\n"
    text += "5. Enter the phone number for the new API account\n\n"
    text += "💡 <b>Tip:</b> You can stop the worker from the Workers menu"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_menu_keyboard())


# ========== AUTHENTICATE WORKER ==========

@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_auth_"))
def authenticate_worker(call):
    """Start interactive authentication for a worker."""
    worker_id = call.data.replace("worker_auth_", "")
    
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
    
    if not worker_cfg:
        bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
        return
    
    session_name = worker_cfg.get("session_name", "unknown")
    api_id = worker_cfg.get("api_id", "N/A")
    
    # Check if already authenticated
    session_file = Path(f"{session_name}.session")
    is_authenticated = session_file.exists()
    
    # Store worker info in temp storage
    temp_storage[call.message.chat.id] = {
        "auth_worker_id": worker_id,
        "auth_api_id": worker_cfg.get("api_id"),
        "auth_api_hash": worker_cfg.get("api_hash"),
        "auth_session_name": session_name
    }
    
    text = f"🔐 <b>Authenticate Worker: {worker_id}</b>\n\n"
    
    if is_authenticated:
        text += "⚠️ This worker is already authenticated.\n"
        text += "Re-authenticating will replace the existing session.\n\n"
    
    text += f"<b>Worker Details:</b>\n"
    text += f"• Worker ID: <code>{worker_id}</code>\n"
    text += f"• API ID: <code>{api_id}</code>\n"
    text += f"• Session: <code>{session_name}</code>\n\n"
    
    text += "📱 <b>Step 1/3: Enter Phone Number</b>\n\n"
    text += "Please send your phone number with country code.\n\n"
    text += "<b>Examples:</b>\n"
    text += "• <code>+1234567890</code>\n"
    text += "• <code>+998901234567</code>\n\n"
    text += "Send /cancel to abort"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data=f"worker_view_{worker_id}"))
    
    msg = bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )
    
    bot.register_next_step_handler(msg, process_auth_phone)


def process_auth_phone(message):
    """Process phone number and request verification code."""
    if message.text == "/cancel":
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Authentication cancelled")
        return
    
    phone = message.text.strip()
    data = temp_storage.get(message.chat.id, {})
    
    # Validate required keys
    required_keys = ["auth_worker_id", "auth_api_id", "auth_api_hash", "auth_session_name"]
    if not data or not all(key in data for key in required_keys):
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Session expired or invalid. Please restart authentication from Workers menu.")
        return
    
    worker_id = data["auth_worker_id"]
    api_id = data["auth_api_id"]
    api_hash = data["auth_api_hash"]
    session_name = data["auth_session_name"]
    
    # Store phone
    temp_storage[message.chat.id]["auth_phone"] = phone
    
    bot.send_message(message.chat.id, f"⏳ Connecting to Telegram as <code>{phone}</code>...", parse_mode='HTML')
    
    # Run async authentication
    try:
        # Create new event loop (get_event_loop() is deprecated when no loop exists)
        try:
            loop = asyncio.get_running_loop()
            # If we get here, there's already a running loop - create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        except RuntimeError:
            # No running loop, create new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        client = TelegramClient(session_name, api_id, api_hash)
        
        async def send_code():
            try:
                # Connect to Telegram
                await client.connect()
                
                # Check if connected
                if not client.is_connected():
                    raise ConnectionError("Failed to connect to Telegram servers")
                
                # Send code request
                # Telethon will automatically handle DC migration if needed
                result = await client.send_code_request(phone)
                
                return result.phone_code_hash
            finally:
                # Always disconnect and save session
                if client.is_connected():
                    await client.disconnect()
        
        phone_code_hash = loop.run_until_complete(send_code())
        
        # Clean up event loop properly
        try:
            # Cancel all pending tasks (if available)
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except (AttributeError, RuntimeError):
                # all_tasks() not available or no tasks
                pass
        except Exception:
            pass
        finally:
            if not loop.is_closed():
                loop.close()
        
        # Store for next step
        temp_storage[message.chat.id]["auth_phone_code_hash"] = phone_code_hash
        temp_storage[message.chat.id]["auth_client_created"] = True
        
        text = f"✅ <b>Code sent to {phone}!</b>\n\n"
        text += "📱 <b>Step 2/3: Enter Verification Code</b>\n\n"
        text += "Please check your Telegram app and send the verification code here.\n\n"
        text += "<b>Example:</b> <code>12345</code>\n\n"
        text += "Send /cancel to abort"
        
        bot.send_message(message.chat.id, text, parse_mode='HTML')
        bot.register_next_step_handler(message, process_auth_code)
        
    except PhoneMigrateError as e:
        temp_storage.pop(message.chat.id, None)
        new_dc = e.new_dc
        worker_id = data.get("auth_worker_id", "unknown")
        bot.send_message(
            message.chat.id,
            f"⚠️ <b>Data Center Migration Required</b>\n\n"
            f"Your phone number <code>{phone}</code> is associated with DC {new_dc}.\n\n"
            f"<b>This is normal!</b> Telegram uses multiple data centers.\n\n"
            f"<b>Solution:</b>\n"
            f"1. Click 🔐 Authenticate again - Telethon will automatically connect to DC {new_dc}\n"
            f"2. Or use terminal authentication (more reliable):\n"
            f"   <code>python3 auth_worker.py {worker_id}</code>\n\n"
            f"💡 Terminal authentication handles DC migration automatically.",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )
    except FloodWaitError as e:
        temp_storage.pop(message.chat.id, None)
        bot.send_message(
            message.chat.id,
            f"❌ <b>Rate Limited!</b>\n\n"
            f"Please wait {e.seconds} seconds before trying again.",
            parse_mode='HTML'
        )
    except ConnectionError as e:
        temp_storage.pop(message.chat.id, None)
        bot.send_message(
            message.chat.id,
            f"❌ <b>Connection Error</b>\n\n"
            f"{str(e)}\n\n"
            f"<b>Possible causes:</b>\n"
            f"• Check your internet connection\n"
            f"• API credentials might be invalid\n"
            f"• Telegram servers might be down\n\n"
            f"<b>What to check:</b>\n"
            f"• API ID: <code>{api_id}</code>\n"
            f"• Make sure API credentials are correct",
            parse_mode='HTML'
        )
    except Exception as e:
        temp_storage.pop(message.chat.id, None)
        error_name = type(e).__name__
        bot.send_message(
            message.chat.id,
            f"❌ <b>Error: {error_name}</b>\n\n"
            f"{str(e)}\n\n"
            f"<b>Troubleshooting:</b>\n"
            f"• Check phone number format (+country code)\n"
            f"• Verify API ID: <code>{api_id}</code>\n"
            f"• Make sure worker API credentials are correct\n"
            f"• Try editing API credentials and try again",
            parse_mode='HTML'
        )


def process_auth_code(message):
    """Process verification code."""
    if message.text == "/cancel":
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Authentication cancelled")
        return
    
    code = message.text.strip()
    data = temp_storage.get(message.chat.id, {})
    
    # Validate required keys
    required_keys = ["auth_worker_id", "auth_api_id", "auth_api_hash", "auth_session_name", "auth_phone", "auth_phone_code_hash"]
    if not data or not all(key in data for key in required_keys):
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Session expired or invalid. Please restart authentication from Workers menu.")
        return
    
    worker_id = data["auth_worker_id"]
    api_id = data["auth_api_id"]
    api_hash = data["auth_api_hash"]
    session_name = data["auth_session_name"]
    phone = data["auth_phone"]
    phone_code_hash = data["auth_phone_code_hash"]
    
    bot.send_message(message.chat.id, "⏳ Verifying code...")
    
    # Run async sign in
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        client = TelegramClient(session_name, api_id, api_hash)
        
        async def sign_in():
            try:
                await client.connect()
                
                if not client.is_connected():
                    raise ConnectionError("Failed to connect to Telegram servers")
                
                try:
                    result = await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                    me = await client.get_me()
                    # Ensure session is saved before disconnecting
                    await asyncio.sleep(0.5)  # Give Telethon time to save session
                    return True, me, None
                except SessionPasswordNeededError:
                    return False, None, "2FA required"
                except PhoneCodeInvalidError:
                    return False, None, "Invalid code"
                except Exception as e:
                    return False, None, str(e)
            finally:
                # Always disconnect and save session
                if client.is_connected():
                    await client.disconnect()
        
        success, me, error = loop.run_until_complete(sign_in())
        
        # Clean up event loop properly
        try:
            # Cancel all pending tasks (if available)
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except (AttributeError, RuntimeError):
                # all_tasks() not available or no tasks
                pass
        except Exception:
            pass
        finally:
            if not loop.is_closed():
                loop.close()
        
        if success:
            # Authentication complete!
            temp_storage.pop(message.chat.id, None)
            
            text = f"✅ <b>Authentication Successful!</b>\n\n"
            text += f"👤 <b>Logged in as:</b> {me.first_name}"
            if me.last_name:
                text += f" {me.last_name}"
            text += "\n"
            if me.username:
                text += f"🔗 <b>Username:</b> @{me.username}\n"
            text += f"📞 <b>Phone:</b> {me.phone}\n\n"
            text += f"📁 <b>Session file created:</b> <code>{session_name}.session</code>\n\n"
            text += f"🎉 Worker '<b>{worker_id}</b>' is now authenticated!\n\n"
            text += "💡 You can now start this worker from the Workers menu."
            
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_menu_keyboard())
            
        elif error == "2FA required":
            # Need 2FA password
            text = f"🔐 <b>Step 3/3: Enter 2FA Password</b>\n\n"
            text += "This account has Two-Factor Authentication enabled.\n\n"
            text += "Please send your 2FA password.\n\n"
            text += "Send /cancel to abort"
            
            bot.send_message(message.chat.id, text, parse_mode='HTML')
            bot.register_next_step_handler(message, process_auth_2fa)
            
        else:
            temp_storage.pop(message.chat.id, None)
            bot.send_message(
                message.chat.id,
                f"❌ <b>Error:</b> {error}\n\n"
                f"Please try again.",
                parse_mode='HTML'
            )
            
    except Exception as e:
        temp_storage.pop(message.chat.id, None)
        bot.send_message(
            message.chat.id,
            f"❌ <b>Error:</b> {str(e)}\n\n"
            f"Please try again.",
            parse_mode='HTML'
        )


def process_auth_2fa(message):
    """Process 2FA password."""
    if message.text == "/cancel":
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Authentication cancelled")
        return
    
    password = message.text.strip()
    data = temp_storage.get(message.chat.id, {})
    
    # Validate required keys
    required_keys = ["auth_worker_id", "auth_api_id", "auth_api_hash", "auth_session_name"]
    if not data or not all(key in data for key in required_keys):
        temp_storage.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "❌ Session expired or invalid. Please restart authentication from Workers menu.")
        return
    
    worker_id = data["auth_worker_id"]
    api_id = data["auth_api_id"]
    api_hash = data["auth_api_hash"]
    session_name = data["auth_session_name"]
    
    bot.send_message(message.chat.id, "⏳ Verifying 2FA password...")
    
    # Run async 2FA check
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        client = TelegramClient(session_name, api_id, api_hash)
        
        async def check_password():
            try:
                await client.connect()
                
                if not client.is_connected():
                    raise ConnectionError("Failed to connect to Telegram servers")
                
                try:
                    await client.sign_in(password=password)
                    me = await client.get_me()
                    # Ensure session is saved before disconnecting
                    await asyncio.sleep(0.5)  # Give Telethon time to save session
                    return True, me, None
                except Exception as e:
                    return False, None, str(e)
            finally:
                # Always disconnect and save session
                if client.is_connected():
                    await client.disconnect()
        
        success, me, error = loop.run_until_complete(check_password())
        
        # Clean up event loop properly
        try:
            # Cancel all pending tasks (if available)
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except (AttributeError, RuntimeError):
                # all_tasks() not available or no tasks
                pass
        except Exception:
            pass
        finally:
            if not loop.is_closed():
                loop.close()
        
        if success:
            # Authentication complete!
            temp_storage.pop(message.chat.id, None)
            
            text = f"✅ <b>Authentication Successful!</b>\n\n"
            text += f"👤 <b>Logged in as:</b> {me.first_name}"
            if me.last_name:
                text += f" {me.last_name}"
            text += "\n"
            if me.username:
                text += f"🔗 <b>Username:</b> @{me.username}\n"
            text += f"📞 <b>Phone:</b> {me.phone}\n\n"
            text += f"📁 <b>Session file created:</b> <code>{session_name}.session</code>\n\n"
            text += f"🎉 Worker '<b>{worker_id}</b>' is now authenticated!\n\n"
            text += "💡 You can now start this worker from the Workers menu."
            
            bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=main_menu_keyboard())
            
        else:
            temp_storage.pop(message.chat.id, None)
            bot.send_message(
                message.chat.id,
                f"❌ <b>2FA Error:</b> {error}\n\n"
                f"Password might be incorrect. Please try again.",
                parse_mode='HTML'
            )
            
    except Exception as e:
        temp_storage.pop(message.chat.id, None)
        bot.send_message(
            message.chat.id,
            f"❌ <b>Error:</b> {str(e)}\n\n"
            f"Please try again.",
            parse_mode='HTML'
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_check_auth_"))
def check_worker_auth(call):
    """Check authentication status of a worker."""
    worker_id = call.data.replace("worker_check_auth_", "")
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
    
    if not worker_cfg:
        bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
        return
    
    session_name = worker_cfg.get("session_name", "unknown")
    session_file = Path(f"{session_name}.session")
    
    if session_file.exists():
        # Get file info
        import os
        file_size = os.path.getsize(session_file)
        mod_time = os.path.getmtime(session_file)
        from datetime import datetime
        mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
        
        message = (
            f"✅ Worker '{worker_id}' is authenticated!\n\n"
            f"📁 Session file: {session_name}.session\n"
            f"📊 Size: {file_size} bytes\n"
            f"📅 Last modified: {mod_date}\n\n"
            f"You can now start this worker!"
        )
        bot.answer_callback_query(call.id, message, show_alert=True)
        
        # Refresh the view
        view_worker_detail(call)
    else:
        bot.answer_callback_query(
            call.id,
            f"❌ Worker '{worker_id}' is NOT authenticated.\n"
            f"Session file '{session_name}.session' not found.\n\n"
            f"Please run: python3 auth_worker.py {worker_id}",
            show_alert=True
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_delete_session_"))
def delete_worker_session(call):
    """Delete session file for a worker (requires confirmation)."""
    worker_id = call.data.replace("worker_delete_session_", "")
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
    
    if not worker_cfg:
        bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
        return
    
    session_name = worker_cfg.get("session_name", "unknown")
    
    text = f"⚠️ <b>Delete Session File?</b>\n\n"
    text += f"Are you sure you want to delete the session file for <b>{worker_id}</b>?\n\n"
    text += f"Session: <code>{session_name}.session</code>\n\n"
    text += "This will:\n"
    text += "• Log out this worker from Telegram\n"
    text += "• Require re-authentication to use again\n"
    text += "• This action cannot be undone!\n\n"
    text += "Use this if you want to switch to a different Telegram account."
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Yes, Delete", callback_data=f"worker_delete_session_confirm_{worker_id}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"worker_auth_{worker_id}")
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("worker_delete_session_confirm_"))
def confirm_delete_worker_session(call):
    """Confirm and delete the session file."""
    worker_id = call.data.replace("worker_delete_session_confirm_", "")
    
    config_manager.load()
    config = config_manager.config
    workers_config = config.get("workers", [])
    
    worker_cfg = next((w for w in workers_config if w["worker_id"] == worker_id), None)
    
    if not worker_cfg:
        bot.answer_callback_query(call.id, "⚠️ Worker not found", show_alert=True)
        return
    
    session_name = worker_cfg.get("session_name", "unknown")
    session_file = Path(f"{session_name}.session")
    
    try:
        if session_file.exists():
            session_file.unlink()
            bot.answer_callback_query(
                call.id,
                f"✅ Session file deleted!\n\n"
                f"Worker '{worker_id}' is now logged out.\n"
                f"Re-authenticate to use again.",
                show_alert=True
            )
        else:
            bot.answer_callback_query(
                call.id,
                f"⚠️ Session file doesn't exist.",
                show_alert=True
            )
        
        # Go back to worker view
        call.data = f"worker_view_{worker_id}"
        view_worker_detail(call)
        
    except Exception as e:
        bot.answer_callback_query(
            call.id,
            f"❌ Error deleting session: {str(e)}",
            show_alert=True
        )


# ========== STATUS ==========

@bot.callback_query_handler(func=lambda call: call.data == "menu_status")
@bot.message_handler(commands=['status'])
def show_status(message_or_call):
    """Show bot status."""
    if isinstance(message_or_call, types.CallbackQuery):
        call = message_or_call
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        is_callback = True
    else:
        message = message_or_call
        if not is_admin(message.from_user.id):
            bot.reply_to(message, "❌ You are not authorized.")
            return
        chat_id = message.chat.id
        message_id = None
        is_callback = False
    
    config_manager.load()
    pairs = config_manager.get_channel_pairs()
    rules = config_manager.get_replacement_rules()
    filters = config_manager.get_filters()
    
    text = "📊 <b>Forwarder Bot Status</b>\n\n"
    text += f"📡 Channel Pairs: <b>{len(pairs)}</b>\n"
    text += f"🔄 Replacement Rules: <b>{len(rules)}</b>\n"
    text += f"🔍 Filters: <b>{'✅ Enabled' if filters.get('enabled') else '❌ Disabled'}</b>\n"
    
    if filters.get("enabled"):
        text += f"   Mode: {filters.get('mode', 'whitelist').capitalize()}\n"
        text += f"   Keywords: {len(filters.get('keywords', []))}\n"
    
    text += f"\n💡 <b>Note:</b> Changes require restarting the forwarder bot to take effect."
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
    
    if is_callback:
        bot.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
    else:
        bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup)


# ========== RELOAD CONFIG ==========

@bot.callback_query_handler(func=lambda call: call.data == "reload_config")
def reload_config(call):
    """Reload configuration."""
    try:
        config_manager.load()
        bot.answer_callback_query(call.id, "✅ Configuration reloaded!")
        back_to_main(call)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")


# ========== HELP ==========

@bot.message_handler(commands=['help'])
def send_help(message):
    """Send help message."""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    help_text = """
📖 <b>Help - Admin Bot Commands</b>

<b>Commands:</b>
/start - Show main menu
/status - Check bot status
/menu - Show main menu
/help - Show this help

<b>Features:</b>
• Manage channel pairs
• Add/remove text replacement rules
• Configure message filters
• View current settings
• Real-time configuration updates

<b>How to use:</b>
1. Use /start to open the menu
2. Select options using buttons
3. Follow the prompts to add/remove items
4. Restart the forwarder bot to apply changes

<b>Getting Channel IDs:</b>
Forward any message from a channel to @userinfobot

<b>Note:</b> All changes are saved immediately but require restarting the main forwarder bot to take effect.
    """
    
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')


# ========== ERROR HANDLER ==========

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    """Handle unknown messages."""
    if not is_admin(message.from_user.id):
        return
    
    bot.reply_to(
        message,
        "❓ Unknown command. Use /start to see the menu or /help for help.",
        reply_markup=main_menu_keyboard()
    )


def run_admin_bot():
    """Run the admin bot."""
    print("="*60)
    print("🤖 Telegram Forwarder Admin Bot")
    print("="*60)
    print(f"\n✅ Bot is running...")
    print(f"💡 Send /start to the bot to begin\n")
    
    if ADMIN_USER_IDS:
        print(f"👥 Authorized users: {len(ADMIN_USER_IDS)}")
    else:
        print("⚠️  WARNING: No admin users configured! Bot is accessible to anyone.")
    
    print(f"\n📝 DEBUG LOGGING ENABLED")
    print(f"   All actions will be logged to the console")
    print(f"\n🛑 Press Ctrl+C to stop\n")
    
    bot.infinity_polling()


if __name__ == '__main__':
    run_admin_bot()

