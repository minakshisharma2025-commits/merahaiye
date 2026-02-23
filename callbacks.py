"""
=============================================================================
BOLLYFLIX BOT - CALLBACK HANDLERS
=============================================================================
All inline button callback handlers:
- Confirmation buttons
- Quality selection (with user preference)
- Season selection
- Navigation (back, cancel)
- Pagination for large season lists
=============================================================================
"""

import asyncio
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    MSG_SELECT_QUALITY, MSG_SELECT_SEASON, MSG_SELECT_SEASON_QUALITY,
    MSG_CANCELLED, MSG_ERROR_SESSION_EXPIRED,
    MSG_ERROR_NO_SEASONS, MSG_ERROR_NO_QUALITIES,
    BTN_CANCEL, BTN_BACK_SEASONS, BTN_GET_LINK,
    QUALITY_ICONS
)
from logger import log_info, log_debug, log_warning
from helpers import sort_qualities
from scraper import get_seasons_list
from handlers import (
    get_session, set_session, clear_session,
    process_movie_download, process_series_download
)
from settings import apply_quality_preference, get_user_quality


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_quality_icon(quality: str) -> str:
    """Get emoji icon for quality"""
    return QUALITY_ICONS.get(quality, "📥")


def build_quality_keyboard(
    qualities: List[str],
    callback_prefix: str = "quality",
    user_id: int = None
) -> InlineKeyboardMarkup:
    """
    Build quality selection keyboard

    Applies user preference to reorder qualities
    """
    keyboard = []

    sorted_qualities = sort_qualities(qualities)

    # Apply user preference if available
    if user_id:
        sorted_qualities = apply_quality_preference(user_id, sorted_qualities)

    # Mark preferred quality
    preferred = get_user_quality(user_id) if user_id else "auto"

    for quality in sorted_qualities:
        icon = get_quality_icon(quality)

        # Add star if this is user's preferred quality
        if preferred != "auto" and quality == preferred:
            label = f"{icon} {quality} ⭐"
        else:
            label = f"{icon} {quality}"

        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"{callback_prefix}_{quality}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(BTN_CANCEL, callback_data="cancel")
    ])

    return InlineKeyboardMarkup(keyboard)


def build_season_keyboard(seasons: List[str]) -> InlineKeyboardMarkup:
    """
    Build season selection keyboard

    Single column for <=6, two columns for more
    """
    keyboard = []

    if len(seasons) <= 6:
        for season in seasons:
            keyboard.append([
                InlineKeyboardButton(
                    f"📁 {season}",
                    callback_data=f"season_{season}"
                )
            ])
    else:
        for i in range(0, len(seasons), 2):
            row = [
                InlineKeyboardButton(
                    f"📁 {seasons[i]}",
                    callback_data=f"season_{seasons[i]}"
                )
            ]

            if i + 1 < len(seasons):
                row.append(
                    InlineKeyboardButton(
                        f"📁 {seasons[i + 1]}",
                        callback_data=f"season_{seasons[i + 1]}"
                    )
                )

            keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton(BTN_CANCEL, callback_data="cancel")
    ])

    return InlineKeyboardMarkup(keyboard)


def build_season_quality_keyboard(
    qualities: List[str],
    season: str,
    user_id: int = None
) -> InlineKeyboardMarkup:
    """
    Build quality keyboard for specific season

    Applies user preference to reorder
    """
    keyboard = []

    sorted_qualities = sort_qualities(qualities)

    if user_id:
        sorted_qualities = apply_quality_preference(user_id, sorted_qualities)

    preferred = get_user_quality(user_id) if user_id else "auto"

    for quality in sorted_qualities:
        icon = get_quality_icon(quality)

        if preferred != "auto" and quality == preferred:
            label = f"{icon} {quality} ⭐"
        else:
            label = f"{icon} {quality}"

        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"series_quality_{quality}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(BTN_BACK_SEASONS, callback_data="back_to_seasons")
    ])

    keyboard.append([
        InlineKeyboardButton(BTN_CANCEL, callback_data="cancel")
    ])

    return InlineKeyboardMarkup(keyboard)


# =============================================================================
# MAIN CALLBACK HANDLER
# =============================================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main callback query handler

    Routes callbacks to appropriate handlers
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    log_debug(f"Callback from {user_id}: {data}")

    if data == "cancel":
        await handle_cancel(update, context)

    elif data == "confirm_yes":
        await handle_confirm(update, context)

    elif data.startswith("dl_"):
        await handle_download_link(update, context, data)

    elif data.startswith("movie_quality_"):
        quality = data.replace("movie_quality_", "")
        await process_movie_download(update, context, quality)

    elif data.startswith("season_") and not data.startswith("season_quality") and not data.startswith("season_page"):
        season = data.replace("season_", "")
        await handle_season_select(update, context, season)

    elif data == "back_to_seasons":
        await handle_back_to_seasons(update, context)

    elif data.startswith("series_quality_"):
        quality = data.replace("series_quality_", "")
        await process_series_download(update, context, quality)

    else:
        log_warning(f"Unknown callback: {data}")


# =============================================================================
# CANCEL HANDLER
# =============================================================================

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel button"""
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    clear_session(user_id)

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=MSG_CANCELLED,
        parse_mode="Markdown"
    )

    log_info(f"User {user_id} cancelled")


# =============================================================================
# CONFIRMATION HANDLER
# =============================================================================

async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle download confirmation

    Movies → quality selection
    Series → season selection
    """
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]

    if content.get("is_series"):
        await show_season_selection(update, context)
    else:
        await show_movie_quality_selection(update, context)


# =============================================================================
# MOVIE QUALITY SELECTION
# =============================================================================

async def show_movie_quality_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Show quality selection for movie"""
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]

    session["state"] = "select_quality"
    set_session(user_id, session)

    qualities = content.get("qualities", ["720p"])
    if not qualities:
        qualities = ["720p"]

    caption = MSG_SELECT_QUALITY.format(title=content["clean_title"])
    keyboard = build_quality_keyboard(qualities, "movie_quality", user_id)

    await edit_or_send(query, context, caption, keyboard)


# =============================================================================
# SEASON SELECTION
# =============================================================================

async def show_season_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Show season selection for series"""
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]

    session["state"] = "select_season"
    set_session(user_id, session)

    seasons_data = content.get("seasons", {})
    seasons_list = get_seasons_list(seasons_data)

    if not seasons_list:
        await query.answer(MSG_ERROR_NO_SEASONS, show_alert=True)
        return

    caption = MSG_SELECT_SEASON.format(title=content["clean_title"])

    # Use pagination if too many seasons
    if len(seasons_list) > 12:
        await handle_season_page(update, context, 0)
        return

    keyboard = build_season_keyboard(seasons_list)

    await edit_or_send(query, context, caption, keyboard)


# =============================================================================
# SEASON SELECT HANDLER
# =============================================================================

async def handle_season_select(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    season: str
):
    """Handle season selection, show quality options"""
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]

    session["state"] = "select_season_quality"
    session["selected_season"] = season
    set_session(user_id, session)

    log_info(f"User {user_id} selected: {season}")

    season_data = content.get("seasons", {}).get(season, {})
    qualities = list(season_data.keys())

    if not qualities:
        await query.answer(MSG_ERROR_NO_QUALITIES, show_alert=True)
        return

    caption = MSG_SELECT_SEASON_QUALITY.format(
        title=content["clean_title"],
        season=season
    )

    keyboard = build_season_quality_keyboard(qualities, season, user_id)

    await edit_or_send(query, context, caption, keyboard)


# =============================================================================
# BACK TO SEASONS
# =============================================================================

async def handle_back_to_seasons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Handle back to seasons button"""
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    session.pop("selected_season", None)
    session["state"] = "select_season"
    set_session(user_id, session)

    await show_season_selection(update, context)


# =============================================================================
# EDIT OR SEND MESSAGE
# =============================================================================

async def edit_or_send(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = "Markdown"
):
    """
    Edit message or send new if edit fails

    Handles both photo and text messages
    """
    chat_id = query.message.chat_id

    try:
        if query.message.photo:
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except Exception as e:
        log_warning(f"Edit failed, sending new: {e}")

        try:
            await query.message.delete()
        except:
            pass

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )


# =============================================================================
# ADVANCED CALLBACKS
# =============================================================================

async def handle_refresh_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Handle refresh link button"""
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]
    quality = session.get("last_quality", "720p")

    await query.answer("Refreshing link...", show_alert=False)

    if content.get("is_series"):
        await process_series_download(update, context, quality)
    else:
        await process_movie_download(update, context, quality)


async def handle_change_quality(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Handle change quality button"""
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]

    if content.get("is_series"):
        if "selected_season" in session:
            await handle_season_select(
                update, context,
                session["selected_season"]
            )
        else:
            await show_season_selection(update, context)
    else:
        await show_movie_quality_selection(update, context)


async def handle_report_issue(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Handle report issue button"""
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)
    content = session.get("content", {})

    await query.answer(
        "Issue reported. Admin will check.",
        show_alert=True
    )

    log_warning(
        f"Issue reported by {user_id}: "
        f"{content.get('clean_title', 'Unknown')}"
    )


# =============================================================================
# DOWNLOAD LINK DELIVERY (Hidden URL System + Limits + Pyrogram)
# =============================================================================

async def handle_download_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    link_type: str
):
    """
    Deliver hidden download link with:
    - Daily limit check (free=10, premium=30)
    - Pyrogram direct file delivery for TG links
    - Psychology UX + auto-delete
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    session = get_session(user_id)

    # Get the real URL from session
    url = session.get(link_type)
    title = session.get("dl_title", "File")
    quality = session.get("dl_quality", "")

    # Escape markdown for Telegram
    esc_title = title.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
    esc_quality = quality.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')

    if not url:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ *Link expired.* Please search again.",
            parse_mode="Markdown"
        )
        return

    # ── Daily Limit Check ──
    from config import FREE_DAILY_LIMIT, PREMIUM_DAILY_LIMIT
    from database import db as download_db

    today_count = download_db.get_today_download_count(user_id)
    is_premium = download_db.is_premium_user(user_id)
    daily_limit = PREMIUM_DAILY_LIMIT if is_premium else FREE_DAILY_LIMIT

    if today_count >= daily_limit:
        tier = "Premium" if is_premium else "Free"
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🚫 *Daily limit reached!* ({today_count}/{daily_limit})\n\n"
                f"_{'Upgrade to Premium for 30 downloads/day!' if not is_premium else 'Premium limit reached for today.'}_"
            ),
            parse_mode="Markdown"
        )
        return

    # ── Pyrogram Direct Delivery (for TG links) ──
    if link_type == "dl_telegram":
        try:
            from bypass import telegram_interceptor, PYROGRAM_AVAILABLE

            if PYROGRAM_AVAILABLE:
                # Show sending animation
                msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"📤 *Sending file via Telegram...*\n\n"
                        f"🎬 {esc_title}\n"
                        f"📊 Quality: {esc_quality}\n\n"
                        f"⏳ Please wait, fetching your file..."
                    ),
                    parse_mode="Markdown"
                )

                # Intercept file from gdflix bot
                file_info = await telegram_interceptor.intercept(url)

                if file_info:
                    # Forward file directly to user
                    caption = (
                        f"✅ *{esc_title}*\n"
                        f"📊 Quality: {esc_quality}\n"
                        f"📥 Downloaded via BollyFlix Bot"
                    )
                    sent = await telegram_interceptor.forward_to_user(
                        file_info, chat_id, caption
                    )

                    if sent:
                        try:
                            await msg.delete()
                        except:
                            pass

                        # Log download
                        download_db.log_download(
                            user_id, title, quality,
                            "telegram_direct"
                        )

                        log_info(f"Direct TG delivery: {title} → user {user_id}")
                        clear_session(user_id)
                        return

                # Intercept failed — fallback to URL button
                try:
                    await msg.delete()
                except:
                    pass
                log_warning(f"Pyrogram intercept failed for {title}, falling back to URL")

        except ImportError:
            pass
        except Exception as e:
            log_warning(f"Pyrogram delivery error: {e}")

    # ── Fallback: URL Button with Psychology UX ──
    if link_type == "dl_telegram":
        sending_text = (
            f"📤 *Sending file via Telegram...*\n\n"
            f"🎬 {esc_title}\n"
            f"📊 Quality: {esc_quality}\n\n"
            f"⏳ Please wait..."
        )
    else:
        sending_text = (
            f"📤 *Preparing your download...*\n\n"
            f"🎬 {esc_title}\n"
            f"📊 Quality: {esc_quality}\n\n"
            f"⏳ Generating secure link..."
        )

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=sending_text,
        parse_mode="Markdown"
    )

    await asyncio.sleep(2)

    try:
        await msg.delete()
    except:
        pass

    # Build the actual link message (temporary)
    remaining = daily_limit - today_count - 1
    tier_label = "Premium" if is_premium else "Free"

    if link_type == "dl_telegram":
        link_text = (
            f"✅ *Your file is ready!*\n\n"
            f"🎬 {esc_title}\n"
            f"📊 Quality: {esc_quality}\n\n"
            f"👇 Tap below to get your file\n\n"
            f"📉 _{tier_label}: {remaining} downloads left today_\n"
            f"⚠️ _This message will auto-delete in 60 seconds_"
        )
        btn_text = "📥 Open in Telegram"
    else:
        link_text = (
            f"✅ *Your download is ready!*\n\n"
            f"🎬 {esc_title}\n"
            f"📊 Quality: {esc_quality}\n\n"
            f"👇 Tap below to download\n\n"
            f"📉 _{tier_label}: {remaining} downloads left today_\n"
            f"⚠️ _This message will auto-delete in 60 seconds_"
        )
        btn_text = "📥 Download Now"

    keyboard = [[InlineKeyboardButton(btn_text, url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    link_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=link_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    # Log download
    download_db.log_download(user_id, title, quality, link_type)
    log_info(f"User {user_id} clicked {link_type}: {title} ({quality}) [{today_count+1}/{daily_limit}]")

    clear_session(user_id)

    # Auto-delete after 60 seconds
    await asyncio.sleep(60)
    try:
        await link_msg.delete()
    except:
        pass


# =============================================================================
# SEASON PAGINATION
# =============================================================================

async def handle_season_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int
):
    """Handle season pagination for large season lists"""
    query = update.callback_query
    user_id = query.from_user.id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]
    seasons_data = content.get("seasons", {})
    seasons_list = get_seasons_list(seasons_data)

    page_size = 8
    start = page * page_size
    end = start + page_size

    current_page_seasons = seasons_list[start:end]

    if not current_page_seasons:
        await query.answer("No more seasons", show_alert=True)
        return

    keyboard = []

    # Two column layout
    for i in range(0, len(current_page_seasons), 2):
        row = [
            InlineKeyboardButton(
                f"📁 {current_page_seasons[i]}",
                callback_data=f"season_{current_page_seasons[i]}"
            )
        ]

        if i + 1 < len(current_page_seasons):
            row.append(
                InlineKeyboardButton(
                    f"📁 {current_page_seasons[i + 1]}",
                    callback_data=f"season_{current_page_seasons[i + 1]}"
                )
            )

        keyboard.append(row)

    # Navigation
    nav_row = []

    if page > 0:
        nav_row.append(
            InlineKeyboardButton("◀ Prev", callback_data=f"season_page_{page - 1}")
        )

    if end < len(seasons_list):
        nav_row.append(
            InlineKeyboardButton("Next ▶", callback_data=f"season_page_{page + 1}")
        )

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(BTN_CANCEL, callback_data="cancel")
    ])

    total_pages = (len(seasons_list) + page_size - 1) // page_size

    caption = (
        f"**{content['clean_title']}**\n\n"
        f"Select a season (Page {page + 1}/{total_pages}) 👇"
    )

    await edit_or_send(
        query, context, caption,
        InlineKeyboardMarkup(keyboard)
    )


# =============================================================================
# EXTENDED CALLBACK ROUTER
# =============================================================================

async def extended_callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Extended callback handler with all features
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    log_debug(f"Callback from {user_id}: {data}")

    # Standard callbacks
    if data == "cancel":
        await handle_cancel(update, context)

    elif data == "confirm_yes":
        await handle_confirm(update, context)

    elif data.startswith("dl_"):
        await handle_download_link(update, context, data)

    elif data.startswith("movie_quality_"):
        quality = data.replace("movie_quality_", "")
        await process_movie_download(update, context, quality)

    elif data.startswith("season_") and not data.startswith("season_quality") and not data.startswith("season_page"):
        season = data.replace("season_", "")
        await handle_season_select(update, context, season)

    elif data == "back_to_seasons":
        await handle_back_to_seasons(update, context)

    elif data.startswith("series_quality_"):
        quality = data.replace("series_quality_", "")
        await process_series_download(update, context, quality)

    # Extended callbacks
    elif data == "refresh_link":
        await handle_refresh_link(update, context)

    elif data == "change_quality":
        await handle_change_quality(update, context)

    elif data == "report_issue":
        await handle_report_issue(update, context)

    elif data.startswith("season_page_"):
        page = int(data.replace("season_page_", ""))
        await handle_season_page(update, context, page)

    else:
        log_warning(f"Unknown callback: {data}")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'callback_handler',
    'extended_callback_handler',

    'handle_cancel',
    'handle_confirm',
    'show_movie_quality_selection',
    'show_season_selection',
    'handle_season_select',
    'handle_back_to_seasons',

    'handle_refresh_link',
    'handle_change_quality',
    'handle_report_issue',
    'handle_season_page',
    'handle_download_link',

    'build_quality_keyboard',
    'build_season_keyboard',
    'build_season_quality_keyboard',
    'edit_or_send',
]