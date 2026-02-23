"""
=============================================================================
BOLLYFLIX BOT - LINK EXTRACTORS
=============================================================================
Advanced extraction of download links, seasons, episodes, and qualities
from BollyFlix pages with multiple fallback methods
=============================================================================
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag

from config import DOWNLOAD_DOMAINS, QUALITY_ORDER
from logger import log_info, log_debug, log_warning
from helpers import sort_qualities


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class DownloadLink:
    """Single download link with metadata"""
    url: str
    quality: str = "720p"
    season: Optional[str] = None
    episode: Optional[str] = None
    source: str = ""  # Where link was found
    
    def __hash__(self):
        return hash(self.url)
    
    def __eq__(self, other):
        if isinstance(other, DownloadLink):
            return self.url == other.url
        return False


@dataclass
class ExtractionResult:
    """Result of link extraction"""
    is_series: bool = False
    
    # For movies: quality -> url
    movie_links: Dict[str, str] = field(default_factory=dict)
    
    # For series: season -> {quality -> url}
    series_links: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # All found links (for debugging)
    all_links: List[DownloadLink] = field(default_factory=list)
    
    # Available qualities
    qualities: List[str] = field(default_factory=list)
    
    # Available seasons
    seasons: List[str] = field(default_factory=list)
    
    @property
    def has_links(self) -> bool:
        return bool(self.movie_links or self.series_links)


# =============================================================================
# QUALITY DETECTOR
# =============================================================================

class QualityDetector:
    """Detect video quality from text"""
    
    # Quality patterns with priority (higher = better match)
    PATTERNS = [
        # 4K variants
        (re.compile(r'2160p', re.I), "2160p", 10),
        (re.compile(r'\b4k\b', re.I), "2160p", 10),
        (re.compile(r'\buhd\b', re.I), "2160p", 9),
        
        # 1080p variants
        (re.compile(r'1080p\s*hq', re.I), "1080p HQ", 8),
        (re.compile(r'1080p\s*(?:10\s*bit|10bit)', re.I), "1080p 10bit", 8),
        (re.compile(r'1080p', re.I), "1080p", 7),
        (re.compile(r'\bfull\s*hd\b', re.I), "1080p", 6),
        (re.compile(r'\bfhd\b', re.I), "1080p", 6),
        
        # 720p variants
        (re.compile(r'720p\s*(?:10\s*bit|10bit)', re.I), "720p 10bit", 5),
        (re.compile(r'720p', re.I), "720p", 4),
        (re.compile(r'\bhd\b(?!\s*rip|\s*cam|\s*tc)', re.I), "720p", 3),
        
        # 480p variants
        (re.compile(r'480p', re.I), "480p", 2),
        (re.compile(r'\bsd\b', re.I), "480p", 1),
        
        # 360p (rare)
        (re.compile(r'360p', re.I), "360p", 0),
    ]
    
    @classmethod
    def detect(cls, text: str) -> Optional[str]:
        """
        Detect quality from text
        
        Args:
            text: Text to analyze
        
        Returns:
            Quality string or None
        """
        if not text:
            return None
        
        best_match = None
        best_priority = -1
        
        for pattern, quality, priority in cls.PATTERNS:
            if pattern.search(text) and priority > best_priority:
                best_match = quality
                best_priority = priority
        
        return best_match
    
    @classmethod
    def detect_all(cls, text: str) -> List[str]:
        """
        Detect all qualities mentioned in text
        
        Args:
            text: Text to analyze
        
        Returns:
            List of quality strings
        """
        if not text:
            return []
        
        qualities = []
        
        for pattern, quality, _ in cls.PATTERNS:
            if pattern.search(text) and quality not in qualities:
                qualities.append(quality)
        
        return sort_qualities(qualities)


# =============================================================================
# SEASON DETECTOR
# =============================================================================

class SeasonDetector:
    """Detect season information from text"""
    
    # Season patterns
    PATTERNS = [
        # S01, S1, S01E01
        re.compile(r'\bS0?(\d{1,2})(?:E\d+)?', re.I),
        
        # Season 1, Season 01
        re.compile(r'\bSeason\s*(\d{1,2})\b', re.I),
        
        # Season-1, Season_1
        re.compile(r'\bSeason[-_](\d{1,2})\b', re.I),
    ]
    
    # Range patterns
    RANGE_PATTERNS = [
        # S01-S05, S1-S5
        re.compile(r'\bS0?(\d{1,2})\s*[-–to]+\s*S0?(\d{1,2})\b', re.I),
        
        # Season 1-5, Season 1 to 5
        re.compile(r'\bSeason\s*(\d{1,2})\s*[-–to]+\s*(?:Season\s*)?(\d{1,2})\b', re.I),
        
        # Seasons 1-5
        re.compile(r'\bSeasons?\s*(\d{1,2})\s*[-–&,]\s*(\d{1,2})\b', re.I),
    ]
    
    @classmethod
    def detect(cls, text: str) -> Optional[str]:
        """
        Detect single season from text
        
        Args:
            text: Text to analyze
        
        Returns:
            Season string like "S01" or None
        """
        if not text:
            return None
        
        for pattern in cls.PATTERNS:
            match = pattern.search(text)
            if match:
                season_num = int(match.group(1))
                return f"S{season_num:02d}"
        
        return None
    
    @classmethod
    def detect_all(cls, text: str) -> List[str]:
        """
        Detect all seasons mentioned in text
        
        Args:
            text: Text to analyze
        
        Returns:
            Sorted list of season strings like ["S01", "S02", "S03"]
        """
        if not text:
            return []
        
        seasons: Set[int] = set()
        
        # Check for ranges first
        for pattern in cls.RANGE_PATTERNS:
            match = pattern.search(text)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                for s in range(start, end + 1):
                    seasons.add(s)
        
        # Check individual seasons
        for pattern in cls.PATTERNS:
            for match in pattern.finditer(text):
                seasons.add(int(match.group(1)))
        
        # Format and sort
        return sorted([f"S{s:02d}" for s in seasons])
    
    @classmethod
    def detect_range(cls, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Detect season range from text
        
        Args:
            text: Text to analyze
        
        Returns:
            Tuple of (start, end) or (None, None)
        """
        if not text:
            return None, None
        
        for pattern in cls.RANGE_PATTERNS:
            match = pattern.search(text)
            if match:
                return int(match.group(1)), int(match.group(2))
        
        return None, None


# =============================================================================
# EPISODE DETECTOR
# =============================================================================

class EpisodeDetector:
    """Detect episode information from text"""
    
    PATTERNS = [
        # E01, E1, EP01, EP1
        re.compile(r'\bE[Pp]?0?(\d{1,3})\b'),
        
        # Episode 1, Episode 01
        re.compile(r'\bEpisode\s*(\d{1,3})\b', re.I),
        
        # S01E01 format (extract episode)
        re.compile(r'\bS\d+E(\d{1,3})\b', re.I),
    ]
    
    # Episode count patterns
    COUNT_PATTERNS = [
        re.compile(r'(\d+)\s*Episodes?', re.I),
        re.compile(r'All\s*(\d+)\s*Ep', re.I),
    ]
    
    # All episodes indicator
    ALL_EPISODES_PATTERNS = [
        re.compile(r'\bAll\s*Episodes?\b', re.I),
        re.compile(r'\bComplete\s*(?:Episodes?|Season)\b', re.I),
        re.compile(r'\bFull\s*Season\b', re.I),
    ]
    
    @classmethod
    def detect(cls, text: str) -> Optional[str]:
        """
        Detect single episode from text
        
        Args:
            text: Text to analyze
        
        Returns:
            Episode string like "E01" or None
        """
        if not text:
            return None
        
        for pattern in cls.PATTERNS:
            match = pattern.search(text)
            if match:
                ep_num = int(match.group(1))
                return f"E{ep_num:02d}"
        
        return None
    
    @classmethod
    def is_all_episodes(cls, text: str) -> bool:
        """Check if text indicates all episodes"""
        if not text:
            return False
        
        return any(p.search(text) for p in cls.ALL_EPISODES_PATTERNS)
    
    @classmethod
    def get_episode_count(cls, text: str) -> Optional[int]:
        """Get episode count from text"""
        if not text:
            return None
        
        for pattern in cls.COUNT_PATTERNS:
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        
        return None


# =============================================================================
# LINK VALIDATOR
# =============================================================================

class LinkValidator:
    """Validate and classify download links"""
    
    def __init__(self, domains: List[str] = None):
        self.domains = domains or DOWNLOAD_DOMAINS
    
    def is_download_link(self, url: str) -> bool:
        """Check if URL is a download link"""
        if not url or not isinstance(url, str):
            return False
        
        url_lower = url.lower()
        
        # Must start with http
        if not url_lower.startswith('http'):
            return False
        
        # Check for download domains
        return any(domain in url_lower for domain in self.domains)
    
    def get_link_type(self, url: str) -> str:
        """
        Get type of download link
        
        Returns:
            "ozolinks", "gdflix", "hubcloud", "other"
        """
        if not url:
            return "unknown"
        
        url_lower = url.lower()
        
        if 'ozolinks' in url_lower or 'ouo' in url_lower:
            return "ozolinks"
        elif 'gdflix' in url_lower:
            return "gdflix"
        elif 'hubcloud' in url_lower or 'hubdrive' in url_lower:
            return "hubcloud"
        elif 'fastdl' in url_lower:
            return "fastdl"
        elif 'filepress' in url_lower:
            return "filepress"
        elif 't.me' in url_lower:
            return "telegram"
        else:
            return "other"
    
    def get_priority(self, url: str) -> int:
        """
        Get link priority (higher = better)
        
        Priority order:
        1. Telegram (direct file)
        2. GDFlix (fast)
        3. FastDL
        4. HubCloud
        5. OzoLinks (has timer)
        6. Others
        """
        link_type = self.get_link_type(url)
        
        priorities = {
            "telegram": 100,
            "gdflix": 80,
            "fastdl": 70,
            "hubcloud": 60,
            "filepress": 50,
            "ozolinks": 40,
            "other": 10,
            "unknown": 0
        }
        
        return priorities.get(link_type, 0)


# =============================================================================
# MAIN EXTRACTOR CLASS
# =============================================================================

class LinkExtractor:
    """
    Advanced link extractor for BollyFlix pages
    
    Features:
    - Context-aware extraction (tracks current season/quality)
    - Multiple fallback methods
    - Link deduplication
    - Priority-based link selection
    
    Usage:
        extractor = LinkExtractor()
        result = extractor.extract(soup, page_text, is_series=True)
        
        if result.is_series:
            for season, qualities in result.series_links.items():
                print(f"{season}: {qualities}")
    """
    
    def __init__(self):
        self.quality_detector = QualityDetector()
        self.season_detector = SeasonDetector()
        self.episode_detector = EpisodeDetector()
        self.link_validator = LinkValidator()
    
    def extract(
        self,
        soup: BeautifulSoup,
        page_text: str = "",
        is_series: bool = False
    ) -> ExtractionResult:
        """
        Extract all download links from page
        
        Args:
            soup: BeautifulSoup object
            page_text: Page text content
            is_series: Whether content is a series
        
        Returns:
            ExtractionResult object
        """
        result = ExtractionResult(is_series=is_series)
        
        # Find content container
        content_div = self._find_content_div(soup)
        
        # Extract all links with context
        all_links = self._extract_links_with_context(content_div)
        result.all_links = all_links
        
        if is_series:
            # Organize by season and quality
            result.series_links = self._organize_series_links(all_links)
            result.seasons = sorted(result.series_links.keys())
            result.qualities = self._get_all_qualities(result.series_links)
        else:
            # Organize by quality only
            result.movie_links = self._organize_movie_links(all_links)
            result.qualities = sort_qualities(list(result.movie_links.keys()))
        
        return result
    
    def _find_content_div(self, soup: BeautifulSoup) -> Tag:
        """Find the main content container"""
        selectors = [
            ('div', {'class_': 'entry-content'}),
            ('div', {'class_': 'post-content'}),
            ('div', {'class_': 'content'}),
            ('article', {}),
        ]
        
        for tag, attrs in selectors:
            element = soup.find(tag, **attrs)
            if element:
                return element
        
        return soup
    
    def _extract_links_with_context(self, container: Tag) -> List[DownloadLink]:
        """Extract links while tracking context (season/quality)"""
        links = []
        
        # Context tracking
        current_season = None
        current_quality = None
        
        # Scan all elements in order
        elements = container.find_all([
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',  # Headings
            'p', 'div', 'span',  # Text containers
            'a',  # Links
            'strong', 'b', 'em',  # Emphasis
            'li',  # List items
        ])
        
        for element in elements:
            text = element.get_text().strip()
            
            if not text:
                continue
            
            # Update context from headings and text
            if element.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'):
                # Check for season
                detected_season = self.season_detector.detect(text)
                if detected_season:
                    current_season = detected_season
                
                # Check for quality
                detected_quality = self.quality_detector.detect(text)
                if detected_quality:
                    current_quality = detected_quality
            
            # Extract links
            if element.name == 'a':
                href = element.get('href', '')
                
                if self.link_validator.is_download_link(href):
                    link = self._create_download_link(
                        url=href,
                        text=text,
                        context_season=current_season,
                        context_quality=current_quality
                    )
                    links.append(link)
            
            # Also check for quality/season in regular text
            else:
                detected_season = self.season_detector.detect(text)
                if detected_season:
                    current_season = detected_season
                
                detected_quality = self.quality_detector.detect(text)
                if detected_quality:
                    current_quality = detected_quality
        
        return links
    
    def _create_download_link(
        self,
        url: str,
        text: str,
        context_season: Optional[str],
        context_quality: Optional[str]
    ) -> DownloadLink:
        """Create DownloadLink with detected metadata"""
        # Try to detect from link text first
        season = self.season_detector.detect(text) or context_season
        quality = self.quality_detector.detect(text) or context_quality or "720p"
        episode = self.episode_detector.detect(text)
        
        # Default season for series
        if not season:
            season = "S01"
        
        return DownloadLink(
            url=url,
            quality=quality,
            season=season,
            episode=episode,
            source=self.link_validator.get_link_type(url)
        )
    
    def _organize_series_links(
        self,
        links: List[DownloadLink]
    ) -> Dict[str, Dict[str, str]]:
        """Organize links by season and quality"""
        organized: Dict[str, Dict[str, str]] = {}
        
        for link in links:
            season = link.season or "S01"
            quality = link.quality or "720p"
            
            if season not in organized:
                organized[season] = {}
            
            # Keep highest priority link for each quality
            if quality not in organized[season]:
                organized[season][quality] = link.url
            else:
                # Compare priorities
                existing_priority = self.link_validator.get_priority(organized[season][quality])
                new_priority = self.link_validator.get_priority(link.url)
                
                if new_priority > existing_priority:
                    organized[season][quality] = link.url
        
        return organized
    
    def _organize_movie_links(self, links: List[DownloadLink]) -> Dict[str, str]:
        """Organize links by quality only"""
        organized: Dict[str, str] = {}
        
        for link in links:
            quality = link.quality or "720p"
            
            # Keep highest priority link for each quality
            if quality not in organized:
                organized[quality] = link.url
            else:
                existing_priority = self.link_validator.get_priority(organized[quality])
                new_priority = self.link_validator.get_priority(link.url)
                
                if new_priority > existing_priority:
                    organized[quality] = link.url
        
        return organized
    
    def _get_all_qualities(self, series_links: Dict[str, Dict[str, str]]) -> List[str]:
        """Get all unique qualities from series links"""
        qualities = set()
        
        for season_data in series_links.values():
            qualities.update(season_data.keys())
        
        return sort_qualities(list(qualities))


# =============================================================================
# STANDALONE EXTRACTION FUNCTIONS
# =============================================================================

def extract_movie_links(soup: BeautifulSoup, page_text: str = "") -> Dict[str, str]:
    """
    Extract download links for movies
    
    Args:
        soup: BeautifulSoup object
        page_text: Page text content
    
    Returns:
        Dict of quality -> url
    """
    extractor = LinkExtractor()
    result = extractor.extract(soup, page_text, is_series=False)
    return result.movie_links


def extract_series_links(soup: BeautifulSoup, page_text: str = "") -> Dict[str, Dict[str, str]]:
    """
    Extract download links for series
    
    Args:
        soup: BeautifulSoup object
        page_text: Page text content
    
    Returns:
        Dict of season -> {quality -> url}
    """
    extractor = LinkExtractor()
    result = extractor.extract(soup, page_text, is_series=True)
    return result.series_links


def extract_seasons_from_page(soup: BeautifulSoup, page_text: str = "") -> Dict[str, Dict[str, str]]:
    """
    Alias for extract_series_links (backward compatibility)
    """
    return extract_series_links(soup, page_text)


def detect_quality(text: str) -> Optional[str]:
    """Detect quality from text"""
    return QualityDetector.detect(text)


def detect_season(text: str) -> Optional[str]:
    """Detect season from text"""
    return SeasonDetector.detect(text)


def detect_all_seasons(text: str) -> List[str]:
    """Detect all seasons from text"""
    return SeasonDetector.detect_all(text)


def get_season_range(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Get season range from text"""
    return SeasonDetector.detect_range(text)


def is_download_url(url: str) -> bool:
    """Check if URL is a download link"""
    return LinkValidator().is_download_link(url)


def get_link_type(url: str) -> str:
    """Get type of download link"""
    return LinkValidator().get_link_type(url)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("EXTRACTORS DEMO")
    print("=" * 60)
    
    # Quality detection
    print("\n📊 Quality Detection:")
    test_texts = [
        "Download 1080p WEB-DL",
        "720p 10bit HEVC",
        "4K UHD BluRay",
        "480p HDRip",
        "Full HD Movie"
    ]
    
    for text in test_texts:
        quality = QualityDetector.detect(text)
        print(f"  '{text}' -> {quality}")
    
    # Season detection
    print("\n📁 Season Detection:")
    test_texts = [
        "Money Heist S01-S05",
        "Breaking Bad Season 3",
        "Stranger Things S01 S02 S03",
        "Game of Thrones Seasons 1-8"
    ]
    
    for text in test_texts:
        seasons = SeasonDetector.detect_all(text)
        print(f"  '{text}' -> {seasons}")
    
    # Link validation
    print("\n🔗 Link Validation:")
    test_urls = [
        "https://ozolinks.com/abc123",
        "https://gdflix.top/file/xyz",
        "https://t.me/filebot?start=abc",
        "https://google.com"
    ]
    
    validator = LinkValidator()
    for url in test_urls:
        is_dl = validator.is_download_link(url)
        link_type = validator.get_link_type(url)
        priority = validator.get_priority(url)
        print(f"  {url[:40]}...")
        print(f"    Download: {is_dl} | Type: {link_type} | Priority: {priority}")
    
    print(f"\n{'=' * 60}")
    print("✅ Extractors demo complete!")