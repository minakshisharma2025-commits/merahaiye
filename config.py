"""
=============================================================================
BOLLYFLIX BOT - CONFIGURATION
=============================================================================
"""

import os
import re
from typing import List, Dict


# =============================================================================
# BOT CONFIGURATION
# =============================================================================

BOT_TOKEN = ""

if not BOT_TOKEN:
    BOT_TOKEN = "5942749621:AAFASNWBqOt27ORCbOJ4RNDuPj3lki0c0jA"

BOT_NAME = "BollyFlix Bot"
BOT_USERNAME = os.environ.get("BOT_USERNAME", "BollyFlixBot")
BOT_VERSION = "3.0"
MAX_LOGIN_ATTEMPTS = 3


# =============================================================================
# OWNER CONFIGURATION
# =============================================================================

_owner_ids_str = os.environ.get("OWNER_IDS", "")
if _owner_ids_str:
    OWNER_IDS: List[int] = [int(x.strip()) for x in _owner_ids_str.split(",") if x.strip()]
else:
    OWNER_IDS: List[int] = [1651746145]

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ajjubhai")


# =============================================================================
# PYROGRAM CONFIGURATION
# =============================================================================

API_ID = os.environ.get("API_ID", "")
API_HASH = os.environ.get("API_HASH", "")
SESSION_NAME = "bollyflix_userbot"


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

DATABASE_FILE = os.environ.get("DATABASE_FILE", "bollyflix_data.json")
DATABASE_CHANNEL_ID = os.environ.get("DATABASE_CHANNEL_ID", "me")
MAX_CACHE_AGE_HOURS = 24
MAX_SEARCH_LOG = 1000
MAX_DOWNLOAD_LOG = 1000



# DAILY DOWNLOAD LIMITS
# =============================================================================

FREE_DAILY_LIMIT = 40
PREMIUM_DAILY_LIMIT = 30


# =============================================================================
# SEARCH CONFIGURATION
# =============================================================================

BOLLYFLIX_BASE_URL = "https://bollyflix.sarl"
MAX_SEARCH_RESULTS = 20
REQUEST_TIMEOUT = 20


# =============================================================================
# BYPASS CONFIGURATION
# =============================================================================

BYPASS_TIMEOUT = 30
BOT_RESPONSE_TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 2


# =============================================================================
# WELCOME IMAGE
# =============================================================================

# Set your welcome banner image URL here
# Recommended: 800x400px, JPG/PNG
# You can use Telegraph, Imgur, or any direct image URL
WELCOME_IMAGE_URL = os.environ.get(
    "WELCOME_IMAGE_URL",
    "https://i.ibb.co/placeholder/bollyflix-banner.jpg"
)


# Set to True to send image with /start, False for text only
WELCOME_IMAGE_ENABLED = True


# =============================================================================
# DEFAULT SETTINGS
# =============================================================================

DEFAULT_SETTINGS = {
    "default_quality": "auto",
    "language": "all",
    "content_type": "all",
    "results_count": "10",
    "auto_bypass": "on",
}

SETTINGS_MESSAGES = {
    "main": "⚙️ **Settings**\n\nCustomize your experience.",
    "saved": "✅ Setting saved!",
    "reset": "🔄 All settings reset to defaults.",
    "invalid": "❌ Invalid option.",
}


# =============================================================================
# CHROME PATHS
# =============================================================================

CHROME_PATHS: List[str] = [
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/usr/bin/google-chrome-stable",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


# =============================================================================
# HTTP HEADERS
# =============================================================================

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://bollyflix.sarl/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


# =============================================================================
# QUALITY SETTINGS
# =============================================================================

QUALITY_ORDER: List[str] = [
    "480p",
    "720p",
    "720p 10bit",
    "1080p",
    "1080p 10bit",
    "1080p HQ",
    "2160p",
    "4K"
]

QUALITY_ICONS: Dict[str, str] = {
    "480p": "📱",
    "720p": "💻",
    "720p 10bit": "💻",
    "1080p": "🖥️",
    "1080p 10bit": "🖥️",
    "1080p HQ": "🖥️",
    "2160p": "📺",
    "4K": "📺",
}


# =============================================================================
# DOWNLOAD DOMAINS
# =============================================================================

DOWNLOAD_DOMAINS: List[str] = [
    "fxlinks", "fastdlserver",
    "ozolinks", "ouo.io", "ouo.press",
    "gdflix", "gdrive", "gdtot",
    "hubcloud", "hubdrive",
    "filepress", "filebee",
    "links4u", "link4u",
    "shrinkme", "shorte",
    "droplink", "dropgalaxy",
    "indishare", "linkvertise",
    "fastdl", "fastlinks",
]


# =============================================================================
# BOT MESSAGES - WELCOME
# =============================================================================

MSG_WELCOME = """🎬 **Welcome to {bot_name}** 🍿
━━━━━━━⍟━━━━━━━

Hey **{name}**! 👋
I'm your ultra-fast ⚡ and powerful assistant for downloading Movies & Web Series.

**✨ Key Features:**
🔍 _Deep Search Engine_
🎥 _Multiple Qualities (480p - 2160p 4K)_
📥 _Direct Telegram File Delivery_
⚡ _Bypass Annoying Ads/Links_

**🎯 How to use:**
Simply type the name of any Movie or Series in the chat, and I'll fetch the best links for you instantly!

👇 _**Type any Movie or Series name to search and download!**_""".replace("{bot_name}", BOT_NAME)

MSG_WELCOME_BACK = """🎬 **Welcome Back to {bot_name}!** 🍿
━━━━━━━⍟━━━━━━━

Hey **{name}**! 👋 Great to see you again.

Your popcorn is ready! 🍿 Just tell me what you want to watch today.

👇 _**Type a movie or series name to search!**_""".replace("{bot_name}", BOT_NAME)


# =============================================================================
# BOT MESSAGES - AUTH
# =============================================================================

MSG_OWNER_LOGIN = """🔐 **Authentication Required**

Enter your admin password to continue:"""

MSG_LOGIN_SUCCESS = """✅ **Authenticated**

Welcome back, boss. Full access granted.

**Admin commands:**
/admin — Control panel
/stats — Statistics
/users — User list
/ban — Ban user
/unban — Unban user
/broadcast — Message all users"""

MSG_LOGIN_FAILED = """❌ **Wrong password**

Attempt {attempt} of {max_attempts}. Try again:"""

MSG_LOGIN_BLOCKED = """🚫 **Locked out**

Too many failed attempts. Use /start to try again later."""


# =============================================================================
# BOT MESSAGES - SEARCH
# =============================================================================

MSG_SEARCHING = """🔍 Searching for "**{query}**" ..."""

MSG_NO_RESULTS = """No results found for "**{query}**"

**Try:**
• Check your spelling
• Use the full name
• Add the year — e.g. "Avengers 2019"

Type another name to search 👇"""

MSG_SEARCH_RESULTS = """**Search Results** for "{query}"

{results}

**Type a number** (1-{max}) to select 👇"""

MSG_TOO_SHORT = """Too short — type at least **2 characters** to search."""

MSG_INVALID_NUMBER = """Invalid input. Type a number between **1** and **{max}**."""


# =============================================================================
# BOT MESSAGES - CONTENT INFO
# =============================================================================

MSG_LOADING = """Loading details ⏳"""

MSG_MOVIE_INFO = """🎬 **{title}**

Year: {year}
Genre: {genre}
Duration: {duration}
Rating: {rating}/10 {stars}
Quality: {qualities}

Tap below to continue 👇"""

MSG_SERIES_INFO = """📺 **{title}**

Year: {year}
Genre: {genre}
Rating: {rating}/10
Seasons: {season_count}
Available: {seasons}
Quality: {qualities}

Tap below to continue 👇"""

MSG_SELECT_QUALITY = """**{title}**

Select your preferred quality 👇"""

MSG_SELECT_SEASON = """**{title}**

Select a season to download 👇"""

MSG_SELECT_SEASON_QUALITY = """**{title}** — {season}

Select quality for this season 👇"""


# =============================================================================
# BOT MESSAGES - DOWNLOAD
# =============================================================================

MSG_FETCHING = """Fetching link ⏳

{title}
Quality: {quality}"""

MSG_BYPASSING = """Bypassing protection ⚡

{title}
Quality: {quality}

This takes about 3-5 seconds..."""

MSG_GENERATING = """Almost there ⏳

Generating your download link..."""

MSG_MOVIE_READY = """✅ **Download Ready**

🎬 **{title}**

Year: {year}
Genre: {genre}
Duration: {duration}
Rating: {rating}/10 {stars}
Quality: {quality}

⚠️ Link expires in 24 hours

Type another name to search 👇"""

MSG_SERIES_READY = """✅ **Download Ready**

📺 **{title}**

Season: {season}
Year: {year}
Genre: {genre}
Rating: {rating}/10
Quality: {quality}

⚠️ Link expires in 24 hours

Type another name to search 👇"""


# =============================================================================
# BOT MESSAGES - ERRORS
# =============================================================================

MSG_ERROR_GENERIC = """Something went wrong. Please try again."""

MSG_ERROR_SESSION_EXPIRED = """Session expired. Please search again."""

MSG_ERROR_BYPASS_FAILED = """Bypass failed. Try again or use the direct link."""

MSG_ERROR_CONTENT_LOAD = """Couldn't load the content. Please try again."""

MSG_ERROR_NO_SEASONS = """No seasons found for this title."""

MSG_ERROR_NO_QUALITIES = """No download links found for this season."""

MSG_ERROR_BANNED = """🚫 You've been banned from using this bot."""

MSG_ERROR_NOT_AUTHORIZED = """You're not authorized to do this."""


# =============================================================================
# BOT MESSAGES - HELP
# =============================================================================

MSG_HELP = """**How to use {bot_name}**

**Searching:**
Just type any movie or series name. That's it.

**Downloading:**
1. Type a name → pick a result
2. Choose quality (480p to 4K)
3. Tap download → get the link

**For series:**
Pick a season first, then choose quality.

**Commands:**
/start — Restart the bot
/help — This message
/settings — Your preferences
/status — Your stats
/history — Download history

**Tips:**
• Add year for better results: "Inception 2010"
• Be specific with spelling
• Try alternate names if no results

Need help? Contact the admin.""".replace("{bot_name}", BOT_NAME)


# =============================================================================
# BOT MESSAGES - USER
# =============================================================================

MSG_USER_STATUS = """**Your Profile**

ID: `{user_id}`
Name: {name}
Joined: {joined}

Searches: {searches}
Downloads: {downloads}

Status: {status}"""

MSG_USER_HISTORY = """**Download History** — {name}

{history}

Total downloads: {total}"""

MSG_NO_HISTORY = """**Download History**

Nothing here yet. Start by searching for a movie or series 👇"""


# =============================================================================
# BOT MESSAGES - ADMIN
# =============================================================================

MSG_ADMIN_PANEL = """**Admin Panel**

Owner: {name}
ID: `{user_id}`

**Users**
Total: {total_users}
Active (24h): {active_users}

**Activity**
Searches: {total_searches}
Downloads: {total_downloads}

**Cache**
Entries: {cache_count}

**Commands:**
/stats — Full statistics
/users — User list
/broadcast — Message all users
/ban `<id>` — Ban user
/unban `<id>` — Unban user"""

MSG_CANCELLED = """Cancelled. Type a movie or series name to search 👇"""


# =============================================================================
# BUTTON TEXTS
# =============================================================================

BTN_CONFIRM_YES = "✅ Yes, Download"
BTN_CANCEL = "❌ Cancel"
BTN_BACK_SEASONS = "🔙 Back to Seasons"
BTN_DOWNLOAD = "📥 Download"
BTN_TELEGRAM_FILE = "📥 Get via Telegram"
BTN_GET_LINK = "📥 Get Link"
BTN_SEARCH = "🔍 Search"
BTN_SETTINGS = "⚙️ Settings"
BTN_HELP = "📖 Help"
BTN_HISTORY = "📜 History"
BTN_STATUS = "📊 Status"
BTN_ABOUT = "ℹ️ About"


# =============================================================================
# REGEX PATTERNS
# =============================================================================

PATTERN_YEAR_BRACKET = re.compile(r'\((\d{4})\)')
PATTERN_YEAR_PLAIN = re.compile(r'\b(20\d{2}|19\d{2})\b')

PATTERN_SEASON = re.compile(r'[Ss](\d{1,2})|[Ss]eason\s*(\d{1,2})', re.IGNORECASE)
PATTERN_EPISODE = re.compile(r'[Ee](\d{1,3})|[Ee]pisode\s*(\d{1,3})', re.IGNORECASE)

PATTERN_480P = re.compile(r'480p', re.IGNORECASE)
PATTERN_720P = re.compile(r'720p(?!\s*\(?10)', re.IGNORECASE)
PATTERN_720P_10BIT = re.compile(r'720p\s*\(?10\s*bit\)?', re.IGNORECASE)
PATTERN_1080P = re.compile(r'1080p(?!\s*\(?10)(?!\s*hq)', re.IGNORECASE)
PATTERN_1080P_10BIT = re.compile(r'1080p\s*\(?10\s*bit\)?', re.IGNORECASE)
PATTERN_1080P_HQ = re.compile(r'1080p\s*hq', re.IGNORECASE)
PATTERN_2160P = re.compile(r'2160p|4k|uhd', re.IGNORECASE)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_owner(user_id: int) -> bool:
    """Check if user is an owner"""
    return user_id in OWNER_IDS


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in OWNER_IDS