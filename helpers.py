"""
=============================================================================
BOLLYFLIX BOT - HELPER UTILITIES
=============================================================================
General utility functions for formatting, cleaning, extraction, and more
=============================================================================
"""

import os
import re
import hashlib
from typing import Optional, List, Tuple, Union
from datetime import datetime, timedelta

from config import CHROME_PATHS, QUALITY_ORDER


# =============================================================================
# SIZE FORMATTING
# =============================================================================

def format_size(size_bytes: Union[int, float]) -> str:
    """
    Convert bytes to human readable format
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string like "1.5 GB"
    
    Examples:
        format_size(1024) -> "1.0 KB"
        format_size(1048576) -> "1.0 MB"
        format_size(1073741824) -> "1.0 GB"
    """
    if not size_bytes or size_bytes < 0:
        return "0 B"
    
    size_bytes = float(size_bytes)
    
    # Define units
    units = [
        (1024 ** 4, "TB"),
        (1024 ** 3, "GB"),
        (1024 ** 2, "MB"),
        (1024, "KB"),
        (1, "B")
    ]
    
    for factor, unit in units:
        if size_bytes >= factor:
            value = size_bytes / factor
            if unit in ("TB", "GB"):
                return f"{value:.2f} {unit}"
            elif unit == "MB":
                return f"{value:.1f} {unit}"
            else:
                return f"{int(value)} {unit}"
    
    return "0 B"


def parse_size(size_str: str) -> int:
    """
    Parse human readable size to bytes
    
    Args:
        size_str: String like "1.5 GB" or "500 MB"
    
    Returns:
        Size in bytes
    """
    if not size_str:
        return 0
    
    size_str = size_str.upper().strip()
    
    # Pattern: number + optional space + unit
    match = re.match(r'([\d.]+)\s*([KMGT]?B)', size_str)
    if not match:
        return 0
    
    value = float(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4
    }
    
    return int(value * multipliers.get(unit, 1))


# =============================================================================
# CHROME PATH DETECTION
# =============================================================================

def get_chrome_path() -> Optional[str]:
    """
    Find Chrome/Chromium binary path
    
    Returns:
        Path to chrome executable or None
    """
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    
    # Try which command on Linux/Mac
    try:
        import shutil
        for browser in ["google-chrome", "chromium", "chromium-browser", "chrome"]:
            path = shutil.which(browser)
            if path:
                return path
    except:
        pass
    
    return None


def is_chrome_available() -> bool:
    """Check if Chrome/Chromium is available"""
    return get_chrome_path() is not None


# =============================================================================
# STAR RATING GENERATOR
# =============================================================================

def generate_stars(rating: Union[str, float, int], max_stars: int = 10) -> str:
    """
    Generate star rating display
    
    Args:
        rating: Rating value (0-10)
        max_stars: Maximum stars to show
    
    Returns:
        Star string like "⭐⭐⭐⭐⭐⭐⭐✨"
    
    Examples:
        generate_stars(7.5) -> "⭐⭐⭐⭐⭐⭐⭐✨"
        generate_stars("8.0") -> "⭐⭐⭐⭐⭐⭐⭐⭐"
        generate_stars(5) -> "⭐⭐⭐⭐⭐"
    """
    try:
        # Parse rating
        if isinstance(rating, str):
            rating = rating.replace('/10', '').replace('/5', '').strip()
            rating = float(rating)
        
        # Clamp to valid range
        rating = max(0, min(max_stars, float(rating)))
        
        # Calculate stars
        full_stars = int(rating)
        has_half = (rating - full_stars) >= 0.5
        
        # Build star string
        stars = '⭐' * full_stars
        if has_half and full_stars < max_stars:
            stars += '✨'
        
        return stars if stars else '⭐'
        
    except (ValueError, TypeError):
        return '⭐⭐⭐⭐⭐⭐⭐'  # Default 7 stars


def rating_to_emoji(rating: Union[str, float]) -> str:
    """
    Convert rating to single emoji indicator
    
    Args:
        rating: Rating value (0-10)
    
    Returns:
        Single emoji based on rating
    """
    try:
        if isinstance(rating, str):
            rating = float(rating.replace('/10', '').strip())
        
        if rating >= 8.5:
            return "🔥"  # Excellent
        elif rating >= 7.5:
            return "⭐"  # Great
        elif rating >= 6.5:
            return "👍"  # Good
        elif rating >= 5.5:
            return "😐"  # Average
        else:
            return "👎"  # Poor
            
    except:
        return "⭐"


# =============================================================================
# TITLE CLEANING
# =============================================================================

def clean_title(title: str) -> str:
    """
    Clean movie/series title - Keep only Name + Year
    Remove all junk like quality, codec, source info
    
    Args:
        title: Raw title from website
    
    Returns:
        Cleaned title
    
    Examples:
        clean_title("Avengers Endgame 2019 1080p WEB-DL x264") -> "Avengers Endgame 2019"
        clean_title("Money Heist S01 720p NF WEB-DL Dual Audio") -> "Money Heist"
    """
    if not title:
        return "Unknown"
    
    original = title
    
    # Patterns to remove (order matters!)
    remove_patterns = [
        # Download/Free keywords
        r'(?:Free\s+)?Download\s*',
        r'Direct\s+Download\s*',
        
        # Audio info
        r'Dual\s*Audio[^|]*',
        r'Hindi\s*(?:Dubbed|DD|Audio)[^|]*',
        r'Hindi\s*[\-\+]\s*English[^|]*',
        r'Multi\s*Audio[^|]*',
        r'ORG\s*Hindi[^|]*',
        
        # Source tags
        r'WEB[\-\s]?(?:DL|Rip|HDRip)[^|]*',
        r'Blu[\-\s]?Ray[^|]*',
        r'BRRip[^|]*',
        r'HDRip[^|]*',
        r'DVDRip[^|]*',
        r'DVDScr[^|]*',
        r'HDTC[^|]*',
        r'HDCAM[^|]*',
        r'CAMRip[^|]*',
        r'PreDVD[^|]*',
        
        # Codec info
        r'[xX]\.?264[^|]*',
        r'[xX]\.?265[^|]*',
        r'HEVC[^|]*',
        r'10\s*bit[^|]*',
        r'HDR\d*[^|]*',
        
        # Audio codec
        r'AAC[^|]*',
        r'DD[P\+]?\s*\d+\.\d+[^|]*',
        r'Atmos[^|]*',
        r'DTS[^|]*',
        
        # Subtitles
        r'ESub[s]?[^|]*',
        r'MSub[s]?[^|]*',
        r'Eng\s*Sub[s]?[^|]*',
        
        # Streaming platforms
        r'(?:AMZN|Amazon|NF|Netflix|DSNP|Disney\+?|Hotstar|ZEE5|SonyLIV|Voot|MX\s*Player|JioCinema)[^|]*',
        
        # Quality tags (will keep year)
        r'\d{3,4}p\s*(?:HD|Full\s*HD|UHD|HDR)?[^|]*',
        
        # Movie/Series tags
        r'(?:Hindi|English|Telugu|Tamil|Malayalam|Kannada|South|Bollywood|Hollywood)\s*Movie[^|]*',
        r'(?:Web|TV)\s*Series[^|]*',
        
        # Brackets content
        r'\{[^}]*\}',
        r'\[[^\]]*\]',
        
        # Extra tags
        r'UnRated[^|]*',
        r'Extended[^|]*',
        r'Director[\'s]*\s*Cut[^|]*',
        r'Remastered[^|]*',
        r'PROPER[^|]*',
        r'REPACK[^|]*',
    ]
    
    cleaned = title
    for pattern in remove_patterns:
        cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
    
    # Clean up
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Multiple spaces
    cleaned = re.sub(r'[\|\-\–\—\:\;]+\s*$', '', cleaned)  # Trailing separators
    cleaned = re.sub(r'^\s*[\|\-\–\—\:\;]+', '', cleaned)  # Leading separators
    cleaned = re.sub(r'\(\s*\)', '', cleaned)  # Empty brackets
    cleaned = cleaned.strip()
    
    # If we removed everything, return original
    if len(cleaned) < 2:
        # Try to extract just the name
        match = re.match(r'^([A-Za-z0-9\s\:]+)', original)
        if match:
            return match.group(1).strip()
        return original.strip()
    
    return cleaned


def extract_title_and_year(title: str) -> Tuple[str, Optional[str]]:
    """
    Extract clean title and year separately
    
    Args:
        title: Raw title
    
    Returns:
        Tuple of (clean_title, year or None)
    """
    clean = clean_title(title)
    
    # Try to find year
    year_match = re.search(r'\((\d{4})\)|\b(19\d{2}|20\d{2})\b', clean)
    year = None
    
    if year_match:
        year = year_match.group(1) or year_match.group(2)
        # Remove year from title
        clean = re.sub(r'\s*\(?\d{4}\)?\s*$', '', clean).strip()
    
    return clean, year


# =============================================================================
# METADATA EXTRACTION
# =============================================================================

def extract_year(title: str, page_content: str = "") -> str:
    """
    Extract year from title or page content
    
    Args:
        title: Movie/series title
        page_content: Optional page text content
    
    Returns:
        Year string or "N/A"
    """
    # Check title first - bracketed year
    year_match = re.search(r'\((\d{4})\)', title)
    if year_match:
        year = year_match.group(1)
        if 1900 <= int(year) <= 2030:
            return year
    
    # Plain year in title
    year_match = re.search(r'\b(20\d{2}|19\d{2})\b', title)
    if year_match:
        return year_match.group(1)
    
    # Check page content
    if page_content:
        patterns = [
            r'(?:Release|Year|Released)[:\s]*(\d{4})',
            r'(\d{4})\s*(?:Release|Film|Movie)',
            r'Year[:\s]+(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, page_content, re.IGNORECASE)
            if match:
                year = match.group(1)
                if 1900 <= int(year) <= 2030:
                    return year
    
    return "N/A"


def extract_rating(page_content: str, soup=None) -> str:
    """
    Extract IMDB rating from page content
    
    Args:
        page_content: Page text content
        soup: Optional BeautifulSoup object
    
    Returns:
        Rating string or "7.5"
    """
    # Try BeautifulSoup first
    if soup:
        # Look for rating span
        rating_span = soup.find("span", id="imdb_rating")
        if rating_span:
            rating = rating_span.get_text().strip()
            if rating:
                return rating
        
        # Meta tag
        meta_rating = soup.find("meta", {"itemprop": "ratingValue"})
        if meta_rating:
            rating = meta_rating.get("content", "")
            if rating:
                return rating
    
    # Search in content
    patterns = [
        r'IMDB[:\s]*Rating[:\s]*([\d.]+)',
        r'Rating[:\s]*([\d.]+)\s*/\s*10',
        r'([\d.]+)\s*/\s*10\s*(?:IMDB|IMDb)',
        r'IMDB[:\s]*([\d.]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, page_content, re.IGNORECASE)
        if match:
            rating = match.group(1)
            try:
                if 0 <= float(rating) <= 10:
                    return rating
            except:
                pass
    
    return "7.5"


def extract_genre(page_content: str) -> str:
    """
    Extract genre from page content
    
    Args:
        page_content: Page text content
    
    Returns:
        Genre string or "N/A"
    """
    patterns = [
        r'Genre[s]?[:\s]*([A-Za-z,\s\-&]+?)(?:\n|Movie|Quality|Director|Release)',
        r'Genre[s]?[:\s]*([A-Za-z,\s\-&]+?)(?:\|)',
        r'Category[:\s]*([A-Za-z,\s\-&]+?)(?:\n)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, page_content, re.IGNORECASE)
        if match:
            genre = match.group(1).strip()
            genre = re.sub(r'\s+', ' ', genre)
            
            # Split and clean
            genres = [
                g.strip().title() 
                for g in genre.split(',') 
                if g.strip() and len(g.strip()) > 2
            ]
            
            if genres:
                return ', '.join(genres[:3])  # Max 3 genres
    
    return "N/A"


def extract_duration(page_content: str) -> str:
    """
    Extract duration/runtime from page content
    
    Args:
        page_content: Page text content
    
    Returns:
        Duration string or "N/A"
    """
    patterns = [
        r'(?:Runtime|Duration|Time)[:\s]*(\d+\s*(?:hr?|hour)?\s*\d*\s*(?:min)?)',
        r'(\d{1,2}h\s*\d{1,2}m)',
        r'(\d+)\s*(?:min|minutes)',
        r'Duration[:\s]*(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, page_content, re.IGNORECASE)
        if match:
            duration = match.group(1).strip()
            if duration:
                # Format nicely
                if duration.isdigit():
                    mins = int(duration)
                    if mins > 60:
                        hours = mins // 60
                        mins = mins % 60
                        return f"{hours}h {mins}m"
                    return f"{mins} min"
                return duration
    
    return "N/A"


# =============================================================================
# QUALITY HANDLING
# =============================================================================

def sort_qualities(qualities: List[str]) -> List[str]:
    """
    Sort qualities in order: 480p → 720p → 1080p → 2160p
    
    Args:
        qualities: List of quality strings
    
    Returns:
        Sorted list
    """
    def get_priority(quality: str) -> int:
        q_lower = quality.lower().strip()
        
        for i, standard_quality in enumerate(QUALITY_ORDER):
            if standard_quality.lower() in q_lower or q_lower in standard_quality.lower():
                return i
        
        # Extract number for unknown qualities
        match = re.search(r'(\d+)p', q_lower)
        if match:
            return int(match.group(1))
        
        return 999
    
    return sorted(qualities, key=get_priority)


def normalize_quality(quality: str) -> str:
    """
    Normalize quality string to standard format
    
    Args:
        quality: Raw quality string
    
    Returns:
        Normalized quality like "1080p"
    """
    q_lower = quality.lower().strip()
    
    # Check standard qualities
    quality_map = {
        "480": "480p",
        "720": "720p",
        "1080": "1080p",
        "2160": "2160p",
        "4k": "2160p",
        "uhd": "2160p",
        "hd": "720p",
        "full hd": "1080p",
        "fhd": "1080p",
    }
    
    for key, value in quality_map.items():
        if key in q_lower:
            # Check for 10bit
            if "10" in q_lower and "bit" in q_lower:
                return f"{value.replace('p', '')}p 10bit"
            # Check for HQ
            if "hq" in q_lower:
                return f"{value} HQ"
            return value
    
    return quality


def get_quality_emoji(quality: str) -> str:
    """
    Get emoji for quality
    
    Args:
        quality: Quality string
    
    Returns:
        Emoji string
    """
    q_lower = quality.lower()
    
    if "2160" in q_lower or "4k" in q_lower:
        return "📺"
    elif "1080" in q_lower:
        return "🖥️"
    elif "720" in q_lower:
        return "💻"
    elif "480" in q_lower:
        return "📱"
    else:
        return "📥"


# =============================================================================
# URL & HASH UTILITIES
# =============================================================================

def generate_cache_key(url: str) -> str:
    """
    Generate short cache key from URL
    
    Args:
        url: Full URL
    
    Returns:
        16-character hash key
    """
    return hashlib.md5(url.encode()).hexdigest()[:16]


def is_valid_url(url: str) -> bool:
    """
    Check if string is a valid URL
    
    Args:
        url: String to check
    
    Returns:
        True if valid URL
    """
    if not url or not isinstance(url, str):
        return False
    
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(pattern.match(url))


def extract_domain(url: str) -> str:
    """
    Extract domain from URL
    
    Args:
        url: Full URL
    
    Returns:
        Domain name
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ""


def is_download_link(url: str, domains: List[str] = None) -> bool:
    """
    Check if URL is a download link
    
    Args:
        url: URL to check
        domains: List of download domains
    
    Returns:
        True if download link
    """
    if not url:
        return False
    
    if domains is None:
        from config import DOWNLOAD_DOMAINS
        domains = DOWNLOAD_DOMAINS
    
    url_lower = url.lower()
    return any(domain in url_lower for domain in domains)


# =============================================================================
# TIME & DATE UTILITIES
# =============================================================================

def format_datetime(dt: datetime, format_type: str = "short") -> str:
    """
    Format datetime to string
    
    Args:
        dt: Datetime object
        format_type: "short", "long", "date", "time"
    
    Returns:
        Formatted string
    """
    if not dt:
        return "N/A"
    
    formats = {
        "short": "%d %b %Y",
        "long": "%d %B %Y, %H:%M",
        "date": "%Y-%m-%d",
        "time": "%H:%M:%S",
        "full": "%Y-%m-%d %H:%M:%S"
    }
    
    return dt.strftime(formats.get(format_type, formats["short"]))


def parse_datetime(dt_string: str) -> Optional[datetime]:
    """
    Parse datetime from ISO format string
    
    Args:
        dt_string: ISO format datetime string
    
    Returns:
        Datetime object or None
    """
    try:
        return datetime.fromisoformat(dt_string)
    except:
        return None


def time_ago(dt: datetime) -> str:
    """
    Get human readable time ago string
    
    Args:
        dt: Datetime object
    
    Returns:
        String like "2 hours ago"
    """
    if not dt:
        return "N/A"
    
    diff = datetime.now() - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} minute{'s' if mins > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return format_datetime(dt, "short")


# =============================================================================
# TEXT UTILITIES
# =============================================================================

def truncate(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to max length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def escape_markdown(text: str) -> str:
    """
    Escape Markdown special characters
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text
    """
    if not text:
        return ""
    
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename - remove invalid characters
    
    Args:
        filename: Original filename
    
    Returns:
        Safe filename
    """
    if not filename:
        return "file"
    
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    return filename.strip('_') or "file"


# =============================================================================
# TELEGRAM LINK EXTRACTION
# =============================================================================

def extract_tg_from_fastdl(fastdl_url: str, timeout: int = 10) -> Optional[str]:
    """
    Extract Telegram bot link from FastDL/GDFlix page
    
    Converts filesgram.site/?start=X&bot=Y → t.me/Y?start=X
    
    Args:
        fastdl_url: FastDL or GDFlix URL (e.g., fastdlserver.life/?id=xxx)
        timeout: Request timeout in seconds
    
    Returns:
        Telegram bot link (t.me/...) or None
    """
    if not fastdl_url or not fastdl_url.startswith("http"):
        return None
    
    try:
        import requests as req
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
        
        response = req.get(fastdl_url, headers=headers, timeout=timeout, allow_redirects=True)
        
        if response.status_code != 200:
            return None
        
        html = response.text
        
        # Method 1: Find filesgram.site link (handles &amp; HTML encoding)
        filesgram_pattern = re.compile(
            r'https?://filesgram\.site/?\?start=([^\s"\'&]+)(?:&amp;|&)bot=([^\s"\'&]+)',
            re.IGNORECASE
        )
        match = filesgram_pattern.search(html)
        if match:
            start_param = match.group(1)
            bot_name = match.group(2)
            return f"https://t.me/{bot_name}?start={start_param}"
        
        # Method 2: Direct t.me link with start parameter
        tme_pattern = re.compile(
            r'https?://t\.me/([^/?"\'\s]+)\?start=([^&"\'\s]+)',
            re.IGNORECASE
        )
        match = tme_pattern.search(html)
        if match:
            return match.group(0)
        
        return None
        
    except Exception:
        return None


def extract_tg_from_fxlinks(fxlinks_url: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract FastDL URL and Telegram link from fxlinks page
    
    Chain: fxlinks.rest → fastdlserver.life → filesgram → t.me
    
    Args:
        fxlinks_url: FXLinks URL (e.g., fxlinks.rest/elinks/xxx/)
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (fastdl_url, telegram_link) - either can be None
    """
    if not fxlinks_url or not fxlinks_url.startswith("http"):
        return None, None
    
    try:
        import requests as req
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
        
        response = req.get(fxlinks_url, headers=headers, timeout=timeout, allow_redirects=True)
        
        if response.status_code != 200:
            return None, None
        
        html = response.text
        
        # Extract first fastdlserver.life link (Season Zip or first episode)
        fastdl_pattern = re.compile(
            r'https?://fastdlserver\.life/?\?id=[^"\'\s]+',
            re.IGNORECASE
        )
        fastdl_match = fastdl_pattern.search(html)
        fastdl_url = fastdl_match.group(0) if fastdl_match else None
        
        # Now get TG link from fastdl page
        tg_link = None
        if fastdl_url:
            tg_link = extract_tg_from_fastdl(fastdl_url, timeout)
        
        return fastdl_url, tg_link
        
    except Exception:
        return None, None


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("HELPERS DEMO")
    print("=" * 50)
    
    # Size formatting
    print("\n📦 Size Formatting:")
    print(f"  1024 bytes = {format_size(1024)}")
    print(f"  1.5 GB = {format_size(1.5 * 1024**3)}")
    
    # Title cleaning
    print("\n🎬 Title Cleaning:")
    raw = "Avengers Endgame 2019 1080p WEB-DL x264 Dual Audio Hindi-English"
    print(f"  Raw: {raw}")
    print(f"  Clean: {clean_title(raw)}")
    
    # Star rating
    print("\n⭐ Star Rating:")
    print(f"  7.5 = {generate_stars(7.5)}")
    print(f"  9.0 = {generate_stars(9.0)}")
    
    # Quality sorting
    print("\n📊 Quality Sorting:")
    qualities = ["1080p", "480p", "2160p", "720p"]
    print(f"  Before: {qualities}")
    print(f"  After: {sort_qualities(qualities)}")
    
    # Chrome path
    print(f"\n🌐 Chrome Path: {get_chrome_path() or 'Not found'}")
    
    print("\n✅ Helpers demo complete!")