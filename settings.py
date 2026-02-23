"""
=============================================================================
BOLLYFLIX BOT - USER SETTINGS SYSTEM
=============================================================================
Complete settings management:
- Default Quality preference
- Language Filter
- Content Type preference
- Results per search
- Auto Bypass toggle
- Per-user persistent storage
- Reset to defaults
=============================================================================
"""

from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import (
    OWNER_IDS,
    QUALITY_ORDER,
    DEFAULT_SETTINGS,
    SETTINGS_MESSAGES
)
from logger import log_info, log_user, log_warning
from database import db


# =============================================================================
# SETTINGS DEFINITIONS
# =============================================================================

class SettingsKeys:
    """All settings keys as constants"""
    DEFAULT_QUALITY = "default_quality"
    LANGUAGE = "language"
    CONTENT_TYPE = "content_type"
    RESULTS_COUNT = "results_count"
    AUTO_BYPASS = "auto_bypass"


# Available options for each setting
SETTINGS_OPTIONS = {
    SettingsKeys.DEFAULT_QUALITY: {
        "key": SettingsKeys.DEFAULT_QUALITY,
        "label": "🎬 Default Quality",
        "description": "Preferred quality will be shown first",
        "options": [
            {"value": "auto", "label": "Auto (Show All)", "emoji": "🔄"},
            {"value": "480p", "label": "480p", "emoji": "📱"},
            {"value": "720p", "label": "720p", "emoji": "💻"},
            {"value": "1080p", "label": "1080p", "emoji": "🖥️"},
            {"value": "2160p", "label": "4K / 2160p", "emoji": "📺"},
        ]
    },

    SettingsKeys.LANGUAGE: {
        "key": SettingsKeys.LANGUAGE,
        "label": "🌐 Language Filter",
        "description": "Filter results by language",
        "options": [
            {"value": "all", "label": "All Languages", "emoji": "🌍"},
            {"value": "hindi", "label": "Hindi", "emoji": "🇮🇳"},
            {"value": "english", "label": "English", "emoji": "🇺🇸"},
            {"value": "dubbed", "label": "Hindi Dubbed", "emoji": "🎙️"},
            {"value": "south", "label": "South Indian", "emoji": "🎭"},
        ]
    },

    SettingsKeys.CONTENT_TYPE: {
        "key": SettingsKeys.CONTENT_TYPE,
        "label": "📺 Content Preference",
        "description": "What type of content you watch",
        "options": [
            {"value": "all", "label": "Movies + Series", "emoji": "🎯"},
            {"value": "movie", "label": "Movies Only", "emoji": "🎬"},
            {"value": "series", "label": "Series Only", "emoji": "📺"},
        ]
    },

    SettingsKeys.RESULTS_COUNT: {
        "key": SettingsKeys.RESULTS_COUNT,
        "label": "🔢 Results Per Search",
        "description": "How many results to show",
        "options": [
            {"value": "5", "label": "5 Results", "emoji": "5️⃣"},
            {"value": "10", "label": "10 Results", "emoji": "🔟"},
            {"value": "15", "label": "15 Results", "emoji": "1️⃣"},
        ]
    },

    SettingsKeys.AUTO_BYPASS: {
        "key": SettingsKeys.AUTO_BYPASS,
        "label": "⚡ Auto Bypass",
        "description": "Automatically bypass link protection",
        "options": [
            {"value": "on", "label": "On — Auto bypass links", "emoji": "✅"},
            {"value": "off", "label": "Off — Show raw link", "emoji": "❌"},
        ]
    },
}

# Order in which settings appear
SETTINGS_DISPLAY_ORDER = [
    SettingsKeys.DEFAULT_QUALITY,
    SettingsKeys.LANGUAGE,
    SettingsKeys.CONTENT_TYPE,
    SettingsKeys.RESULTS_COUNT,
    SettingsKeys.AUTO_BYPASS,
]


# =============================================================================
# SETTINGS MANAGER
# =============================================================================

class SettingsManager:
    """
    Manages per-user settings with database persistence

    Usage:
        manager = SettingsManager()
        quality = manager.get(user_id, "default_quality")
        manager.set(user_id, "default_quality", "1080p")
    """

    def __init__(self):
        self._cache: Dict[int, Dict[str, Any]] = {}

    def get_all(self, user_id: int) -> Dict[str, Any]:
        """
        Get all settings for a user

        Returns merged dict of defaults + user overrides
        """
        # Check cache first
        if user_id in self._cache:
            return self._cache[user_id].copy()

        # Load from database
        saved = db.get_user_settings(user_id)

        # Merge with defaults
        settings = DEFAULT_SETTINGS.copy()
        if saved:
            settings.update(saved)

        # Cache it
        self._cache[user_id] = settings

        return settings.copy()

    def get(self, user_id: int, key: str, default: Any = None) -> Any:
        """
        Get single setting value

        Args:
            user_id: Telegram user ID
            key: Setting key from SettingsKeys
            default: Fallback value

        Returns:
            Setting value
        """
        settings = self.get_all(user_id)
        return settings.get(key, default or DEFAULT_SETTINGS.get(key))

    def set(self, user_id: int, key: str, value: Any) -> bool:
        """
        Set single setting value

        Args:
            user_id: Telegram user ID
            key: Setting key
            value: New value

        Returns:
            True if saved successfully
        """
        # Validate key
        if key not in SETTINGS_OPTIONS:
            log_warning(f"Invalid setting key: {key}")
            return False

        # Validate value
        valid_values = [opt["value"] for opt in SETTINGS_OPTIONS[key]["options"]]
        if value not in valid_values:
            log_warning(f"Invalid value '{value}' for setting '{key}'")
            return False

        # Update cache
        if user_id not in self._cache:
            self.get_all(user_id)

        self._cache[user_id][key] = value

        # Save to database
        db.save_user_settings(user_id, self._cache[user_id])

        log_info(f"User {user_id} changed {key} = {value}")
        return True

    def reset(self, user_id: int) -> bool:
        """
        Reset all settings to defaults

        Args:
            user_id: Telegram user ID

        Returns:
            True if reset successfully
        """
        self._cache[user_id] = DEFAULT_SETTINGS.copy()
        db.save_user_settings(user_id, DEFAULT_SETTINGS.copy())

        log_info(f"User {user_id} reset all settings")
        return True

    def get_display_value(self, key: str, value: Any) -> str:
        """
        Get human readable display value

        Args:
            key: Setting key
            value: Current value

        Returns:
            Display string like "✅ 1080p"
        """
        if key not in SETTINGS_OPTIONS:
            return str(value)

        for option in SETTINGS_OPTIONS[key]["options"]:
            if option["value"] == str(value):
                return f"{option['emoji']} {option['label']}"

        return str(value)

    def clear_cache(self, user_id: int = None):
        """Clear settings cache"""
        if user_id:
            self._cache.pop(user_id, None)
        else:
            self._cache.clear()


# Global instance
settings_manager = SettingsManager()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_user_quality(user_id: int) -> str:
    """Quick helper to get user's preferred quality"""
    return settings_manager.get(user_id, SettingsKeys.DEFAULT_QUALITY, "auto")


def get_user_language(user_id: int) -> str:
    """Quick helper to get user's language preference"""
    return settings_manager.get(user_id, SettingsKeys.LANGUAGE, "all")


def get_user_content_type(user_id: int) -> str:
    """Quick helper to get user's content type preference"""
    return settings_manager.get(user_id, SettingsKeys.CONTENT_TYPE, "all")


def get_user_results_count(user_id: int) -> int:
    """Quick helper to get user's results count preference"""
    count = settings_manager.get(user_id, SettingsKeys.RESULTS_COUNT, "10")
    return int(count)


def get_user_auto_bypass(user_id: int) -> bool:
    """Quick helper to check if auto bypass is on"""
    return settings_manager.get(user_id, SettingsKeys.AUTO_BYPASS, "on") == "on"


# =============================================================================
# KEYBOARD BUILDERS
# =============================================================================

def build_settings_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """
    Build main settings menu keyboard

    Shows all settings with current values
    """
    settings = settings_manager.get_all(user_id)
    buttons = []

    for key in SETTINGS_DISPLAY_ORDER:
        option_info = SETTINGS_OPTIONS[key]
        current_value = settings.get(key, DEFAULT_SETTINGS.get(key))
        display = settings_manager.get_display_value(key, current_value)

        buttons.append([
            InlineKeyboardButton(
                f"{option_info['label']}  →  {display}",
                callback_data=f"settings_edit_{key}"
            )
        ])

    # Reset and close buttons
    buttons.append([
        InlineKeyboardButton("🔄 Reset All", callback_data="settings_reset"),
        InlineKeyboardButton("✖ Close", callback_data="settings_close")
    ])

    return InlineKeyboardMarkup(buttons)


def build_setting_options_keyboard(
    key: str,
    current_value: Any
) -> InlineKeyboardMarkup:
    """
    Build keyboard for individual setting options

    Shows all options with checkmark on current selection
    """
    if key not in SETTINGS_OPTIONS:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="settings_back")
        ]])

    option_info = SETTINGS_OPTIONS[key]
    buttons = []

    for option in option_info["options"]:
        # Mark current selection
        if option["value"] == str(current_value):
            label = f"● {option['emoji']} {option['label']}"
        else:
            label = f"○ {option['emoji']} {option['label']}"

        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"settings_set_{key}_{option['value']}"
            )
        ])

    # Back button
    buttons.append([
        InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back")
    ])

    return InlineKeyboardMarkup(buttons)


def build_reset_confirm_keyboard() -> InlineKeyboardMarkup:
    """Build confirmation keyboard for reset"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Reset", callback_data="settings_reset_confirm"),
            InlineKeyboardButton("❌ No, Cancel", callback_data="settings_back")
        ]
    ])


# =============================================================================
# MESSAGE BUILDERS
# =============================================================================

def build_settings_main_message(user_id: int) -> str:
    """Build the main settings message"""
    settings = settings_manager.get_all(user_id)

    lines = ["⚙️ **Settings**\n"]
    lines.append("Customize your experience. Tap any option to change.\n")

    for key in SETTINGS_DISPLAY_ORDER:
        option_info = SETTINGS_OPTIONS[key]
        current_value = settings.get(key, DEFAULT_SETTINGS.get(key))
        display = settings_manager.get_display_value(key, current_value)

        lines.append(f"**{option_info['label']}**")
        lines.append(f"  Current: {display}\n")

    return "\n".join(lines)


def build_setting_edit_message(key: str, user_id: int) -> str:
    """Build message for editing a specific setting"""
    if key not in SETTINGS_OPTIONS:
        return "❌ Unknown setting."

    option_info = SETTINGS_OPTIONS[key]
    current_value = settings_manager.get(user_id, key)
    display = settings_manager.get_display_value(key, current_value)

    lines = [
        f"⚙️ **{option_info['label']}**\n",
        f"{option_info['description']}\n",
        f"Current: **{display}**\n",
        "Select an option below:"
    ]

    return "\n".join(lines)


# =============================================================================
# COMMAND HANDLER
# =============================================================================

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /settings command

    Shows main settings menu with current values
    """
    user = update.effective_user
    user_id = user.id

    log_user(f"User {user_id} opened settings")

    message = build_settings_main_message(user_id)
    keyboard = build_settings_main_keyboard(user_id)

    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# =============================================================================
# CALLBACK HANDLER
# =============================================================================

async def settings_callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Handle all settings-related callbacks

    Callback data formats:
        settings_edit_{key}           — Open setting editor
        settings_set_{key}_{value}    — Set a value
        settings_back                 — Back to main settings
        settings_reset                — Show reset confirmation
        settings_reset_confirm        — Confirm reset
        settings_close                — Close settings menu

    Returns:
        True if callback was handled, False otherwise
    """
    query = update.callback_query
    data = query.data

    if not data.startswith("settings_"):
        return False

    await query.answer()

    user = query.from_user
    user_id = user.id

    # -----------------------------------------------------------------
    # EDIT — Open specific setting
    # -----------------------------------------------------------------
    if data.startswith("settings_edit_"):
        key = data.replace("settings_edit_", "")

        if key not in SETTINGS_OPTIONS:
            await query.answer("❌ Invalid setting", show_alert=True)
            return True

        message = build_setting_edit_message(key, user_id)
        current_value = settings_manager.get(user_id, key)
        keyboard = build_setting_options_keyboard(key, current_value)

        try:
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception:
            pass

        return True

    # -----------------------------------------------------------------
    # SET — Change a setting value
    # -----------------------------------------------------------------
    if data.startswith("settings_set_"):
        # Parse: settings_set_{key}_{value}
        parts = data.replace("settings_set_", "").split("_", 1)

        if len(parts) != 2:
            await query.answer("❌ Invalid option", show_alert=True)
            return True

        key, value = parts

        if key not in SETTINGS_OPTIONS:
            await query.answer("❌ Invalid setting", show_alert=True)
            return True

        # Check if same value
        current = settings_manager.get(user_id, key)
        if str(current) == value:
            await query.answer("Already selected!", show_alert=False)
            return True

        # Save new value
        success = settings_manager.set(user_id, key, value)

        if success:
            display = settings_manager.get_display_value(key, value)
            await query.answer(f"✅ Changed to {display}", show_alert=False)

            # Refresh the edit view
            message = build_setting_edit_message(key, user_id)
            keyboard = build_setting_options_keyboard(key, value)

            try:
                await query.edit_message_text(
                    message,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        else:
            await query.answer("❌ Failed to save", show_alert=True)

        return True

    # -----------------------------------------------------------------
    # BACK — Return to main settings
    # -----------------------------------------------------------------
    if data == "settings_back":
        message = build_settings_main_message(user_id)
        keyboard = build_settings_main_keyboard(user_id)

        try:
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception:
            pass

        return True

    # -----------------------------------------------------------------
    # RESET — Show confirmation
    # -----------------------------------------------------------------
    if data == "settings_reset":
        message = (
            "🔄 **Reset Settings**\n\n"
            "This will reset all your settings to defaults.\n\n"
            "Are you sure?"
        )
        keyboard = build_reset_confirm_keyboard()

        try:
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception:
            pass

        return True

    # -----------------------------------------------------------------
    # RESET CONFIRM — Actually reset
    # -----------------------------------------------------------------
    if data == "settings_reset_confirm":
        settings_manager.reset(user_id)

        await query.answer("✅ Settings reset to defaults!", show_alert=True)

        # Show updated settings
        message = build_settings_main_message(user_id)
        keyboard = build_settings_main_keyboard(user_id)

        try:
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception:
            pass

        return True

    # -----------------------------------------------------------------
    # CLOSE — Delete settings message
    # -----------------------------------------------------------------
    if data == "settings_close":
        try:
            await query.delete_message()
        except Exception:
            try:
                await query.edit_message_text("✅ Settings closed.")
            except Exception:
                pass

        return True

    return False


# =============================================================================
# APPLY SETTINGS TO SEARCH
# =============================================================================

def apply_settings_to_results(
    user_id: int,
    results: List[Dict]
) -> List[Dict]:
    """
    Apply user settings to search results

    Filters and reorders based on user preferences:
    - Language filter
    - Content type filter
    - Results count limit

    Args:
        user_id: Telegram user ID
        results: Raw search results

    Returns:
        Filtered and trimmed results
    """
    if not results:
        return results

    settings = settings_manager.get_all(user_id)
    filtered = results.copy()

    # Apply language filter
    lang_pref = settings.get(SettingsKeys.LANGUAGE, "all")

    if lang_pref != "all":
        lang_filtered = []
        for item in filtered:
            title_lower = (item.get("title", "") or "").lower()

            if lang_pref == "hindi" and any(w in title_lower for w in ["hindi", "हिंदी"]):
                lang_filtered.append(item)
            elif lang_pref == "english" and any(w in title_lower for w in ["english", "eng"]):
                lang_filtered.append(item)
            elif lang_pref == "dubbed" and any(w in title_lower for w in ["dubbed", "dual audio", "hindi dubbed"]):
                lang_filtered.append(item)
            elif lang_pref == "south" and any(w in title_lower for w in ["tamil", "telugu", "malayalam", "kannada", "south"]):
                lang_filtered.append(item)
            elif lang_pref == "all":
                lang_filtered.append(item)

        # Only apply filter if we still have results
        if lang_filtered:
            filtered = lang_filtered

    # Apply content type filter
    content_pref = settings.get(SettingsKeys.CONTENT_TYPE, "all")

    if content_pref != "all":
        type_filtered = []
        for item in filtered:
            item_type = item.get("content_type", "movie")
            if content_pref == "movie" and item_type == "movie":
                type_filtered.append(item)
            elif content_pref == "series" and item_type in ("series", "anime"):
                type_filtered.append(item)

        if type_filtered:
            filtered = type_filtered

    # Apply results count limit
    count = int(settings.get(SettingsKeys.RESULTS_COUNT, "10"))
    filtered = filtered[:count]

    return filtered


def apply_quality_preference(
    user_id: int,
    qualities: List[str]
) -> List[str]:
    """
    Reorder qualities based on user preference

    Moves preferred quality to top of list

    Args:
        user_id: Telegram user ID
        qualities: Available qualities

    Returns:
        Reordered qualities list
    """
    if not qualities:
        return qualities

    preferred = get_user_quality(user_id)

    if preferred == "auto" or preferred not in qualities:
        return qualities

    # Move preferred to front
    reordered = [preferred]
    for q in qualities:
        if q != preferred:
            reordered.append(q)

    return reordered


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Manager
    'settings_manager',
    'SettingsManager',
    'SettingsKeys',
    'SETTINGS_OPTIONS',

    # Quick helpers
    'get_user_quality',
    'get_user_language',
    'get_user_content_type',
    'get_user_results_count',
    'get_user_auto_bypass',

    # Handlers
    'settings_command',
    'settings_callback_handler',

    # Apply to results
    'apply_settings_to_results',
    'apply_quality_preference',

    # Keyboard builders
    'build_settings_main_keyboard',
    'build_setting_options_keyboard',
]