"""
=============================================================================
BOLLYFLIX BOT - LOGIN SYSTEM (Pyrogram Session Manager)
=============================================================================
Allows OWNER to log in a Telegram user account for file interception.
The session is stored in database and used by TelegramInterceptor.

Commands:
  /login  - Start login flow (OWNER only)
  /logout - Clear session and logout

Based on devgagan's login system, adapted for python-telegram-bot.
=============================================================================
"""

import os
import asyncio
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import API_ID, API_HASH, OWNER_IDS
from logger import log_info, log_success, log_error, log_warning
from database import db

# Pyrogram (optional)
try:
    from pyrogram import Client
    from pyrogram.errors import (
        ApiIdInvalid,
        PhoneNumberInvalid,
        PhoneCodeInvalid,
        PhoneCodeExpired,
        SessionPasswordNeeded,
        PasswordHashInvalid,
        FloodWait,
    )
    PYROGRAM_OK = True
except ImportError:
    PYROGRAM_OK = False
    log_warning("Pyrogram not installed — /login disabled")


# Conversation states
PHONE, OTP, TWO_FA = range(3)

# Temp storage for login flow
_login_clients = {}


# =============================================================================
# OWNER CHECK
# =============================================================================

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


# =============================================================================
# /login COMMAND
# =============================================================================

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start Pyrogram login flow (OWNER only)"""
    user_id = update.effective_user.id

    if not is_owner(user_id):
        await update.message.reply_text("⛔ Only bot owner can use /login")
        return ConversationHandler.END

    if not PYROGRAM_OK:
        await update.message.reply_text(
            "❌ Pyrogram not installed!\n"
            "Run: `pip install pyrogram`",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    if not API_ID or not API_HASH:
        await update.message.reply_text(
            "❌ API\\_ID or API\\_HASH not set!\n\n"
            "Set them in `config.py` or as environment variables.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    # Check if already logged in
    existing = db.get_session(user_id)
    if existing:
        await update.message.reply_text(
            "⚠️ Already logged in!\n"
            "Use /logout first to re-login.",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📲 *Pyrogram Login*\n\n"
        "Enter your phone number with country code:\n"
        "Example: `+919876543210`\n\n"
        "Type /cancel to abort.",
        parse_mode="Markdown",
    )
    return PHONE


# =============================================================================
# PHONE NUMBER HANDLER
# =============================================================================

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number input"""
    user_id = update.effective_user.id
    phone = update.message.text.strip()

    if not phone.startswith("+"):
        await update.message.reply_text(
            "❌ Phone must start with `+` and country code.\n"
            "Example: `+919876543210`",
            parse_mode="Markdown",
        )
        return PHONE

    await update.message.reply_text("📲 Sending OTP...")

    try:
        session_name = f"session_{user_id}"
        client = Client(session_name, api_id=int(API_ID), api_hash=API_HASH)
        await client.connect()

        code = await client.send_code(phone)

        # Store for later
        _login_clients[user_id] = {
            "client": client,
            "phone": phone,
            "code_hash": code.phone_code_hash,
        }

        await update.message.reply_text(
            "✅ OTP sent to your Telegram!\n\n"
            "Enter the OTP with spaces between digits:\n"
            "Example: If OTP is `12345`, type: `1 2 3 4 5`\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown",
        )
        return OTP

    except ApiIdInvalid:
        await update.message.reply_text("❌ Invalid API\\_ID / API\\_HASH combination.")
        return ConversationHandler.END
    except PhoneNumberInvalid:
        await update.message.reply_text("❌ Invalid phone number. Try again.")
        return PHONE
    except FloodWait as e:
        await update.message.reply_text(f"⏳ FloodWait: Try again after {e.value} seconds.")
        return ConversationHandler.END
    except Exception as e:
        log_error(f"Login send_code error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return ConversationHandler.END


# =============================================================================
# OTP HANDLER
# =============================================================================

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OTP input"""
    user_id = update.effective_user.id
    otp = update.message.text.replace(" ", "").strip()

    data = _login_clients.get(user_id)
    if not data:
        await update.message.reply_text("❌ Session expired. Start /login again.")
        return ConversationHandler.END

    client = data["client"]
    phone = data["phone"]
    code_hash = data["code_hash"]

    try:
        await client.sign_in(phone, code_hash, otp)

        # Success — export session
        session_string = await client.export_session_string()
        db.set_session(user_id, session_string)
        await client.disconnect()

        # Clean up temp files
        _cleanup_session_files(user_id)
        _login_clients.pop(user_id, None)

        await update.message.reply_text(
            "✅ *Login successful!*\n\n"
            "Your session is saved. The bot will now use this account "
            "to send files directly to users.\n\n"
            "Use /logout to disconnect.",
            parse_mode="Markdown",
        )
        log_success(f"Pyrogram login successful for owner {user_id}")
        return ConversationHandler.END

    except PhoneCodeInvalid:
        await update.message.reply_text("❌ Invalid OTP. Try again:")
        return OTP
    except PhoneCodeExpired:
        await update.message.reply_text("❌ OTP expired. Start /login again.")
        _login_clients.pop(user_id, None)
        return ConversationHandler.END
    except SessionPasswordNeeded:
        await update.message.reply_text(
            "🔒 *Two-Step Verification*\n\n"
            "Enter your 2FA password:\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown",
        )
        return TWO_FA
    except Exception as e:
        log_error(f"Login sign_in error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return ConversationHandler.END


# =============================================================================
# TWO-FACTOR AUTH HANDLER
# =============================================================================

async def handle_two_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 2FA password"""
    user_id = update.effective_user.id
    password = update.message.text.strip()

    data = _login_clients.get(user_id)
    if not data:
        await update.message.reply_text("❌ Session expired. Start /login again.")
        return ConversationHandler.END

    client = data["client"]

    try:
        await client.check_password(password)

        # Success — export session
        session_string = await client.export_session_string()
        db.set_session(user_id, session_string)
        await client.disconnect()

        # Clean up
        _cleanup_session_files(user_id)
        _login_clients.pop(user_id, None)

        await update.message.reply_text(
            "✅ *Login successful!*\n\n"
            "Your session is saved. The bot will now use this account "
            "to send files directly to users.\n\n"
            "Use /logout to disconnect.",
            parse_mode="Markdown",
        )
        log_success(f"Pyrogram login (2FA) successful for owner {user_id}")
        return ConversationHandler.END

    except PasswordHashInvalid:
        await update.message.reply_text("❌ Wrong password. Try again:")
        return TWO_FA
    except Exception as e:
        log_error(f"Login 2FA error: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        return ConversationHandler.END


# =============================================================================
# /logout COMMAND
# =============================================================================

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear session and logout"""
    user_id = update.effective_user.id

    if not is_owner(user_id):
        await update.message.reply_text("⛔ Only bot owner can use /logout")
        return

    removed = db.remove_session(user_id)
    _cleanup_session_files(user_id)
    _login_clients.pop(user_id, None)

    if removed:
        await update.message.reply_text(
            "✅ Logged out! Session cleared from database and disk."
        )
        log_info(f"Owner {user_id} logged out")
    else:
        await update.message.reply_text("ℹ️ No active session found.")


# =============================================================================
# CANCEL
# =============================================================================

async def login_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel login flow"""
    user_id = update.effective_user.id

    data = _login_clients.pop(user_id, None)
    if data and data.get("client"):
        try:
            await data["client"].disconnect()
        except:
            pass

    _cleanup_session_files(user_id)

    await update.message.reply_text("❌ Login cancelled.")
    return ConversationHandler.END


# =============================================================================
# HELPERS
# =============================================================================

def _cleanup_session_files(user_id: int):
    """Remove temp session files from disk"""
    for ext in ["", "-journal"]:
        path = f"session_{user_id}.session{ext}"
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass


def get_active_session_string() -> str:
    """Get the first available session string from any owner"""
    for owner_id in OWNER_IDS:
        session = db.get_session(owner_id)
        if session:
            return session
    return None


# =============================================================================
# CONVERSATION HANDLER (register in bot.py)
# =============================================================================

login_conversation = ConversationHandler(
    entry_points=[CommandHandler("login", login_command)],
    states={
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
        OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
        TWO_FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_two_fa)],
    },
    fallbacks=[CommandHandler("cancel", login_cancel)],
)
