"""
=============================================================================
BOLLYFLIX BOT - MESSAGE HANDLERS
=============================================================================
All user-facing message handlers:
- /start command with welcome image
- Search handling
- Number selection
- Content display
- Download processing
=============================================================================
"""

import asyncio
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    is_owner, ADMIN_PASSWORD, MAX_LOGIN_ATTEMPTS,
    BOT_NAME,
    WELCOME_IMAGE_URL, WELCOME_IMAGE_ENABLED,
    MSG_WELCOME, MSG_WELCOME_BACK,
    MSG_OWNER_LOGIN, MSG_LOGIN_SUCCESS,
    MSG_LOGIN_FAILED, MSG_LOGIN_BLOCKED,
    MSG_SEARCHING, MSG_NO_RESULTS, MSG_SEARCH_RESULTS,
    MSG_TOO_SHORT, MSG_LOADING,
    MSG_MOVIE_INFO, MSG_SERIES_INFO,
    MSG_FETCHING, MSG_BYPASSING, MSG_GENERATING,
    MSG_MOVIE_READY, MSG_SERIES_READY,
    MSG_ERROR_GENERIC, MSG_ERROR_SESSION_EXPIRED,
    MSG_ERROR_BANNED, MSG_CANCELLED,
    BTN_CONFIRM_YES, BTN_CANCEL,
    BTN_SEARCH, BTN_SETTINGS, BTN_HELP, BTN_HISTORY,
    BTN_STATUS, BTN_ABOUT
)
from logger import log_info, log_success, log_error, log_warning, log_user
from database import db
from helpers import generate_stars, sort_qualities, extract_tg_from_fastdl, extract_tg_from_fxlinks
from scraper import search_bollyflix, scrape_content, get_seasons_list
from bypass import full_bypass, is_bypass_available
from settings import get_user_results_count, apply_settings_to_results


# =============================================================================
# SESSION STORAGE
# =============================================================================

user_sessions: Dict[int, Dict[str, Any]] = {}
owner_login_status: Dict[int, bool] = {}
login_attempts: Dict[int, int] = {}


# =============================================================================
# SESSION HELPERS
# =============================================================================

def get_session(user_id: int) -> Dict[str, Any]:
    """Get user session or create empty one"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    return user_sessions[user_id]


def set_session(user_id: int, data: Dict[str, Any]):
    """Set user session data"""
    user_sessions[user_id] = data


def clear_session(user_id: int):
    """Clear user session"""
    user_sessions.pop(user_id, None)


def is_owner_logged_in(user_id: int) -> bool:
    """Check if owner is logged in"""
    return owner_login_status.get(user_id, False)


# =============================================================================
# WELCOME KEYBOARD
# =============================================================================

def build_welcome_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Build welcome message keyboard"""
    buttons = [
        [
            InlineKeyboardButton(f"🎬 {BTN_SEARCH} 🍿", switch_inline_query_current_chat="")
        ],
        [
            InlineKeyboardButton(BTN_HISTORY, callback_data="user_history"),
            InlineKeyboardButton(BTN_STATUS, callback_data="user_status")
        ],
        [
            InlineKeyboardButton(BTN_SETTINGS, callback_data="settings_back"),
            InlineKeyboardButton(BTN_ABOUT, callback_data="user_about")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


# =============================================================================
# /START COMMAND
# =============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command

    - Sends welcome image (if enabled)
    - Shows welcome message with buttons
    - Adds user to database
    - Prompts owner login if needed
    """
    user = update.effective_user
    user_id = user.id

    log_user(f"User {user_id} ({user.first_name}) started bot")

    # Add user to database
    db.add_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    # Clear previous session
    clear_session(user_id)

    # Check if owner needs login
    if is_owner(user_id) and not is_owner_logged_in(user_id):
        set_session(user_id, {"state": "awaiting_login"})
        login_attempts[user_id] = 0

        await update.message.reply_text(
            MSG_OWNER_LOGIN,
            parse_mode="Markdown"
        )
        return

    # Check if returning user
    db_user = db.get_user(user_id)
    is_returning = db_user and db_user.searches > 0

    if is_returning:
        welcome_text = MSG_WELCOME_BACK.format(name=user.first_name)
    else:
        welcome_text = MSG_WELCOME.format(name=user.first_name)


    # Send welcome with image or text
    if WELCOME_IMAGE_ENABLED and WELCOME_IMAGE_URL:
        try:
            await update.message.reply_photo(
                photo=WELCOME_IMAGE_URL,
                caption=welcome_text,
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            log_warning(f"Welcome image failed: {e}")

    # Fallback to text only
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown"
    )


# =============================================================================
# OWNER LOGIN HANDLER
# =============================================================================

async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handle owner password login

    Returns:
        True if login successful, False otherwise
    """
    user_id = update.effective_user.id
    password = update.message.text.strip()

    # Delete password message for security
    try:
        await update.message.delete()
    except:
        pass

    if password == ADMIN_PASSWORD:
        owner_login_status[user_id] = True
        clear_session(user_id)
        login_attempts.pop(user_id, None)

        log_success(f"Owner {user_id} logged in successfully")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=MSG_LOGIN_SUCCESS,
            parse_mode="Markdown"
        )

        # Send welcome after login
        welcome_text = MSG_WELCOME.format(name=update.effective_user.first_name)

        if WELCOME_IMAGE_ENABLED and WELCOME_IMAGE_URL:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=WELCOME_IMAGE_URL,
                    caption=welcome_text,
                    parse_mode="Markdown"
                )
                return True
            except:
                pass

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_text,
            parse_mode="Markdown"
        )

        return True

    else:
        attempts = login_attempts.get(user_id, 0) + 1
        login_attempts[user_id] = attempts

        if attempts >= MAX_LOGIN_ATTEMPTS:
            owner_login_status[user_id] = False
            clear_session(user_id)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=MSG_LOGIN_BLOCKED,
                parse_mode="Markdown"
            )

            log_warning(f"Owner {user_id} blocked after {attempts} failed attempts")
            return False

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=MSG_LOGIN_FAILED.format(
                attempt=attempts,
                max_attempts=MAX_LOGIN_ATTEMPTS
            ),
            parse_mode="Markdown"
        )

        return False


# =============================================================================
# SEARCH HANDLER
# =============================================================================

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle movie/series search

    - Validates query
    - Searches BollyFlix
    - Applies user settings (filters, count)
    - Shows results with numbers
    """
    user_id = update.effective_user.id
    query = update.message.text.strip()

    # Check if banned
    if db.is_banned(user_id):
        await update.message.reply_text(MSG_ERROR_BANNED)
        return

    # Validate query length
    if len(query) < 2:
        await update.message.reply_text(MSG_TOO_SHORT)
        return

    # Log search
    db.increment_searches(user_id)
    log_info(f"User {user_id} searching: {query}")

    # Send searching message
    msg = await update.message.reply_text(
        MSG_SEARCHING.format(query=query),
        parse_mode="Markdown"
    )

    # Perform search
    results = search_bollyflix(query)

    if not results:
        await msg.edit_text(
            MSG_NO_RESULTS.format(query=query),
            parse_mode="Markdown"
        )
        return

    # Apply user settings (language filter, content type, results count)
    results = apply_settings_to_results(user_id, results)

    if not results:
        await msg.edit_text(
            MSG_NO_RESULTS.format(query=query),
            parse_mode="Markdown"
        )
        return

    # Get user's preferred results count
    max_results = min(len(results), get_user_results_count(user_id))

    # Store results in session
    set_session(user_id, {
        "state": "select_content",
        "results": results[:max_results],
        "query": query
    })

    # Log to database
    db.log_search(user_id, query, len(results))

    # Build results text
    results_text = ""

    for i, result in enumerate(results[:max_results], 1):
        title = result['clean_title'][:45]
        year = result.get('year', '')
        content_type = result.get('content_type', 'movie')

        type_tag = "📺" if content_type == "series" else "🎬"

        if year and year != "N/A":
            results_text += f"{type_tag} **{i}.** {title} ({year})\n\n"
        else:
            results_text += f"{type_tag} **{i}.** {title}\n\n"

    text = MSG_SEARCH_RESULTS.format(
        query=query,
        count=len(results),
        results=results_text.strip(),
        max=max_results
    )

    await msg.edit_text(text, parse_mode="Markdown")


# =============================================================================
# NUMBER SELECTION HANDLER
# =============================================================================

async def number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle number selection from search results

    - Validates selection
    - Loads content details
    - Shows confirmation
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text.isdigit():
        return

    num = int(text)
    session = get_session(user_id)

    if "results" not in session:
        await update.message.reply_text(
            "No active search. Type a movie or series name to search 👇"
        )
        return

    results = session["results"]

    if num < 1 or num > len(results):
        await update.message.reply_text(
            f"Invalid. Type a number between **1** and **{len(results)}**",
            parse_mode="Markdown"
        )
        return

    selected = results[num - 1]

    log_info(f"User {user_id} selected: {selected['clean_title']}")

    await show_content_info(
        update, context,
        url=selected['url'],
        poster=selected.get('poster', '')
    )


# =============================================================================
# CONTENT INFO DISPLAY
# =============================================================================

async def show_content_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    url: str,
    poster: str = "",
    is_callback: bool = False
):
    """
    Display movie/series info with poster

    - Scrapes content details
    - Shows info card with poster
    - Adds confirmation buttons
    """
    if is_callback:
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat_id
    else:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

    # Send loading message
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=MSG_LOADING,
        parse_mode="Markdown"
    )

    # Scrape content
    content = scrape_content(url, poster)

    if not content:
        await msg.edit_text(
            "Couldn't load this content. Please try again.",
            parse_mode="Markdown"
        )
        return

    # Store in session
    set_session(user_id, {
        "state": "confirm_download",
        "content": content
    })

    # Build info text
    if content["is_series"]:
        caption = build_series_info(content)
    else:
        caption = build_movie_info(content)

    # Build keyboard
    keyboard = [
        [InlineKeyboardButton(BTN_CONFIRM_YES, callback_data="confirm_yes")],
        [InlineKeyboardButton(BTN_CANCEL, callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Delete loading message
    try:
        await msg.delete()
    except:
        pass

    # Send with poster or text only
    content_poster = content.get('poster') or poster

    if content_poster:
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=content_poster,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            log_warning(f"Poster failed: {e}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


def build_movie_info(content: Dict) -> str:
    """Build movie info caption"""
    stars = generate_stars(content.get('rating', '7.5'))
    qualities = " · ".join(content.get('qualities', ['720p']))

    return MSG_MOVIE_INFO.format(
        title=content['clean_title'],
        year=content.get('year', 'N/A'),
        genre=content.get('genre', 'N/A'),
        duration=content.get('duration', 'N/A'),
        rating=content.get('rating', '7.5'),
        stars=stars,
        qualities=qualities
    )


def build_series_info(content: Dict) -> str:
    """Build series info caption"""
    seasons = content.get('seasons', {})
    seasons_list = get_seasons_list(seasons)
    season_count = len(seasons_list)

    if season_count <= 5:
        seasons_display = ", ".join(seasons_list)
    else:
        seasons_display = f"{seasons_list[0]} to {seasons_list[-1]}"

    all_qualities = set()
    for season_data in seasons.values():
        all_qualities.update(season_data.keys())
    qualities = " · ".join(sort_qualities(list(all_qualities)))

    return MSG_SERIES_INFO.format(
        title=content['clean_title'],
        year=content.get('year', 'N/A'),
        genre=content.get('genre', 'N/A'),
        rating=content.get('rating', '7.5'),
        season_count=season_count,
        seasons=seasons_display,
        qualities=qualities or "720p"
    )


# =============================================================================
# DOWNLOAD PROCESSING
# =============================================================================

async def process_movie_download(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    quality: str
):
    """
    Process movie download with bypass
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]

    # Get download URL
    download_url = content.get("download_links", {}).get(quality, "")
    if not download_url:
        download_url = content.get("url", "")

    # Log download
    db.increment_downloads(user_id)
    db.log_download(user_id, content["clean_title"], quality, "movie")

    log_info(f"User {user_id} downloading: {content['clean_title']} ({quality})")

    # Delete old message
    try:
        await query.message.delete()
    except:
        pass

    # Send progress
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=MSG_FETCHING.format(
            title=content['clean_title'],
            quality=quality
        ),
        parse_mode="Markdown"
    )

    # Run bypass
    final_url = download_url
    bypass_success = False

    if is_bypass_available():
        try:
            await msg.edit_text(
                MSG_BYPASSING.format(
                    title=content['clean_title'],
                    quality=quality
                ),
                parse_mode="Markdown"
            )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, full_bypass, download_url)

            if result and result.get("success"):
                best = (
                    result.get("best_url") or
                    result.get("telegram_link") or
                    result.get("gdflix_url") or
                    result.get("fastdl_url")
                )
                if best:
                    final_url = best
                    bypass_success = True
                    log_success(f"Bypass done: {final_url[:50]}...")

        except Exception as e:
            log_error(f"Bypass error: {e}")

    # Update progress
    await msg.edit_text(
        MSG_GENERATING.format(
            title=content['clean_title'],
            quality=quality
        ),
        parse_mode="Markdown"
    )

    # Extract Telegram link from FastDL/GDFlix page
    tg_link = None
    try:
        if 'fxlinks' in download_url.lower():
            fastdl_extracted, tg_link = await asyncio.get_event_loop().run_in_executor(
                None, extract_tg_from_fxlinks, download_url
            )
            if fastdl_extracted and not bypass_success:
                final_url = fastdl_extracted
        elif 'fastdl' in final_url.lower() or 'gdflix' in final_url.lower():
            tg_link = await asyncio.get_event_loop().run_in_executor(
                None, extract_tg_from_fastdl, final_url
            )
    except Exception as e:
        log_warning(f"TG link extraction: {e}")


    try:
        await msg.delete()
    except:
        pass

    # Validate URL
    if not final_url or not final_url.startswith("http"):
        final_url = download_url if download_url.startswith("http") else content.get("url", "")

    # Build final message
    stars = generate_stars(content.get('rating', '7.5'))

    final_caption = MSG_MOVIE_READY.format(
        title=content['clean_title'],
        year=content.get('year', 'N/A'),
        genre=content.get('genre', 'N/A'),
        duration=content.get('duration', 'N/A'),
        rating=content.get('rating', '7.5'),
        stars=stars,
        quality=quality
    )

    # Build dual buttons (FastDL + Telegram) — HIDDEN LINKS
    keyboard = []

    # Store real URLs in session (hidden from user)
    session = get_session(user_id)
    session["dl_fastdl"] = final_url
    session["dl_telegram"] = tg_link
    session["dl_title"] = content['clean_title']
    session["dl_quality"] = quality
    set_session(user_id, session)

    # Callback buttons (no URL visible to user)
    keyboard.append([InlineKeyboardButton("📥 Download", callback_data="dl_fastdl")])
    if tg_link:
        keyboard.append([InlineKeyboardButton("📥 Get via Telegram", callback_data="dl_telegram")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send final
    poster = content.get('poster', '')

    if poster:
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=poster,
                caption=final_caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            log_success(f"Movie done: {content['clean_title']} ({quality})")
            return
        except:
            pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=final_caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    log_success(f"Movie done: {content['clean_title']} ({quality})")


async def process_series_download(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    quality: str
):
    """
    Process series download with bypass
    """
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    session = get_session(user_id)

    if "content" not in session:
        await query.answer(MSG_ERROR_SESSION_EXPIRED, show_alert=True)
        return

    content = session["content"]
    season = session.get("selected_season", "S01")

    # Get download URL
    season_data = content.get("seasons", {}).get(season, {})
    download_url = season_data.get(quality, "")
    if not download_url:
        download_url = content.get("url", "")

    # Log download
    db.increment_downloads(user_id)
    db.log_download(
        user_id,
        f"{content['clean_title']} {season}",
        quality, "series", season
    )

    log_info(f"User {user_id} downloading: {content['clean_title']} {season} ({quality})")

    # Delete old message
    try:
        await query.message.delete()
    except:
        pass

    # Progress
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=MSG_FETCHING.format(
            title=f"{content['clean_title']} — {season}",
            quality=quality
        ),
        parse_mode="Markdown"
    )

    # Run bypass
    final_url = download_url
    bypass_success = False

    if is_bypass_available():
        try:
            await msg.edit_text(
                MSG_BYPASSING.format(
                    title=f"{content['clean_title']} — {season}",
                    quality=quality
                ),
                parse_mode="Markdown"
            )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, full_bypass, download_url)

            if result and result.get("success"):
                best = (
                    result.get("best_url") or
                    result.get("telegram_link") or
                    result.get("gdflix_url")
                )
                if best:
                    final_url = best
                    bypass_success = True

        except Exception as e:
            log_error(f"Bypass error: {e}")

    await msg.edit_text(
        MSG_GENERATING.format(
            title=f"{content['clean_title']} — {season}",
            quality=quality
        ),
        parse_mode="Markdown"
    )

    # Extract Telegram link from FastDL/GDFlix page
    tg_link = None
    try:
        if 'fxlinks' in download_url.lower():
            fastdl_extracted, tg_link = await asyncio.get_event_loop().run_in_executor(
                None, extract_tg_from_fxlinks, download_url
            )
            if fastdl_extracted and not bypass_success:
                final_url = fastdl_extracted
        elif 'fastdl' in final_url.lower() or 'gdflix' in final_url.lower():
            tg_link = await asyncio.get_event_loop().run_in_executor(
                None, extract_tg_from_fastdl, final_url
            )
    except Exception as e:
        log_warning(f"TG link extraction: {e}")

    await asyncio.sleep(1)

    try:
        await msg.delete()
    except:
        pass

    # Validate URL
    if not final_url or not final_url.startswith("http"):
        final_url = download_url if download_url.startswith("http") else content.get("url", "")

    # Build final message
    final_caption = MSG_SERIES_READY.format(
        title=content['clean_title'],
        season=season,
        year=content.get('year', 'N/A'),
        genre=content.get('genre', 'N/A'),
        rating=content.get('rating', '7.5'),
        quality=quality
    )

    # Build dual buttons (FastDL + Telegram) — HIDDEN LINKS
    keyboard = []

    # Store real URLs in session (hidden from user)
    session = get_session(user_id)
    session["dl_fastdl"] = final_url
    session["dl_telegram"] = tg_link
    session["dl_title"] = f"{content['clean_title']} {season}"
    session["dl_quality"] = quality
    set_session(user_id, session)

    # Callback buttons (no URL visible to user)
    keyboard.append([InlineKeyboardButton("📥 Download", callback_data="dl_fastdl")])
    if tg_link:
        keyboard.append([InlineKeyboardButton("📥 Get via Telegram", callback_data="dl_telegram")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    poster = content.get('poster', '')

    if poster:
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=poster,
                caption=final_caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            log_success(f"Series done: {content['clean_title']} {season} ({quality})")
            return
        except:
            pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=final_caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    log_success(f"Series done: {content['clean_title']} {season} ({quality})")


# =============================================================================
# MAIN TEXT HANDLER (Router)
# =============================================================================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main text message router
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Check owner login state
    if is_owner(user_id):
        session = get_session(user_id)
        if session.get("state") == "awaiting_login":
            await handle_login(update, context)
            return

    # Check if banned
    if db.is_banned(user_id):
        await update.message.reply_text(MSG_ERROR_BANNED)
        return

    # Route based on content
    if text.isdigit():
        await number_handler(update, context)
    else:
        await search_handler(update, context)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'start_command',
    'text_handler',
    'search_handler',
    'number_handler',
    'handle_login',
    'show_content_info',
    'process_movie_download',
    'process_series_download',
    'get_session',
    'set_session',
    'clear_session',
    'user_sessions',
    'owner_login_status',
]