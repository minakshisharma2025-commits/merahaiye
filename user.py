"""
=============================================================================
BOLLYFLIX BOT - USER COMMANDS
=============================================================================
All user-facing commands:
- /help - Help & usage guide
- /status - User stats & info
- /history - Download history
- /settings - User settings
- /feedback - Send feedback
- /about - Bot information
=============================================================================
"""

from datetime import datetime
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    BOT_NAME, BOT_VERSION, BOT_USERNAME,
    OWNER_IDS, MSG_HELP,
    MSG_USER_STATUS, MSG_USER_HISTORY, MSG_NO_HISTORY
)
from logger import log_info, log_user
from database import db, User, DownloadLog
from helpers import format_datetime, time_ago, truncate


# =============================================================================
# /HELP COMMAND
# =============================================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show help message with usage instructions
    
    Displays:
    - How to use the bot
    - Available commands
    - Tips & tricks
    """
    user_id = update.effective_user.id
    
    log_user(f"User {user_id} requested help")
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton("🔍 Search Movie", switch_inline_query_current_chat=""),
            InlineKeyboardButton("📊 My Status", callback_data="user_status")
        ],
        [
            InlineKeyboardButton("📜 History", callback_data="user_history"),
            InlineKeyboardButton("ℹ️ About", callback_data="user_about")
        ]
    ]
    
    await update.message.reply_text(
        MSG_HELP,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =============================================================================
# /STATUS COMMAND
# =============================================================================

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show user's status and statistics
    
    Displays:
    - User ID & name
    - Join date
    - Search & download counts
    - Account status
    """
    user = update.effective_user
    user_id = user.id
    
    log_user(f"User {user_id} checking status")
    
    # Get user from database
    db_user = db.get_user(user_id)
    
    if not db_user:
        # User not in database, add them
        db.add_user(user_id, user.username, user.first_name)
        db_user = db.get_user(user_id)
    
    # Format join date
    joined = "N/A"
    if db_user and db_user.joined:
        try:
            joined_dt = datetime.fromisoformat(db_user.joined)
            joined = format_datetime(joined_dt, "short")
        except:
            joined = "N/A"
    
    # Determine status
    if db_user and db_user.banned:
        status = "🚫 Banned"
    elif user_id in OWNER_IDS:
        status = "👑 Owner"
    elif db_user and db_user.is_premium:
        status = "⭐ Premium"
    else:
        status = "✅ Active"
    
    # Build status message
    status_text = MSG_USER_STATUS.format(
        user_id=user_id,
        name=user.first_name or "User",
        joined=joined,
        searches=db_user.searches if db_user else 0,
        downloads=db_user.downloads if db_user else 0,
        status=status
    )
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton("📜 My History", callback_data="user_history"),
            InlineKeyboardButton("🔄 Refresh", callback_data="user_status")
        ]
    ]
    
    await update.message.reply_text(
        status_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =============================================================================
# /HISTORY COMMAND
# =============================================================================

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show user's download history
    
    Displays:
    - Recent downloads
    - Title, quality, date
    - Total count
    """
    user = update.effective_user
    user_id = user.id
    
    log_user(f"User {user_id} checking history")
    
    # Get user downloads
    downloads = db.get_user_downloads(user_id, limit=10)
    
    if not downloads:
        await update.message.reply_text(
            MSG_NO_HISTORY,
            parse_mode="Markdown"
        )
        return
    
    # Build history text
    history_lines = []
    
    for i, dl in enumerate(downloads, 1):
        # Format timestamp
        try:
            dl_time = datetime.fromisoformat(dl.timestamp)
            time_str = time_ago(dl_time)
        except:
            time_str = "N/A"
        
        # Content type emoji
        type_emoji = "📺" if dl.content_type == "series" else "🎬"
        
        # Season info
        season_str = f" {dl.season}" if dl.season else ""
        
        # Truncate title
        title = truncate(dl.title, 25)
        
        history_lines.append(
            f"{type_emoji} **{i}.** {title}{season_str}\n"
            f"    📊 {dl.quality} • {time_str}"
        )
    
    history_text = "\n\n".join(history_lines)
    
    # Get total count
    db_user = db.get_user(user_id)
    total = db_user.downloads if db_user else len(downloads)
    
    # Build message
    message = MSG_USER_HISTORY.format(
        name=user.first_name,
        history=history_text,
        total=total
    )
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton("📊 My Status", callback_data="user_status"),
            InlineKeyboardButton("🔄 Refresh", callback_data="user_history")
        ]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =============================================================================
# /ABOUT COMMAND
# =============================================================================

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show bot information
    
    Displays:
    - Bot name & version
    - Features
    - Credits
    """
    user_id = update.effective_user.id
    
    log_user(f"User {user_id} checking about")
    
    # Get stats
    stats = db.get_stats()
    
    about_text = f"""ℹ️ **ABOUT {BOT_NAME.upper()}**

🤖 **Bot Info:**
├ 📛 Name: {BOT_NAME}
├ 🔢 Version: {BOT_VERSION}
├ 👤 Username: @{BOT_USERNAME}
└ 🛠️ Framework: python-telegram-bot

📊 **Statistics:**
├ 👥 Total Users: {stats['users']['total']}
├ 🔍 Total Searches: {stats['searches']['total']}
└ 📥 Total Downloads: {stats['downloads']['total']}

⚡ **Features:**
• 🎬 Movies & Web Series
• 📺 Season-wise Downloads
• 📊 Multiple Qualities (480p-4K)
• 🚀 Fast Bypass System
• 💾 Smart Caching

🔗 **Source:** BollyFlix

💻 **Developed by:** ENI

📝 **Note:**
This bot is for educational purposes only.
All content is sourced from third-party websites.

🙏 **Thank you for using {BOT_NAME}!**"""
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton("📖 Help", callback_data="user_help"),
            InlineKeyboardButton("📊 Status", callback_data="user_status")
        ],
        [
            InlineKeyboardButton("🔍 Start Searching", switch_inline_query_current_chat="")
        ]
    ]
    
    await update.message.reply_text(
        about_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )




# =============================================================================
# /FEEDBACK COMMAND
# =============================================================================

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Allow user to send feedback
    
    - Sets state to await feedback message
    - Forwards feedback to owner
    """
    user = update.effective_user
    user_id = user.id
    
    log_user(f"User {user_id} sending feedback")
    
    # Import session handler
    from handlers import set_session
    
    # Set state to await feedback
    set_session(user_id, {"state": "awaiting_feedback"})
    
    feedback_text = """📝 **SEND FEEDBACK**

Please type your feedback, suggestion, or report any issues.

Your message will be sent to the bot owner.

📌 **Tips for good feedback:**
• Be specific about any issues
• Include movie/series name if relevant
• Mention your device/platform if needed

✍️ **Type your message now:**

_Send /cancel to cancel._"""
    
    await update.message.reply_text(
        feedback_text,
        parse_mode="Markdown"
    )


async def handle_feedback_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Handle incoming feedback message
    
    Returns:
        True if feedback was processed, False otherwise
    """
    from handlers import get_session, clear_session
    
    user = update.effective_user
    user_id = user.id
    message = update.message.text
    
    session = get_session(user_id)
    
    if session.get("state") != "awaiting_feedback":
        return False
    
    # Clear state
    clear_session(user_id)
    
    # Check for cancel
    if message.lower() == "/cancel":
        await update.message.reply_text(
            "❌ Feedback cancelled.",
            parse_mode="Markdown"
        )
        return True
    
    # Forward to owner(s)
    feedback_msg = f"""📬 **NEW FEEDBACK**

👤 **From:** {user.first_name} (@{user.username or 'N/A'})
🆔 **User ID:** `{user_id}`
📅 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

💬 **Message:**
{message}"""
    
    for owner_id in OWNER_IDS:
        try:
            await context.bot.send_message(
                chat_id=owner_id,
                text=feedback_msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            log_info(f"Failed to send feedback to owner {owner_id}: {e}")
    
    # Confirm to user
    await update.message.reply_text(
        "✅ **Feedback Sent!**\n\nThank you for your feedback. The owner will review it soon.",
        parse_mode="Markdown"
    )
    
    log_info(f"Feedback from {user_id}: {truncate(message, 50)}")
    
    return True


# =============================================================================
# USER CALLBACK HANDLERS
# =============================================================================

async def user_callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Handle user-related callbacks
    
    Returns:
        True if callback was handled, False otherwise
    """
    query = update.callback_query
    data = query.data
    
    if not data.startswith("user_") and not data.startswith("setting_"):
        return False
    
    await query.answer()
    
    user_id = query.from_user.id
    
    if data == "user_help":
        await show_help_inline(query, context)
    
    elif data == "user_status":
        await show_status_inline(query, context)
    
    elif data == "user_history":
        await show_history_inline(query, context)
    
    elif data == "user_about":
        await show_about_inline(query, context)
    
    elif data == "setting_notif":
        await query.answer("🔔 Notification settings coming soon!", show_alert=True)
    
    elif data == "setting_quality":
        await query.answer("📊 Quality settings coming soon!", show_alert=True)
    
    else:
        return False
    
    return True


async def show_help_inline(query, context: ContextTypes.DEFAULT_TYPE):
    """Show help as inline edit"""
    keyboard = [
        [
            InlineKeyboardButton("📊 My Status", callback_data="user_status"),
            InlineKeyboardButton("📜 History", callback_data="user_history")
        ],
        [
            InlineKeyboardButton("ℹ️ About", callback_data="user_about")
        ]
    ]
    
    try:
        await query.edit_message_text(
            MSG_HELP,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_status_inline(query, context: ContextTypes.DEFAULT_TYPE):
    """Show status as inline edit"""
    user = query.from_user
    user_id = user.id
    
    db_user = db.get_user(user_id)
    
    if not db_user:
        db.add_user(user_id, user.username, user.first_name)
        db_user = db.get_user(user_id)
    
    joined = "N/A"
    if db_user and db_user.joined:
        try:
            joined_dt = datetime.fromisoformat(db_user.joined)
            joined = format_datetime(joined_dt, "short")
        except:
            joined = "N/A"
    
    if db_user and db_user.banned:
        status = "🚫 Banned"
    elif user_id in OWNER_IDS:
        status = "👑 Owner"
    else:
        status = "✅ Active"
    
    status_text = MSG_USER_STATUS.format(
        user_id=user_id,
        name=user.first_name or "User",
        joined=joined,
        searches=db_user.searches if db_user else 0,
        downloads=db_user.downloads if db_user else 0,
        status=status
    )
    
    keyboard = [
    [
        InlineKeyboardButton("🔍 Search Movie", switch_inline_query_current_chat=""),
        InlineKeyboardButton("📊 My Status", callback_data="user_status")
    ],
    [
        InlineKeyboardButton("⚙️ Settings", callback_data="settings_back"),
        InlineKeyboardButton("📜 History", callback_data="user_history")
    ],
    [
        InlineKeyboardButton("ℹ️ About", callback_data="user_about")
    ]
]
    
    try:
        await query.edit_message_text(
            status_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_history_inline(query, context: ContextTypes.DEFAULT_TYPE):
    """Show history as inline edit"""
    user = query.from_user
    user_id = user.id
    
    downloads = db.get_user_downloads(user_id, limit=10)
    
    if not downloads:
        keyboard = [
            [InlineKeyboardButton("📖 Help", callback_data="user_help")]
        ]
        
        try:
            await query.edit_message_text(
                MSG_NO_HISTORY,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except:
            pass
        return
    
    history_lines = []
    
    for i, dl in enumerate(downloads, 1):
        try:
            dl_time = datetime.fromisoformat(dl.timestamp)
            time_str = time_ago(dl_time)
        except:
            time_str = "N/A"
        
        type_emoji = "📺" if dl.content_type == "series" else "🎬"
        season_str = f" {dl.season}" if dl.season else ""
        title = truncate(dl.title, 25)
        
        history_lines.append(
            f"{type_emoji} **{i}.** {title}{season_str}\n"
            f"    📊 {dl.quality} • {time_str}"
        )
    
    history_text = "\n\n".join(history_lines)
    
    db_user = db.get_user(user_id)
    total = db_user.downloads if db_user else len(downloads)
    
    message = MSG_USER_HISTORY.format(
        name=user.first_name,
        history=history_text,
        total=total
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Status", callback_data="user_status"),
            InlineKeyboardButton("🔄 Refresh", callback_data="user_history")
        ],
        [
            InlineKeyboardButton("📖 Help", callback_data="user_help")
        ]
    ]
    
    try:
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_about_inline(query, context: ContextTypes.DEFAULT_TYPE):
    """Show about as inline edit"""
    stats = db.get_stats()
    
    about_text = f"""ℹ️ **ABOUT {BOT_NAME.upper()}**

🤖 **Bot Info:**
├ 📛 Name: {BOT_NAME}
├ 🔢 Version: {BOT_VERSION}
└ 👤 Username: @{BOT_USERNAME}

📊 **Statistics:**
├ 👥 Users: {stats['users']['total']}
├ 🔍 Searches: {stats['searches']['total']}
└ 📥 Downloads: {stats['downloads']['total']}

⚡ **Features:**
• Movies & Web Series
• Multiple Qualities
• Fast Bypass System

💻 **Developed by:** ENI"""
    
    keyboard = [
        [
            InlineKeyboardButton("📖 Help", callback_data="user_help"),
            InlineKeyboardButton("📊 Status", callback_data="user_status")
        ]
    ]
    
    try:
        await query.edit_message_text(
            about_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


# =============================================================================
# /CANCEL COMMAND
# =============================================================================

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cancel current operation
    
    Clears user session and confirms cancellation
    """
    from handlers import clear_session
    
    user_id = update.effective_user.id
    
    clear_session(user_id)
    
    await update.message.reply_text(
        "❌ **Operation Cancelled**\n\n👇 Type movie/series name to search:",
        parse_mode="Markdown"
    )
    
    log_user(f"User {user_id} cancelled operation via /cancel")


# =============================================================================
# /ID COMMAND
# =============================================================================

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show user's Telegram ID
    
    Useful for users to get their ID for support
    """
    user = update.effective_user
    chat = update.effective_chat
    
    id_text = f"""🆔 **ID INFORMATION**

👤 **Your Info:**
├ 🆔 User ID: `{user.id}`
├ 📛 Name: {user.first_name} {user.last_name or ''}
├ 👤 Username: @{user.username or 'Not set'}
└ 🌐 Language: {user.language_code or 'N/A'}

💬 **Chat Info:**
├ 🆔 Chat ID: `{chat.id}`
└ 📝 Type: {chat.type}

📋 _Tap on ID to copy_"""
    
    await update.message.reply_text(
        id_text,
        parse_mode="Markdown"
    )


# =============================================================================
# /PING COMMAND
# =============================================================================

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Check bot response time
    
    Shows latency for debugging
    """
    import time
    
    start = time.time()
    msg = await update.message.reply_text("🏓 Pinging...")
    end = time.time()
    
    latency = round((end - start) * 1000, 2)
    
    await msg.edit_text(
        f"🏓 **Pong!**\n\n⚡ Latency: `{latency}ms`",
        parse_mode="Markdown"
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Commands
    'help_command',
    'status_command',
    'history_command',
    'about_command',
    'feedback_command',
    'cancel_command',
    'id_command',
    'ping_command',
    
    # Handlers
    'handle_feedback_message',
    'user_callback_handler',
    
    # Inline handlers
    'show_help_inline',
    'show_status_inline',
    'show_history_inline',
    'show_about_inline',
]