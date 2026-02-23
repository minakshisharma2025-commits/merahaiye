"""
=============================================================================
BOLLYFLIX BOT - ADMIN COMMANDS
=============================================================================
Owner/Admin only commands:
- /admin - Admin panel
- /stats - Detailed statistics
- /users - User management
- /ban - Ban user
- /unban - Unban user
- /broadcast - Send to all users
- /logs - View recent logs
- /cache - Cache management
- /restart - Restart bot
=============================================================================
"""

import os
import asyncio
from datetime import datetime
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    is_owner, is_admin, OWNER_IDS,
    BOT_NAME, BOT_VERSION,
    MSG_ADMIN_PANEL, MSG_ERROR_NOT_AUTHORIZED
)
from logger import (
    log_info, log_success, log_error, 
    log_warning, log_admin
)
from database import db
from helpers import format_size, format_datetime, time_ago, truncate
from handlers import owner_login_status, user_sessions


# =============================================================================
# AUTH CHECK DECORATOR
# =============================================================================

def owner_only(func):
    """Decorator to restrict command to owners only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not is_owner(user_id):
            await update.message.reply_text(MSG_ERROR_NOT_AUTHORIZED)
            log_warning(f"Unauthorized access attempt by {user_id}")
            return
        
        if not owner_login_status.get(user_id, False):
            await update.message.reply_text(
                "🔐 Please login first with /start",
                parse_mode="Markdown"
            )
            return
        
        return await func(update, context)
    
    return wrapper


def admin_only(func):
    """Decorator to restrict command to admins only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            await update.message.reply_text(MSG_ERROR_NOT_AUTHORIZED)
            return
        
        return await func(update, context)
    
    return wrapper


# =============================================================================
# /ADMIN COMMAND
# =============================================================================

@owner_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show admin panel with quick stats and options
    """
    user = update.effective_user
    user_id = user.id
    
    log_admin(f"Admin panel accessed by {user_id}")
    
    # Get stats
    stats = db.get_stats()
    
    # Build admin panel
    admin_text = MSG_ADMIN_PANEL.format(
        name=user.first_name,
        user_id=user_id,
        total_users=stats['users']['total'],
        active_users=stats['users']['active_24h'],
        total_searches=stats['searches']['total'],
        total_downloads=stats['downloads']['total'],
        cache_count=stats['cache']['total_entries']
    )
    
    # Build keyboard
    keyboard = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Users", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🗄️ Cache", callback_data="admin_cache")
        ],
        [
            InlineKeyboardButton("📜 Logs", callback_data="admin_logs"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")
        ]
    ]
    
    await update.message.reply_text(
        admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

@owner_only
async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generate a secure link to the WebAdmin Dashboard
    """
    user_id = update.effective_user.id
    
    # In a real environment, generate a temporary JWT token.
    # For now, we will pass the user_id as a query param and the frontend will use it.
    
    # Fetch ngrok/server URL if configured, otherwise use localhost.
    dashboard_url = f"http://127.0.0.1:8080/?uid={user_id}"
    
    keyboard = [
        [InlineKeyboardButton("🌐 Open Web Dashboard", url=dashboard_url)]
    ]
    
    await update.message.reply_text(
        "🔐 *WebAdmin Dashboard* generated for your session.\n\n"
        "Click the button below to open the dashboard in your browser.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# =============================================================================
# /STATS COMMAND
# =============================================================================

@owner_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show detailed bot statistics
    """
    user_id = update.effective_user.id
    
    log_admin(f"Stats viewed by {user_id}")
    
    stats = db.get_stats()
    
    # Get top users
    top_downloaders = db.get_top_users(limit=5, by="downloads")
    top_searchers = db.get_top_users(limit=5, by="searches")
    
    # Format top users
    top_dl_text = ""
    for i, user in enumerate(top_downloaders, 1):
        name = user.first_name or f"User {user.user_id}"
        top_dl_text += f"  {i}. {truncate(name, 15)} - {user.downloads}\n"
    
    top_search_text = ""
    for i, user in enumerate(top_searchers, 1):
        name = user.first_name or f"User {user.user_id}"
        top_search_text += f"  {i}. {truncate(name, 15)} - {user.searches}\n"
    
    # Calculate averages
    total_users = stats['users']['total'] or 1
    avg_downloads = stats['downloads']['total'] / total_users
    avg_searches = stats['searches']['total'] / total_users
    
    stats_text = f"""📊 **DETAILED STATISTICS**

👥 **Users:**
├ 📈 Total: {stats['users']['total']}
├ ✅ Active (24h): {stats['users']['active_24h']}
├ 🚫 Banned: {stats['users']['banned']}
└ 📊 Active Rate: {(stats['users']['active_24h'] / total_users * 100):.1f}%

🔍 **Searches:**
├ 📈 Total: {stats['searches']['total']}
├ 📝 Logged: {stats['searches']['logged']}
└ 📊 Avg/User: {avg_searches:.1f}

📥 **Downloads:**
├ 📈 Total: {stats['downloads']['total']}
├ 📝 Logged: {stats['downloads']['logged']}
└ 📊 Avg/User: {avg_downloads:.1f}

🗄️ **Cache:**
├ 📁 Entries: {stats['cache']['total_entries']}
└ 🎯 Hits: {stats['cache']['total_hits']}

🏆 **Top Downloaders:**
{top_dl_text or '  No data'}

🔍 **Top Searchers:**
{top_search_text or '  No data'}

⏰ **Bot Info:**
├ 🚀 Started: {stats['bot'].get('started', 'N/A')[:10]}
└ 🔄 Updated: {stats['bot'].get('last_updated', 'N/A')[:19]}"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats"),
            InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
        ]
    ]
    
    await update.message.reply_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =============================================================================
# /USERS COMMAND
# =============================================================================

@owner_only
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show user list and management options
    """
    user_id = update.effective_user.id
    
    log_admin(f"Users list viewed by {user_id}")
    
    # Get recent users
    all_users = db.get_all_users()
    
    # Sort by last active (most recent first)
    all_users.sort(
        key=lambda u: u.last_active or u.joined or "",
        reverse=True
    )
    
    recent_users = all_users[:10]
    
    # Build user list
    users_text = "👥 **USER MANAGEMENT**\n\n"
    users_text += f"📊 Total Users: {len(all_users)}\n\n"
    users_text += "📋 **Recent Users:**\n\n"
    
    for i, user in enumerate(recent_users, 1):
        name = truncate(user.first_name or "Unknown", 15)
        status = "🚫" if user.banned else "✅"
        
        # Time ago
        try:
            last = datetime.fromisoformat(user.last_active or user.joined)
            last_str = time_ago(last)
        except:
            last_str = "N/A"
        
        users_text += (
            f"{status} **{i}.** {name}\n"
            f"    🆔 `{user.user_id}` • {last_str}\n"
            f"    📥 {user.downloads} downloads • 🔍 {user.searches} searches\n\n"
        )
    
    users_text += f"_Showing {len(recent_users)} of {len(all_users)} users_"
    
    keyboard = [
        [
            InlineKeyboardButton("🚫 Banned List", callback_data="admin_banned"),
            InlineKeyboardButton("🔝 Top Users", callback_data="admin_top_users")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_users"),
            InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
        ]
    ]
    
    await update.message.reply_text(
        users_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =============================================================================
# /BAN COMMAND
# =============================================================================

@owner_only
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ban a user from using the bot
    
    Usage: /ban <user_id> [reason]
    """
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ **Usage:** `/ban <user_id> [reason]`\n\n"
            "**Example:**\n"
            "`/ban 123456789 Spamming`",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID! Must be a number.")
        return
    
    # Check if trying to ban owner
    if target_id in OWNER_IDS:
        await update.message.reply_text("❌ Cannot ban an owner!")
        return
    
    # Get reason
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"
    
    # Check if user exists
    target_user = db.get_user(target_id)
    
    if not target_user:
        await update.message.reply_text(
            f"❌ User `{target_id}` not found in database!",
            parse_mode="Markdown"
        )
        return
    
    # Check if already banned
    if target_user.banned:
        await update.message.reply_text(
            f"⚠️ User `{target_id}` is already banned!",
            parse_mode="Markdown"
        )
        return
    
    # Ban user
    success = db.ban_user(target_id, reason)
    
    if success:
        log_admin(f"User {target_id} banned by {user_id}. Reason: {reason}")
        
        await update.message.reply_text(
            f"✅ **User Banned!**\n\n"
            f"🆔 User ID: `{target_id}`\n"
            f"👤 Name: {target_user.first_name or 'Unknown'}\n"
            f"📝 Reason: {reason}\n"
            f"👮 Banned by: {update.effective_user.first_name}",
            parse_mode="Markdown"
        )
        
        # Try to notify the banned user
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🚫 **You have been banned!**\n\n📝 Reason: {reason}",
                parse_mode="Markdown"
            )
        except:
            pass
    else:
        await update.message.reply_text("❌ Failed to ban user!")


# =============================================================================
# /UNBAN COMMAND
# =============================================================================

@owner_only
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Unban a user
    
    Usage: /unban <user_id>
    """
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ **Usage:** `/unban <user_id>`\n\n"
            "**Example:**\n"
            "`/unban 123456789`",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID! Must be a number.")
        return
    
    # Check if user exists
    target_user = db.get_user(target_id)
    
    if not target_user:
        await update.message.reply_text(
            f"❌ User `{target_id}` not found in database!",
            parse_mode="Markdown"
        )
        return
    
    # Check if not banned
    if not target_user.banned:
        await update.message.reply_text(
            f"⚠️ User `{target_id}` is not banned!",
            parse_mode="Markdown"
        )
        return
    
    # Unban user
    success = db.unban_user(target_id)
    
    if success:
        log_admin(f"User {target_id} unbanned by {user_id}")
        
        await update.message.reply_text(
            f"✅ **User Unbanned!**\n\n"
            f"🆔 User ID: `{target_id}`\n"
            f"👤 Name: {target_user.first_name or 'Unknown'}\n"
            f"👮 Unbanned by: {update.effective_user.first_name}",
            parse_mode="Markdown"
        )
        
        # Try to notify the user
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="✅ **You have been unbanned!**\n\nYou can now use the bot again.",
                parse_mode="Markdown"
            )
        except:
            pass
    else:
        await update.message.reply_text("❌ Failed to unban user!")


# =============================================================================
# /BROADCAST COMMAND
# =============================================================================

@owner_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Broadcast message to all users
    
    Usage: Reply to a message with /broadcast
    """
    user_id = update.effective_user.id
    
    # Check if reply
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ **Usage:**\n"
            "Reply to any message with /broadcast\n\n"
            "**Tips:**\n"
            "• You can broadcast text, photos, videos\n"
            "• Message will be copied to all users\n"
            "• Banned users will be skipped",
            parse_mode="Markdown"
        )
        return
    
    broadcast_msg = update.message.reply_to_message
    
    # Get all users
    all_users = db.get_all_users()
    active_users = [u for u in all_users if not u.banned]
    
    if not active_users:
        await update.message.reply_text("❌ No active users to broadcast!")
        return
    
    # Confirm
    confirm_text = (
        f"📢 **BROADCAST CONFIRMATION**\n\n"
        f"👥 Recipients: {len(active_users)} users\n"
        f"📝 Message: {truncate(broadcast_msg.text or '[Media]', 50)}\n\n"
        f"Are you sure you want to broadcast?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Broadcast", callback_data="broadcast_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
        ]
    ]
    
    # Store broadcast message in session
    from handlers import set_session
    set_session(user_id, {
        "state": "broadcast_confirm",
        "broadcast_msg_id": broadcast_msg.message_id,
        "broadcast_chat_id": broadcast_msg.chat.id,
        "target_count": len(active_users)
    })
    
    await update.message.reply_text(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def execute_broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Execute the broadcast after confirmation"""
    query = update.callback_query
    user_id = query.from_user.id
    
    from handlers import get_session, clear_session
    session = get_session(user_id)
    
    if session.get("state") != "broadcast_confirm":
        await query.answer("Session expired!", show_alert=True)
        return
    
    msg_id = session.get("broadcast_msg_id")
    chat_id = session.get("broadcast_chat_id")
    
    clear_session(user_id)
    
    # Update message
    await query.edit_message_text(
        "📢 **Broadcasting...**\n\n⏳ Please wait...",
        parse_mode="Markdown"
    )
    
    # Get users
    all_users = db.get_all_users()
    active_users = [u for u in all_users if not u.banned]
    
    success = 0
    failed = 0
    
    log_admin(f"Broadcast started by {user_id} to {len(active_users)} users")
    
    for user in active_users:
        try:
            await context.bot.copy_message(
                chat_id=user.user_id,
                from_chat_id=chat_id,
                message_id=msg_id
            )
            success += 1
            
            # Small delay to avoid flood
            await asyncio.sleep(0.05)
            
        except Exception as e:
            failed += 1
            log_warning(f"Broadcast failed for {user.user_id}: {e}")
    
    # Final report
    await query.edit_message_text(
        f"📢 **BROADCAST COMPLETE!**\n\n"
        f"✅ Sent: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {success + failed}",
        parse_mode="Markdown"
    )
    
    log_admin(f"Broadcast completed: {success} success, {failed} failed")


# =============================================================================
# /CACHE COMMAND
# =============================================================================

@owner_only
async def cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cache management command
    
    Usage: /cache [clear]
    """
    user_id = update.effective_user.id
    args = context.args
    
    if args and args[0].lower() == "clear":
        # Clear cache
        db.clear_cache()
        
        await update.message.reply_text(
            "✅ **Cache Cleared!**\n\nAll cached URLs have been removed.",
            parse_mode="Markdown"
        )
        
        log_admin(f"Cache cleared by {user_id}")
        return
    
    # Show cache info
    cache_stats = db.get_cache_stats()
    
    cache_text = f"""🗄️ **CACHE MANAGEMENT**

📊 **Statistics:**
├ 📁 Total Entries: {cache_stats['total_entries']}
└ 🎯 Total Hits: {cache_stats['total_hits']}

⚙️ **Commands:**
• `/cache` - Show this info
• `/cache clear` - Clear all cache

💡 **Info:**
Cache stores bypassed URLs for 24 hours
to speed up repeated requests."""
    
    keyboard = [
        [
            InlineKeyboardButton("🗑️ Clear Cache", callback_data="cache_clear"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_cache")
        ],
        [
            InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
        ]
    ]
    
    await update.message.reply_text(
        cache_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =============================================================================
# /LOGS COMMAND
# =============================================================================

@owner_only
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    View recent activity logs
    """
    user_id = update.effective_user.id
    
    log_admin(f"Logs viewed by {user_id}")
    
    # Get recent searches and downloads
    recent_searches = db.get_recent_searches(limit=5)
    recent_downloads = db.get_recent_downloads(limit=5)
    
    logs_text = "📜 **RECENT ACTIVITY LOGS**\n\n"
    
    # Recent searches
    logs_text += "🔍 **Recent Searches:**\n"
    
    if recent_searches:
        for search in recent_searches:
            try:
                search_time = datetime.fromisoformat(search.timestamp)
                time_str = time_ago(search_time)
            except:
                time_str = "N/A"
            
            logs_text += (
                f"  • `{search.user_id}`: {truncate(search.query, 20)} "
                f"({search.results_count} results) - {time_str}\n"
            )
    else:
        logs_text += "  No recent searches\n"
    
    logs_text += "\n📥 **Recent Downloads:**\n"
    
    if recent_downloads:
        for dl in recent_downloads:
            try:
                dl_time = datetime.fromisoformat(dl.timestamp)
                time_str = time_ago(dl_time)
            except:
                time_str = "N/A"
            
            type_emoji = "📺" if dl.content_type == "series" else "🎬"
            
            logs_text += (
                f"  {type_emoji} `{dl.user_id}`: {truncate(dl.title, 20)} "
                f"({dl.quality}) - {time_str}\n"
            )
    else:
        logs_text += "  No recent downloads\n"
    
    # Active sessions
    active_sessions = len(user_sessions)
    logs_text += f"\n👥 **Active Sessions:** {active_sessions}"
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_logs"),
            InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
        ]
    ]
    
    await update.message.reply_text(
        logs_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =============================================================================
# /EXPORT COMMAND
# =============================================================================

@owner_only
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Export database to file
    
    Usage: /export
    """
    user_id = update.effective_user.id
    
    log_admin(f"Database export by {user_id}")
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bollyflix_export_{timestamp}.json"
    
    # Export
    success = db.export_data(filename)
    
    if success and os.path.exists(filename):
        # Send file
        try:
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption=f"📦 **Database Export**\n\n📅 {timestamp}",
                    parse_mode="Markdown"
                )
            
            # Remove local file
            os.remove(filename)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to send file: {e}")
    else:
        await update.message.reply_text("❌ Export failed!")


# =============================================================================
# ADMIN CALLBACK HANDLER
# =============================================================================

async def admin_callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Handle admin-related callbacks
    
    Returns:
        True if callback was handled, False otherwise
    """
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    # Check authorization
    if not is_owner(user_id):
        await query.answer("Not authorized!", show_alert=True)
        return True
    
    if not data.startswith("admin_") and not data.startswith("broadcast_") and not data.startswith("cache_"):
        return False
    
    await query.answer()
    
    # Admin panel callbacks
    if data == "admin_panel":
        await show_admin_panel_inline(query, context)
    
    elif data == "admin_stats":
        await show_stats_inline(query, context)
    
    elif data == "admin_users":
        await show_users_inline(query, context)
    
    elif data == "admin_logs":
        await show_logs_inline(query, context)
    
    elif data == "admin_cache":
        await show_cache_inline(query, context)
    
    elif data == "admin_refresh":
        await show_admin_panel_inline(query, context)
    
    elif data == "admin_banned":
        await show_banned_users_inline(query, context)
    
    elif data == "admin_top_users":
        await show_top_users_inline(query, context)
    
    # Broadcast callbacks
    elif data == "broadcast_confirm":
        await execute_broadcast(update, context)
    
    elif data == "broadcast_cancel":
        from handlers import clear_session
        clear_session(user_id)
        await query.edit_message_text("❌ Broadcast cancelled.")
    
    # Cache callbacks
    elif data == "cache_clear":
        db.clear_cache()
        await query.answer("✅ Cache cleared!", show_alert=True)
        await show_cache_inline(query, context)
    
    else:
        return False
    
    return True


# =============================================================================
# INLINE ADMIN DISPLAYS
# =============================================================================

async def show_admin_panel_inline(query, context):
    """Show admin panel inline"""
    user = query.from_user
    stats = db.get_stats()
    
    admin_text = MSG_ADMIN_PANEL.format(
        name=user.first_name,
        user_id=user.id,
        total_users=stats['users']['total'],
        active_users=stats['users']['active_24h'],
        total_searches=stats['searches']['total'],
        total_downloads=stats['downloads']['total'],
        cache_count=stats['cache']['total_entries']
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Users", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("🗄️ Cache", callback_data="admin_cache")
        ],
        [
            InlineKeyboardButton("📜 Logs", callback_data="admin_logs"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")
        ]
    ]
    
    try:
        await query.edit_message_text(
            admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_stats_inline(query, context):
    """Show stats inline"""
    stats = db.get_stats()
    total_users = stats['users']['total'] or 1
    
    stats_text = f"""📊 **BOT STATISTICS**

👥 **Users:** {stats['users']['total']}
├ ✅ Active (24h): {stats['users']['active_24h']}
└ 🚫 Banned: {stats['users']['banned']}

🔍 **Searches:** {stats['searches']['total']}
📥 **Downloads:** {stats['downloads']['total']}
🗄️ **Cache:** {stats['cache']['total_entries']} entries

📊 **Averages:**
├ 📥 Downloads/User: {stats['downloads']['total'] / total_users:.1f}
└ 🔍 Searches/User: {stats['searches']['total'] / total_users:.1f}"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        ]
    ]
    
    try:
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_users_inline(query, context):
    """Show users inline"""
    all_users = db.get_all_users()
    all_users.sort(key=lambda u: u.last_active or "", reverse=True)
    recent = all_users[:8]
    
    users_text = f"👥 **USERS** ({len(all_users)} total)\n\n"
    
    for i, user in enumerate(recent, 1):
        name = truncate(user.first_name or "Unknown", 12)
        status = "🚫" if user.banned else "✅"
        users_text += f"{status} {i}. {name} (`{user.user_id}`)\n"
    
    keyboard = [
        [
            InlineKeyboardButton("🚫 Banned", callback_data="admin_banned"),
            InlineKeyboardButton("🏆 Top", callback_data="admin_top_users")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_users"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        ]
    ]
    
    try:
        await query.edit_message_text(
            users_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_banned_users_inline(query, context):
    """Show banned users inline"""
    banned = db.get_banned_users()
    
    if not banned:
        text = "🚫 **BANNED USERS**\n\n✅ No banned users!"
    else:
        text = f"🚫 **BANNED USERS** ({len(banned)})\n\n"
        for i, user in enumerate(banned[:10], 1):
            name = truncate(user.first_name or "Unknown", 15)
            reason = user.ban_reason or "No reason"
            text += f"{i}. {name} (`{user.user_id}`)\n   📝 {truncate(reason, 30)}\n\n"
    
    keyboard = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_users")
        ]
    ]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_top_users_inline(query, context):
    """Show top users inline"""
    top_dl = db.get_top_users(5, "downloads")
    top_search = db.get_top_users(5, "searches")
    
    text = "🏆 **TOP USERS**\n\n"
    
    text += "📥 **Top Downloaders:**\n"
    for i, user in enumerate(top_dl, 1):
        name = truncate(user.first_name or "Unknown", 12)
        text += f"  {i}. {name}: {user.downloads}\n"
    
    text += "\n🔍 **Top Searchers:**\n"
    for i, user in enumerate(top_search, 1):
        name = truncate(user.first_name or "Unknown", 12)
        text += f"  {i}. {name}: {user.searches}\n"
    
    keyboard = [
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_users")
        ]
    ]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_logs_inline(query, context):
    """Show logs inline"""
    searches = db.get_recent_searches(5)
    downloads = db.get_recent_downloads(5)
    
    text = "📜 **RECENT LOGS**\n\n🔍 **Searches:**\n"
    
    for s in searches:
        text += f"  • `{s.user_id}`: {truncate(s.query, 15)}\n"
    
    text += "\n📥 **Downloads:**\n"
    
    for d in downloads:
        text += f"  • `{d.user_id}`: {truncate(d.title, 15)}\n"
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_logs"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        ]
    ]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


async def show_cache_inline(query, context):
    """Show cache inline"""
    stats = db.get_cache_stats()
    
    text = f"""🗄️ **CACHE INFO**

📁 Entries: {stats['total_entries']}
🎯 Hits: {stats['total_hits']}

💡 Cache stores bypassed URLs for 24h"""
    
    keyboard = [
        [
            InlineKeyboardButton("🗑️ Clear", callback_data="cache_clear"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_cache")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        ]
    ]
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass


# =============================================================================
# /ADMIN_PANEL COMMAND
# =============================================================================

async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Get secure link to WebAdmin Dashboard
    """
    user_id = update.effective_user.id
    
    role = db.get_user_role(user_id)
    if role not in ["owner", "admin", "manager"]:
        await update.message.reply_text("⛔ You do not have permission to access the WebAdmin Dashboard.")
        return
        
    dashboard_url = f"http://127.0.0.1:8080/?uid={user_id}"
    
    keyboard = [[InlineKeyboardButton("Open Dashboard", url=dashboard_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔐 **WebAdmin Dashboard Access**\n\n"
        f"Your role: `{role.upper()}`\n"
        f"Click the button below to access the secure live dashboard. Do not share this link.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    log_admin(f"User {user_id} requested WebAdmin access link")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Decorators
    'owner_only',
    'admin_only',
    
    # Commands
    'admin_command',
    'stats_command',
    'users_command',
    'ban_command',
    'unban_command',
    'broadcast_command',
    'cache_command',
    'logs_command',
    'export_command',
    'admin_panel_command',
    
    # Handlers
    'admin_callback_handler',
    'execute_broadcast',
]