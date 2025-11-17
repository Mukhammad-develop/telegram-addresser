"""Telegram Bot Admin Panel for managing the forwarder configuration."""
import telebot
from telebot import types
import json
import os
from src.config_manager import ConfigManager

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
    """Show channel pairs."""
    config_manager.load()
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
        
        config_manager.add_channel_pair(source, target, backfill)
        
        bot.reply_to(
            message,
            f"✅ <b>Channel pair added!</b>\n\n"
            f"Source: <code>{source}</code>\n"
            f"Target: <code>{target}</code>\n"
            f"Backfill: {backfill}\n\n"
            f"Don't forget to restart the forwarder bot!",
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
    pairs = config_manager.get_all_channel_pairs()
    
    if not pairs:
        bot.answer_callback_query(call.id, "No pairs to remove!")
        return
    
    text = "🗑️ <b>Remove Channel Pair</b>\n\n"
    text += "Send the pair number to remove:\n\n"
    
    for i, pair in enumerate(pairs):
        text += f"{i+1}. {pair['source']} → {pair['target']}\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.register_next_step_handler(call.message, process_remove_channel_pair)


def process_remove_channel_pair(message):
    """Process channel pair removal."""
    try:
        index = int(message.text.strip()) - 1
        config_manager.remove_channel_pair(index)
        bot.reply_to(
            message,
            "✅ Channel pair removed! Restart the forwarder bot to apply changes.",
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
    pairs = config_manager.get_all_channel_pairs()
    
    text = "🔄 <b>Toggle Channel Pair</b>\n\n"
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
        pairs = config_manager.get_all_channel_pairs()
        current = pairs[index].get("enabled", True)
        config_manager.update_channel_pair(index, enabled=not current)
        
        status = "disabled" if current else "enabled"
        bot.reply_to(
            message,
            f"✅ Channel pair {status}! Restart the forwarder bot to apply changes.",
            reply_markup=main_menu_keyboard()
        )
    except (ValueError, IndexError):
        bot.reply_to(message, "❌ Invalid pair number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


# ========== REPLACEMENT RULES ==========

@bot.callback_query_handler(func=lambda call: call.data == "menu_rules")
def show_rules(call):
    """Show replacement rules."""
    # Clear any temporary storage when navigating to menu
    if call.message.chat.id in temp_storage:
        temp_storage.pop(call.message.chat.id)
    
    config_manager.load()
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
        config_manager.add_replacement_rule(find_text, replace_text, case_sensitive, is_regex)
        print(f"[STEP 4] Rule saved successfully!")
        
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
    config_manager.load()
    rules = config_manager.get_replacement_rules()
    
    if not rules:
        bot.answer_callback_query(call.id, "No rules to remove!")
        return
    
    text = "🗑️ <b>Remove Replacement Rule</b>\n\n"
    text += "Send the rule number to remove:\n\n"
    
    for i, rule in enumerate(rules):
        text += f"{i+1}. {rule['find']} → {rule['replace']}\n"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    bot.register_next_step_handler(call.message, process_remove_rule)


def process_remove_rule(message):
    """Process rule removal."""
    try:
        index = int(message.text.strip()) - 1
        config_manager.remove_replacement_rule(index)
        bot.reply_to(message, "✅ Replacement rule removed!", reply_markup=main_menu_keyboard())
    except (ValueError, IndexError):
        bot.reply_to(message, "❌ Invalid rule number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")


# ========== FILTERS ==========

@bot.callback_query_handler(func=lambda call: call.data == "menu_filters")
def show_filters(call):
    """Show filter settings."""
    config_manager.load()
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
    """Show settings."""
    config_manager.load()
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

