"""
=============================================================================
BOLLYFLIX BOT - CONTENT TYPE DETECTION
=============================================================================
Smart detection system for Movies vs Series/Web Series/Anime
Uses multiple patterns and scoring for accurate detection
=============================================================================
"""

import re
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from logger import log_debug


# =============================================================================
# CONTENT TYPES
# =============================================================================

class ContentType(Enum):
    """Content type enumeration"""
    MOVIE = "movie"
    SERIES = "series"
    ANIME = "anime"
    DOCUMENTARY = "documentary"
    UNKNOWN = "unknown"
    
    def __str__(self):
        return self.value


# =============================================================================
# DETECTION RESULT
# =============================================================================

@dataclass
class DetectionResult:
    """Result of content type detection"""
    content_type: ContentType
    confidence: float  # 0.0 to 1.0
    reasons: List[str]
    season_count: int = 0
    detected_seasons: List[str] = None
    
    def __post_init__(self):
        if self.detected_seasons is None:
            self.detected_seasons = []
    
    @property
    def is_series(self) -> bool:
        return self.content_type in (ContentType.SERIES, ContentType.ANIME)
    
    @property
    def is_movie(self) -> bool:
        return self.content_type == ContentType.MOVIE


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

class DetectionPatterns:
    """All patterns used for detection"""
    
    # =========================================================================
    # SERIES INDICATORS (High confidence)
    # =========================================================================
    
    SERIES_EXACT_PHRASES = [
        'web series', 'webseries', 'web-series',
        'tv series', 'tvseries', 'tv-series',
        'tv show', 'tvshow', 'tv-show',
        'mini series', 'miniseries', 'mini-series',
        'limited series',
        'complete series', 'complete season',
        'complete all season', 'all seasons', 'all season',
        'full series', 'full season',
        'season pack', 'seasons pack',
    ]
    
    ANIME_PHRASES = [
        'anime series', 'anime',
        'animated series',
        'japanese anime',
        'dubbed anime',
    ]
    
    # Multi-season patterns (very high confidence)
    MULTI_SEASON_PATTERNS = [
        r's0?1\s*[&\-–to]+\s*s0?[2-9]',           # S01-S05
        r's0?1\s*,\s*s0?2',                        # S01, S02
        r'season\s*1\s*[&\-–to]+\s*season\s*[2-9]', # Season 1 - Season 5
        r'season\s*1\s*,\s*season\s*2',            # Season 1, Season 2
        r'\bs0?1\b.*\bs0?2\b.*\bs0?3\b',           # S01...S02...S03
        r'\bseason\s*1\b.*\bseason\s*2\b',         # Season 1...Season 2
        r'seasons?\s*\d+\s*[-–&]\s*\d+',           # Seasons 1-5
    ]
    
    # Episode patterns (high confidence)
    EPISODE_PATTERNS = [
        r'all\s*episodes?',
        r'complete\s*episodes?',
        r'\d+\s*episodes?',
        r'episode\s*\d+\s*[-–to]+\s*\d+',         # Episode 1-10
        r'ep\s*\d+\s*[-–to]+\s*ep\s*\d+',         # Ep 1 - Ep 10
        r's\d+\s*e\d+',                            # S01E01
        r'e0?1\s*[-–]\s*e\d+',                     # E01-E10
        r'\d+\s*eps?\.?',                          # 10 eps
    ]
    
    # Season mention pattern
    SEASON_PATTERN = re.compile(
        r'(?:\bs0?(\d{1,2})\b|\bseason\s*(\d{1,2})\b)',
        re.IGNORECASE
    )
    
    # =========================================================================
    # MOVIE INDICATORS
    # =========================================================================
    
    MOVIE_PHRASES = [
        'full movie', 'movie download',
        'hindi movie', 'english movie',
        'bollywood movie', 'hollywood movie',
        'south movie', 'south indian movie',
        'telugu movie', 'tamil movie',
        'malayalam movie', 'kannada movie',
        'punjabi movie', 'marathi movie',
        'bhojpuri movie', 'gujarati movie',
        'korean movie', 'chinese movie',
        'japanese movie', 'thai movie',
        'dual audio movie', 'dubbed movie',
        'hd movie', 'new movie',
        '(movie)', '[movie]',
        'theatrical', 'theatrical release',
    ]
    
    MOVIE_YEAR_PATTERN = re.compile(
        r'^[A-Za-z0-9\s\:\'\"\-]+\s*\(?(19|20)\d{2}\)?$'
    )
    
    # =========================================================================
    # DOCUMENTARY INDICATORS
    # =========================================================================
    
    DOCUMENTARY_PHRASES = [
        'documentary', 'docuseries', 'docu-series',
        'true story', 'based on true',
        'national geographic', 'nat geo',
        'discovery channel', 'bbc documentary',
        'history channel',
    ]


# =============================================================================
# MAIN DETECTOR CLASS
# =============================================================================

class ContentDetector:
    """
    Smart content type detector
    
    Uses multiple signals:
    - Exact phrase matching
    - Pattern matching (seasons, episodes)
    - Scoring system for confidence
    
    Usage:
        detector = ContentDetector()
        result = detector.detect("Money Heist S01-S05 Complete", page_content)
        
        if result.is_series:
            print(f"Series with {result.season_count} seasons")
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.patterns = DetectionPatterns()
    
    def detect(self, title: str, page_content: str = "") -> DetectionResult:
        """
        Detect content type from title and page content.
        MOVIE-FIRST logic: when in doubt, return movie.
        Series classification requires a STRONG, explicit signal.
        """
        if not title:
            return DetectionResult(
                content_type=ContentType.UNKNOWN,
                confidence=0.0,
                reasons=["No title provided"]
            )

        title_lower = title.lower().strip()
        full_text = f"{title} {page_content}".lower()

        reasons = []
        detected_seasons = []
        series_score = 0.0
        movie_score = 0.0

        # =====================================================================
        # RULE 0: HARD MOVIE OVERRIDE
        # If the word "movie" is explicitly present in the title, it IS a movie.
        # Nothing overrides this — prevents "Avengers Movie S01" false-series.
        # =====================================================================
        MOVIE_KEYWORDS = [
            r'\bmovie\b', r'\bfilm\b', r'\bcinema\b',
            r'\btheatrical\b', r'\bdvdrip\b', r'\bbluray\b',
            r'\bhdcam\b', r'\bwebrip\b', r'\bbdrip\b',
        ]
        for kw in MOVIE_KEYWORDS:
            if re.search(kw, title_lower):
                movie_score += 4.0
                reasons.append(f"Hard movie keyword: '{kw}'")
                break  # One is enough for strong signal

        # =====================================================================
        # RULE 1: STRONG SERIES SIGNALS (explicit, unambiguous)
        # =====================================================================

        # 1a. Explicit series phrases (e.g. "web series", "tv show", "all seasons")
        for phrase in self.patterns.SERIES_EXACT_PHRASES:
            if phrase in full_text:
                series_score += 3.5
                reasons.append(f"Series phrase: '{phrase}'")

        # 1b. Anime / animated series phrases
        for phrase in self.patterns.ANIME_PHRASES:
            if phrase in full_text:
                series_score += 3.0
                reasons.append(f"Anime indicator: '{phrase}'")

        # 1c. Multi-season patterns — strongest possible signal
        for pattern in self.patterns.MULTI_SEASON_PATTERNS:
            if re.search(pattern, full_text, re.IGNORECASE):
                series_score += 6.0
                reasons.append("Multi-season range detected")
                break

        # 1d. Strong episode patterns (ranges, counts like "12 Episodes", S01E01)
        STRONG_EP_PATTERNS = [
            (r'all\s*episodes?', 3.5),
            (r'complete\s*episodes?', 3.5),
            (r'\d{2,}\s*episodes?', 3.0),        # "12 episodes" (2+ digits)
            (r'episode\s*\d+\s*[-–to]+\s*\d+', 3.0),  # Episode 1-10
            (r'ep\s*\d+\s*[-–to]+\s*ep\s*\d+', 3.0),  # Ep 1 - Ep 10
            (r'e0?1\s*[-–]\s*e\d+', 3.0),              # E01-E10
            (r's\d+\s*e\d+', 4.0),                      # S01E01 — UNAMBIGUOUS series
            (r'\bs\d{1,2}\b', 3.5),                     # bare S01, S02 — series notation
        ]
        for pattern, pts in STRONG_EP_PATTERNS:
            if re.search(pattern, full_text, re.IGNORECASE):
                series_score += pts
                reasons.append("Strong episode pattern found")
                break

        # =====================================================================
        # RULE 2: SEASON COUNTING (careful — movies can say "Chapter 2" etc.)
        # Only gives series points for MULTIPLE distinct seasons.
        # A lone "Season 1" or "S01" by itself is NOT enough.
        # =====================================================================
        season_matches = self.patterns.SEASON_PATTERN.findall(full_text)
        unique_seasons = set()

        for match in season_matches:
            season_num = match[0] or match[1]
            if season_num:
                unique_seasons.add(int(season_num))
                detected_seasons.append(f"S{int(season_num):02d}")

        detected_seasons = sorted(list(set(detected_seasons)))
        season_count = len(unique_seasons)

        if season_count >= 3:
            series_score += 5.0
            reasons.append(f"3+ distinct seasons: {season_count}")
        elif season_count == 2:
            series_score += 3.5
            reasons.append(f"2 distinct seasons found")
        elif season_count == 1:
            # Season 2, 3, 4+ are NEVER movie titles — strong series signal
            # Season 1 alone is ambiguous (could be a movie/pilot)
            max_season = max(unique_seasons) if unique_seasons else 0
            if movie_score > 0:
                reasons.append("Single season ignored (movie keyword overrides)")
            elif max_season >= 2:
                # 'Season 2' or higher — no movie is ever called 'Season 2'
                series_score += 3.5
                reasons.append(f"Season {max_season} — strong series indicator")
            else:
                # Season 1 alone is weak
                series_score += 1.0
                reasons.append("Season 1 alone (weak hint)")

        # =====================================================================
        # RULE 3: MOVIE INDICATORS (additional weight)
        # =====================================================================
        for phrase in self.patterns.MOVIE_PHRASES:
            if phrase in full_text:
                movie_score += 3.5
                reasons.append(f"Movie indicator: '{phrase}'")

        if self.patterns.MOVIE_YEAR_PATTERN.match(title.strip()):
            movie_score += 1.5
            reasons.append("Title+year format (movie-like)")

        # =====================================================================
        # RULE 4: DOCUMENTARY CHECK
        # =====================================================================
        is_documentary = False
        for phrase in self.patterns.DOCUMENTARY_PHRASES:
            if phrase in full_text:
                is_documentary = True
                reasons.append(f"Documentary indicator: '{phrase}'")
                break

        # =====================================================================
        # FINAL DECISION
        # Series needs a STRONG signal (>= 3.5). Movie wins all ties.
        # =====================================================================
        SERIES_THRESHOLD = 3.5  # raised from 2.0 — must be truly explicit

        if series_score >= SERIES_THRESHOLD and series_score > movie_score:
            content_type = ContentType.ANIME if 'anime' in full_text else ContentType.SERIES
            confidence = min(1.0, series_score / 12.0)
        elif movie_score >= SERIES_THRESHOLD and movie_score > series_score:
            content_type = ContentType.DOCUMENTARY if is_documentary else ContentType.MOVIE
            confidence = min(1.0, movie_score / 10.0)
        elif series_score > 0 and series_score > movie_score and series_score >= SERIES_THRESHOLD:
            content_type = ContentType.SERIES
            confidence = 0.6
        else:
            # Default: MOVIE (more common, safer default)
            content_type = ContentType.DOCUMENTARY if is_documentary else ContentType.MOVIE
            confidence = 0.4
            reasons.append("Default: movie (no strong series signal)")

        return DetectionResult(
            content_type=content_type,
            confidence=confidence,
            reasons=reasons,
            season_count=season_count,
            detected_seasons=detected_seasons
        )
    
    def is_series(self, title: str, page_content: str = "") -> bool:
        """
        Quick check if content is series
        
        Args:
            title: Content title
            page_content: Optional page content
        
        Returns:
            True if series/anime
        """
        result = self.detect(title, page_content)
        return result.is_series
    
    def is_movie(self, title: str, page_content: str = "") -> bool:
        """
        Quick check if content is movie
        
        Args:
            title: Content title
            page_content: Optional page content
        
        Returns:
            True if movie
        """
        result = self.detect(title, page_content)
        return result.is_movie
    
    def get_seasons(self, title: str, page_content: str = "") -> List[str]:
        """
        Extract season list from content
        
        Args:
            title: Content title
            page_content: Optional page content
        
        Returns:
            List of seasons like ["S01", "S02", "S03"]
        """
        result = self.detect(title, page_content)
        return result.detected_seasons


# =============================================================================
# GLOBAL DETECTOR INSTANCE
# =============================================================================

_detector = ContentDetector()


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

def detect_content_type(title: str, page_content: str = "") -> str:
    """
    Detect content type (returns string)
    
    Args:
        title: Content title
        page_content: Optional page content
    
    Returns:
        "movie", "series", "anime", or "documentary"
    """
    result = _detector.detect(title, page_content)
    return str(result.content_type)


def is_series_content(title: str, page_content: str = "") -> bool:
    """
    Check if content is a series
    
    Args:
        title: Content title
        page_content: Optional page content
    
    Returns:
        True if series/anime
    """
    return _detector.is_series(title, page_content)


def is_movie_content(title: str, page_content: str = "") -> bool:
    """
    Check if content is a movie
    
    Args:
        title: Content title
        page_content: Optional page content
    
    Returns:
        True if movie
    """
    return _detector.is_movie(title, page_content)


def is_definitely_movie(title: str, page_content: str = "") -> bool:
    """
    Check if content is DEFINITELY a movie (high confidence)
    
    Args:
        title: Content title
        page_content: Optional page content
    
    Returns:
        True if definitely a movie
    """
    result = _detector.detect(title, page_content)
    return result.is_movie and result.confidence >= 0.6


def is_definitely_series(title: str, page_content: str = "") -> bool:
    """
    Check if content is DEFINITELY a series (high confidence)
    
    Args:
        title: Content title
        page_content: Optional page content
    
    Returns:
        True if definitely a series
    """
    result = _detector.detect(title, page_content)
    return result.is_series and result.confidence >= 0.6


def get_detection_result(title: str, page_content: str = "") -> DetectionResult:
    """
    Get full detection result
    
    Args:
        title: Content title
        page_content: Optional page content
    
    Returns:
        DetectionResult object
    """
    return _detector.detect(title, page_content)


def extract_seasons_from_title(title: str) -> List[str]:
    """
    Extract season numbers from title
    
    Args:
        title: Content title
    
    Returns:
        List like ["S01", "S02"]
    """
    return _detector.get_seasons(title)


# =============================================================================
# ADVANCED DETECTION FUNCTIONS
# =============================================================================

def detect_season_range(title: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Detect season range from title
    
    Args:
        title: Content title
    
    Returns:
        Tuple of (start_season, end_season) or (None, None)
    
    Examples:
        "Show S01-S05" -> (1, 5)
        "Show Season 1 to Season 3" -> (1, 3)
    """
    title_lower = title.lower()
    
    # Pattern: S01-S05 or S1-S5
    match = re.search(r's0?(\d+)\s*[-–to]+\s*s0?(\d+)', title_lower)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Pattern: Season 1 - Season 5
    match = re.search(r'season\s*(\d+)\s*[-–to]+\s*season\s*(\d+)', title_lower)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Pattern: Seasons 1-5
    match = re.search(r'seasons?\s*(\d+)\s*[-–to]+\s*(\d+)', title_lower)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    return None, None


def detect_episode_info(title: str) -> Dict[str, any]:
    """
    Detect episode information from title
    
    Args:
        title: Content title
    
    Returns:
        Dict with episode info
    """
    title_lower = title.lower()
    result = {
        "has_episodes": False,
        "episode_count": None,
        "episode_range": None,
        "specific_episode": None
    }
    
    # All episodes
    if re.search(r'all\s*episodes?|complete\s*episodes?', title_lower):
        result["has_episodes"] = True
        return result
    
    # Episode count: "10 Episodes"
    match = re.search(r'(\d+)\s*episodes?', title_lower)
    if match:
        result["has_episodes"] = True
        result["episode_count"] = int(match.group(1))
        return result
    
    # Episode range: E01-E10
    match = re.search(r'e0?(\d+)\s*[-–to]+\s*e0?(\d+)', title_lower)
    if match:
        result["has_episodes"] = True
        result["episode_range"] = (int(match.group(1)), int(match.group(2)))
        return result
    
    # Specific episode: S01E05
    match = re.search(r's0?(\d+)\s*e0?(\d+)', title_lower)
    if match:
        result["has_episodes"] = True
        result["specific_episode"] = {
            "season": int(match.group(1)),
            "episode": int(match.group(2))
        }
        return result
    
    return result


def get_content_emoji(content_type: str) -> str:
    """
    Get emoji for content type
    
    Args:
        content_type: Type string
    
    Returns:
        Emoji string
    """
    emoji_map = {
        "movie": "🎬",
        "series": "📺",
        "anime": "🎌",
        "documentary": "📹",
        "unknown": "❓"
    }
    return emoji_map.get(content_type.lower(), "🎬")


def format_detection_result(result: DetectionResult) -> str:
    """
    Format detection result for display
    
    Args:
        result: DetectionResult object
    
    Returns:
        Formatted string
    """
    emoji = get_content_emoji(str(result.content_type))
    confidence_bar = "█" * int(result.confidence * 10) + "░" * (10 - int(result.confidence * 10))
    
    text = f"{emoji} **{result.content_type.value.title()}**\n"
    text += f"📊 Confidence: [{confidence_bar}] {result.confidence:.0%}\n"
    
    if result.is_series and result.detected_seasons:
        text += f"📁 Seasons: {', '.join(result.detected_seasons)}\n"
    
    if result.reasons:
        text += f"💡 Reasons: {', '.join(result.reasons[:3])}"
    
    return text


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("CONTENT DETECTOR DEMO")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        # Movies
        ("Avengers Endgame 2019 1080p WEB-DL", ""),
        ("Oppenheimer (2023) Hindi Dubbed Full Movie", ""),
        ("KGF Chapter 2 Hindi Movie Download", ""),
        
        # Series
        ("Money Heist S01-S05 Complete Web Series", ""),
        ("Squid Game Season 1 All Episodes", ""),
        ("Breaking Bad S01 S02 S03 S04 S05", ""),
        ("Stranger Things Complete Series", ""),
        
        # Anime
        ("Demon Slayer Anime Series S01-S03", ""),
        ("Attack on Titan All Seasons", ""),
        
        # Edge cases
        ("The Batman 2022", ""),  # Movie with "The"
        ("The Mandalorian S01", ""),  # Series with "The"
    ]
    
    detector = ContentDetector(debug=True)
    
    for title, content in test_cases:
        print(f"\n{'─' * 50}")
        print(f"📝 Title: {title}")
        
        result = detector.detect(title, content)
        
        emoji = get_content_emoji(str(result.content_type))
        print(f"{emoji} Type: {result.content_type.value}")
        print(f"📊 Confidence: {result.confidence:.0%}")
        
        if result.detected_seasons:
            print(f"📁 Seasons: {result.detected_seasons}")
        
        if result.reasons:
            print(f"💡 Reasons: {result.reasons[:2]}")
    
    print(f"\n{'=' * 60}")
    print("✅ Detection demo complete!")