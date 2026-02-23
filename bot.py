"""
=============================================================================
BOLLYFLIX BOT - BOT BUILDER & APPLICATION
=============================================================================
Main bot setup, handler registration, and application configuration
=============================================================================
"""

import asyncio
from typing import Optional
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from config import (
    BOT_TOKEN, BOT_NAME, BOT_VERSION,
    MSG_ERROR_GENERIC
)
from logger import (
    log_info, log_success, log_error,
    log_warning, log_bot
)
from database import db

# Import handlers
from handlers import (
    start_command,
    text_handler
)

# Import callbacks
from callbacks import (
    callback_handler,
    extended_callback_handler
)

# Import user commands
from user import (
    help_command,
    status_command,
    history_command,
    about_command,
    feedback_command,
    cancel_command,
    id_command,
    ping_command,
    user_callback_handler,
    handle_feedback_message
)

# Import settings system
from settings import (
    settings_command,
    settings_callback_handler
)

# Import admin commands
from admin import (
    admin_command,
    stats_command,
    users_command,
    ban_command,
    unban_command,
    broadcast_command,
    cache_command,
    logs_command,
    export_command,
    admin_callback_handler,
    admin_panel_command
)

# Import login system
from login import login_conversation, logout_command

# Import WebServer
from web_server import start_web_server, stop_web_server


# =============================================================================
# BOT COMMANDS LIST
# =============================================================================

USER_COMMANDS = [
    BotCommand("start", "🚀 Start the bot"),
    BotCommand("help", "📖 How to use"),
    BotCommand("settings", "⚙️ Your preferences"),
    BotCommand("status", "📊 Your stats"),
    BotCommand("history", "📜 Download history"),
    BotCommand("about", "ℹ️ About bot"),
    BotCommand("cancel", "❌ Cancel operation"),
    BotCommand("id", "🆔 Your Telegram ID"),
    BotCommand("ping", "🏓 Check bot status"),
]

ADMIN_COMMANDS = [
    BotCommand("admin", "🔧 Admin panel"),
    BotCommand("stats", "📊 Bot statistics"),
    BotCommand("users", "👥 User management"),
    BotCommand("ban", "🚫 Ban user"),
    BotCommand("unban", "✅ Unban user"),
    BotCommand("broadcast", "📢 Broadcast message"),
    BotCommand("cache", "🗄️ Cache management"),
    BotCommand("logs", "📜 View logs"),
    BotCommand("export", "📦 Export database"),
    BotCommand("login", "🔑 Login userbot"),
    BotCommand("logout", "🚪 Logout userbot"),
    BotCommand("admin_panel", "🌐 Open Web Admin Dashboard"),
]


# =============================================================================
# ERROR HANDLER
# =============================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Global error handler for the bot
    
    Logs errors and sends friendly message to user
    """
    error = context.error
    
    log_error(f"Bot error: {error}")
    
    # Log full traceback in debug mode
    if hasattr(error, '__traceback__'):
        import traceback
        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        log_error(f"Traceback:\n{tb}")
    
    # Try to notify user
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(MSG_ERROR_GENERIC)
    except:
        pass


# =============================================================================
# COMBINED CALLBACK ROUTER
# =============================================================================

async def combined_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Combined callback handler that routes to appropriate handler
    
    Priority:
    1. Admin callbacks (admin_*, broadcast_*, cache_*)
    2. Settings callbacks (settings_*)
    3. User callbacks (user_*, setting_*)
    4. Main callbacks (quality, season, etc.)
    """
    query = update.callback_query
    data = query.data
    
    # Try admin callbacks first
    if data.startswith(("admin_", "broadcast_", "cache_")):
        handled = await admin_callback_handler(update, context)
        if handled:
            return
    
    # Try settings callbacks
    if data.startswith("settings_"):
        handled = await settings_callback_handler(update, context)
        if handled:
            return
    
    # Try user callbacks
    if data.startswith(("user_", "setting_")):
        handled = await user_callback_handler(update, context)
        if handled:
            return
    
    # Fall through to main callback handler
    await extended_callback_handler(update, context)


# =============================================================================
# TEXT MESSAGE ROUTER
# =============================================================================

async def combined_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Combined text handler that checks for feedback first
    """
    # Check for feedback message
    from handlers import get_session
    
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if session.get("state") == "awaiting_feedback":
        await handle_feedback_message(update, context)
        return
    
    # Normal text handling
    await text_handler(update, context)


# =============================================================================
# STARTUP & SHUTDOWN
# =============================================================================

async def post_init(application: Application):
    """
    Called after bot initialization
    
    - Sets bot commands
    - Logs startup info
    """
    bot = application.bot
    
    # Set commands for users
    await bot.set_my_commands(USER_COMMANDS)
    
    # Get bot info
    me = await bot.get_me()
    
    log_success(f"Bot initialized: @{me.username}")
    log_info(f"Bot ID: {me.id}")
    log_info(f"Bot Name: {me.first_name}")
    
    # Start the WebAdmin API server in the background
    asyncio.create_task(start_web_server(host="0.0.0.0", port=8080))


async def post_shutdown(application: Application):
    """
    Called before bot shutdown
    
    - Saves database
    - Cleanup resources
    """
    log_info("Shutting down bot...")
    
    # Stop WebAdmin Server
    await stop_web_server()
    
    # Save database
    db.save()
    
    log_success("Bot shutdown complete")


# =============================================================================
# APPLICATION BUILDER
# =============================================================================

def create_application() -> Application:
    """
    Create and configure the bot application
    
    Returns:
        Configured Application instance
    """
    log_bot("Creating bot application...")
    
    # Build application
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # =========================================================================
    # REGISTER COMMAND HANDLERS
    # =========================================================================
    
    log_info("Registering command handlers...")
    
    # Basic commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    # User commands
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("ping", ping_command))
    
    # Admin commands
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("cache", cache_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("logout", logout_command))
    
    # WebAdmin Command
    app.add_handler(CommandHandler("admin_panel", admin_panel_command))

    # Login conversation handler (must be before generic text handler)
    app.add_handler(login_conversation)
    
    # =========================================================================
    # REGISTER MESSAGE HANDLERS
    # =========================================================================
    
    log_info("Registering message handlers...")
    
    # Text messages (search, number selection)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            combined_text_handler
        )
    )
    
    # =========================================================================
    # REGISTER CALLBACK HANDLERS
    # =========================================================================
    
    log_info("Registering callback handlers...")
    
    # Combined callback handler
    app.add_handler(CallbackQueryHandler(combined_callback_handler))
    
    # =========================================================================
    # REGISTER ERROR HANDLER
    # =========================================================================
    
    app.add_error_handler(error_handler)
    
    log_success("Bot application created successfully!")
    
    return app


# =============================================================================
# RUN BOT
# =============================================================================

def run_bot():
    """
    Start the bot with polling
    
    This is the main entry point for running the bot
    """
    # Print banner
    print_banner()
    
    # Create application
    app = create_application()
    
    # Run with polling
    log_bot("Starting bot polling...")
    print("\n" + "=" * 50)
    print("🟢 BOT IS RUNNING!")
    print("=" * 50)
    print("📱 Send /start to your bot to begin")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 50 + "\n")
    
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


async def run_bot_async():
    """
    Start the bot asynchronously (for advanced usage)
    
    Useful when integrating with other async frameworks
    """
    app = create_application()
    
    async with app:
        await app.start()
        log_success("Bot started (async mode)")
        
        # Keep running until stopped
        await app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        # Wait forever
        await asyncio.Event().wait()


# =============================================================================
# BANNER
# =============================================================================

def print_banner():
    """Print startup banner"""
    from bypass import get_bypass_status
    
    status = get_bypass_status()
    
    banner = f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗  ██████╗ ██╗     ██╗  ██╗   ██╗███████╗██╗     ║
║   ██╔══██╗██╔═══██╗██║     ██║  ╚██╗ ██╔╝██╔════╝██║     ║
║   ██████╔╝██║   ██║██║     ██║   ╚████╔╝ █████╗  ██║     ║
║   ██╔══██╗██║   ██║██║     ██║    ╚██╔╝  ██╔══╝  ██║     ║
║   ██████╔╝╚██████╔╝███████╗███████╗██║   ██║     ██║     ║
║   ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═╝   ╚═╝     ╚═╝     ║
║                                                           ║
║                    {BOT_NAME} v{BOT_VERSION}                        ║
║                                                           ║
╠═══════════════════════════════════════════════════════════╣
║  📦 Components:                                           ║
║  • Chrome Driver: {'✅ Ready' if status['chrome_available'] else '❌ Not Found'}                              ║
║  • Pyrogram:      {'✅ Ready' if status['pyrogram_available'] else '❌ Not Found'}                              ║
║  • Bypass System: {'✅ Ready' if status['bypass_ready'] else '❌ Not Ready'}                              ║
║                                                           ║
╠═══════════════════════════════════════════════════════════╣
║  🎬 Features:                                             ║
║  • Movie & Series Search                                  ║
║  • Multiple Qualities (480p - 4K)                         ║
║  • Season-wise Downloads                                  ║
║  • Fast Bypass (Timer Nuke)                               ║
║  • User Settings & Preferences                            ║
║  • User Management                                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'create_application',
    'run_bot',
    'run_bot_async',
    'print_banner',
    'error_handler',
    'combined_callback_handler',
    'combined_text_handler',
]