"""
=============================================================================
BOLLYFLIX BOT - WEB SCRAPER v3.0 (ULTRA FAST - PURE REQUESTS)
=============================================================================
High Performance Scraper with:
- NO CHROME - Pure HTTP Requests
- NO CLOUDSCRAPER - Simple Requests Only
- Connection Pooling
- Smart Caching
- Parallel Processing
- Auto Retry Logic
- 2000+ Users Scalable
- Rate Limiting Protection
- Domain Rotation
=============================================================================
"""

import re
import sys
import time
import random
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    BOLLYFLIX_BASE_URL,
    DEFAULT_HEADERS,
    MAX_SEARCH_RESULTS,
    REQUEST_TIMEOUT
)
from logger import (
    log_info, log_error, log_success,
    log_warning, log_search, log_working
)
from helpers import (
    clean_title, extract_year, extract_rating,
    extract_genre, extract_duration, sort_qualities
)
from detectors import detect_content_type, is_series_content

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

print("📦 Scraper module loading...", flush=True)


# =============================================================================
# CONSTANTS
# =============================================================================

# Multiple domains for rotation
BOLLYFLIX_DOMAINS = [
    "https://bollyflix.sarl",
]

# Download domains
DOWNLOAD_DOMAINS = [
    'fxlinks',
    'ozolinks', 'ouo.io', 'ouo.press',
    'gdflix', 'gdrive', 'gdtot',
    'hubcloud', 'hubdrive',
    'filepress', 'filebee',
    'links4u', 'link4u',
    'shrinkme', 'shorte',
    'droplink', 'dropgalaxy',
    'indishare', 'linkvertise',
    'fastdl', 'fastlinks',
    'link.', 'go.', 'redirect'
]

# Quality patterns
QUALITY_PATTERNS = {
    "480p": re.compile(r'480p', re.I),
    "720p": re.compile(r'720p(?!\s*10)', re.I),
    "720p 10bit": re.compile(r'720p\s*10\s*bit', re.I),
    "1080p": re.compile(r'1080p(?!\s*10)(?!\s*hq)', re.I),
    "1080p 10bit": re.compile(r'1080p\s*10\s*bit', re.I),
    "1080p HQ": re.compile(r'1080p\s*hq', re.I),
    "2160p": re.compile(r'2160p|4k|uhd', re.I),
}

SEASON_PATTERN = re.compile(r'[Ss]0?(\d{1,2})|[Ss]eason\s*(\d{1,2})', re.I)
EPISODE_PATTERN = re.compile(r'[Ee]0?(\d{1,3})|[Ee]pisode\s*(\d{1,3})', re.I)

# User agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class SearchResult:
    title: str
    clean_title: str
    url: str
    poster: str = ""
    year: str = "N/A"
    content_type: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "clean_title": self.clean_title,
            "url": self.url,
            "poster": self.poster,
            "year": self.year,
            "content_type": self.content_type
        }


@dataclass
class ContentInfo:
    url: str
    title: str = ""
    clean_title: str = ""
    year: str = "N/A"
    genre: str = "N/A"
    duration: str = "N/A"
    rating: str = "7.5"
    poster: str = ""
    is_series: bool = False
    content_type: str = "movie"
    description: str = ""
    director: str = "N/A"
    cast: str = "N/A"
    language: str = "N/A"
    download_links: Dict[str, str] = field(default_factory=dict)
    seasons: Dict[str, Dict[str, str]] = field(default_factory=dict)
    qualities: List[str] = field(default_factory=list)
    scraped_at: str = ""
    source: str = "bollyflix"
    
    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "title": self.title,
            "clean_title": self.clean_title,
            "year": self.year,
            "genre": self.genre,
            "duration": self.duration,
            "rating": self.rating,
            "poster": self.poster,
            "is_series": self.is_series,
            "content_type": self.content_type,
            "download_links": self.download_links,
            "seasons": self.seasons,
            "qualities": self.qualities,
        }


# =============================================================================
# CACHE MANAGER
# =============================================================================

class CacheManager:
    def __init__(self, default_ttl: timedelta = timedelta(hours=1), max_size: int = 10000):
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.lock = threading.RLock()
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if datetime.now() < expiry:
                    self.hits += 1
                    return value
                else:
                    del self.cache[key]
            self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: timedelta = None):
        if ttl is None:
            ttl = self.default_ttl
        with self.lock:
            if len(self.cache) >= self.max_size:
                keys_to_remove = list(self.cache.keys())[:self.max_size // 10]
                for k in keys_to_remove:
                    del self.cache[k]
            self.cache[key] = (value, datetime.now() + ttl)
    
    def clear(self):
        with self.lock:
            self.cache.clear()
    
    def stats(self) -> Dict:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {"size": len(self.cache), "hits": self.hits, "misses": self.misses, "hit_rate": f"{hit_rate:.1f}%"}


_search_cache = CacheManager(default_ttl=timedelta(minutes=30), max_size=5000)
_content_cache = CacheManager(default_ttl=timedelta(hours=2), max_size=10000)


# =============================================================================
# HTTP CLIENT (Pure Requests - No Cloudscraper)
# =============================================================================

class HttpClient:
    def __init__(self, pool_size: int = 50, max_retries: int = 3, timeout: int = 20):
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.timeout = timeout
        self._session_pool: List[requests.Session] = []
        self._pool_lock = threading.Lock()
        self._working_domain: Optional[str] = None
        self._request_count = 0
        self._error_count = 0
        
        self._init_pool()
        print(f"✅ HTTP Client initialized with {len(self._session_pool)} sessions", flush=True)
    
    def _init_pool(self):
        for _ in range(self.pool_size):
            session = self._create_session()
            self._session_pool.append(session)
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        
        retry = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=retry,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self._get_headers())
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        ua = random.choice(USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "DNT": "1",
        }
    
    def _get_session(self) -> requests.Session:
        with self._pool_lock:
            if self._session_pool:
                session = self._session_pool.pop(0)
                session.headers.update(self._get_headers())
                return session
            return self._create_session()
    
    def _return_session(self, session: requests.Session):
        with self._pool_lock:
            if len(self._session_pool) < self.pool_size:
                self._session_pool.append(session)
    
    def _find_working_domain(self) -> str:
        print("🔍 Finding working domain...", flush=True)
        
        domains = BOLLYFLIX_DOMAINS.copy()
        random.shuffle(domains)
        
        for domain in domains:
            try:
                session = self._get_session()
                try:
                    response = session.get(domain, timeout=10, allow_redirects=True)
                    
                    if response.status_code == 200 and not self._is_blocked(response):
                        print(f"✅ Working domain: {domain}", flush=True)
                        self._working_domain = domain
                        return domain
                finally:
                    self._return_session(session)
            except Exception as e:
                print(f"❌ Domain {domain} failed: {e}", flush=True)
                continue
        
        print(f"⚠️ No working domain, using default: {BOLLYFLIX_BASE_URL}", flush=True)
        return BOLLYFLIX_BASE_URL
    
    def _is_blocked(self, response: requests.Response) -> bool:
        if response.status_code in [403, 503, 520, 521, 522, 523, 524]:
            return True
        
        content = response.text[:5000].lower()
        blocked = [
            'cloudflare', 'cf-browser-verification', 'challenge-platform',
            'just a moment', 'enable javascript', 'checking your browser',
            'ddos-guard', 'attention required', 'blocked'
        ]
        return any(b in content for b in blocked)
    
    def get(self, url: str) -> Optional[requests.Response]:
        session = None
        
        for attempt in range(self.max_retries):
            try:
                session = self._get_session()
                
                if attempt > 0:
                    time.sleep(random.uniform(0.5, 1.5))
                
                response = session.get(url, timeout=self.timeout, allow_redirects=True)
                response.encoding = response.apparent_encoding or 'utf-8'
                
                if self._is_blocked(response):
                    print(f"⚠️ Blocked (attempt {attempt + 1})", flush=True)
                    self._return_session(session)
                    session = None
                    continue
                
                self._request_count += 1
                return response
                
            except requests.exceptions.Timeout:
                print(f"⚠️ Timeout (attempt {attempt + 1})", flush=True)
            except requests.exceptions.ConnectionError:
                print(f"⚠️ Connection error (attempt {attempt + 1})", flush=True)
            except Exception as e:
                print(f"❌ Request error: {e}", flush=True)
            finally:
                if session:
                    self._return_session(session)
                    session = None
        
        self._error_count += 1
        return None
    
    def get_with_domain_rotation(self, path: str) -> Optional[requests.Response]:
        if not self._working_domain:
            self._find_working_domain()
        
        domain = self._working_domain or BOLLYFLIX_BASE_URL
        url = domain.rstrip('/') + '/' + path.lstrip('/')
        
        response = self.get(url)
        
        if response is None or self._is_blocked(response):
            print("🔄 Domain blocked, rotating...", flush=True)
            self._working_domain = None
            new_domain = self._find_working_domain()
            
            if new_domain != domain:
                new_url = new_domain.rstrip('/') + '/' + path.lstrip('/')
                response = self.get(new_url)
        
        return response
    
    def stats(self) -> Dict:
        return {
            "requests": self._request_count,
            "errors": self._error_count,
            "pool_size": len(self._session_pool),
            "working_domain": self._working_domain or "unknown"
        }
    
    def close(self):
        with self._pool_lock:
            for session in self._session_pool:
                try:
                    session.close()
                except:
                    pass
            self._session_pool.clear()


_http_client = HttpClient(pool_size=50, max_retries=3, timeout=20)


# =============================================================================
# POSTER EXTRACTOR
# =============================================================================

class PosterExtractor:
    LAZY_ATTRS = ['data-src', 'data-lazy-src', 'data-original', 'data-lazy', 'src']
    
    @classmethod
    def extract_from_element(cls, element) -> str:
        if not element:
            return ""
        
        img = element.find('img')
        if img:
            for attr in cls.LAZY_ATTRS:
                url = img.get(attr, '')
                if url and not url.startswith('data:') and 'placeholder' not in url.lower():
                    return cls._fix_url(url)
        
        for tag in element.find_all(['div', 'figure', 'a'], limit=10):
            style = tag.get('style', '')
            if 'url(' in style:
                match = re.search(r'url\(["\']?([^"\')\s]+)', style)
                if match:
                    return cls._fix_url(match.group(1))
        
        return ""
    
    @classmethod
    def extract_from_page(cls, soup) -> str:
        selectors = [
            ('div', {'class_': 'featured-image'}),
            ('div', {'class_': 'post-thumbnail'}),
            ('div', {'class_': 'poster'}),
        ]
        
        for tag, attrs in selectors:
            element = soup.find(tag, **attrs)
            if element:
                poster = cls.extract_from_element(element)
                if poster:
                    return poster
        
        meta = soup.find('meta', {'property': 'og:image'})
        if meta:
            return cls._fix_url(meta.get('content', ''))
        
        return ""
    
    @staticmethod
    def _fix_url(url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if url.startswith('//'):
            return 'https:' + url
        if not url.startswith('http'):
            return 'https://' + url.lstrip('/')
        return url


# =============================================================================
# HELPERS
# =============================================================================

def is_download_link(url: str) -> bool:
    if not url:
        return False
    return any(d in url.lower() for d in DOWNLOAD_DOMAINS)


def detect_quality(text: str, current: str = "720p") -> str:
    if not text:
        return current
    for quality, pattern in QUALITY_PATTERNS.items():
        if pattern.search(text):
            return quality
    return current


def detect_season(text: str) -> Optional[str]:
    if not text:
        return None
    match = SEASON_PATTERN.search(text)
    if match:
        num = int(match.group(1) or match.group(2))
        return f"S{num:02d}"
    return None


def generate_cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


# =============================================================================
# LINK EXTRACTORS
# =============================================================================

def extract_movie_links(soup, page_text: str = "") -> Dict[str, str]:
    links = {}
    content_div = soup.find('div', class_='entry-content') or soup.find('article') or soup
    current_quality = "720p"
    
    for element in content_div.find_all(['h2', 'h3', 'h4', 'p', 'a', 'strong', 'span'], limit=500):
        text = element.get_text().strip()
        if not text:
            continue
        
        current_quality = detect_quality(text, current_quality)
        
        if element.name == 'a':
            href = element.get('href', '')
            if is_download_link(href):
                link_quality = detect_quality(text, current_quality)
                if link_quality not in links:
                    links[link_quality] = href
    
    return links


def extract_series_links(soup, page_text: str = "") -> Dict[str, Dict[str, str]]:
    seasons = {}
    content_div = soup.find('div', class_='entry-content') or soup.find('article') or soup
    current_season = None
    current_quality = "720p"
    
    for element in content_div.find_all(['h2', 'h3', 'h4', 'p', 'a', 'strong', 'span'], limit=1000):
        text = element.get_text().strip()
        if not text:
            continue
        
        detected_season = detect_season(text)
        if detected_season:
            current_season = detected_season
        
        current_quality = detect_quality(text, current_quality)
        
        if element.name == 'a':
            href = element.get('href', '')
            if is_download_link(href):
                link_season = detect_season(text) or current_season or "S01"
                link_quality = detect_quality(text, current_quality)
                
                if link_season not in seasons:
                    seasons[link_season] = {}
                if link_quality not in seasons[link_season]:
                    seasons[link_season][link_quality] = href
    
    return seasons


# =============================================================================
# ARTICLE PARSER
# =============================================================================

def parse_search_article(article) -> Optional[Dict]:
    title_tag = article.find('h2') or article.find('h3') or article.find('h4')
    if not title_tag:
        return None
    
    link_tag = article.find('a', href=True)
    if not link_tag:
        return None
    
    url = link_tag.get('href', '')
    if not url or not url.startswith('http'):
        return None
    
    raw_title = title_tag.get_text().strip()
    if not raw_title:
        return None
    
    poster = PosterExtractor.extract_from_element(article)
    content_type = "series" if is_series_content(raw_title) else "movie"
    
    return {
        "title": raw_title,
        "clean_title": clean_title(raw_title),
        "url": url,
        "poster": poster,
        "year": extract_year(raw_title),
        "content_type": content_type
    }


# =============================================================================
# SEARCH FUNCTION
# =============================================================================

def _search_single_page(url: str, retries: int = 3) -> Optional[BeautifulSoup]:
    """Fetch a search page with retry + header rotation"""
    for attempt in range(retries):
        try:
            session = _http_client._get_session()
            try:
                # Rotate User-Agent + add Referer on each attempt
                headers = _http_client._get_headers()
                headers["Referer"] = "https://www.google.com/"
                
                if attempt > 0:
                    # Different UA on retry
                    headers["User-Agent"] = random.choice(USER_AGENTS)
                    time.sleep(random.uniform(0.5, 1.5))
                
                response = session.get(url, headers=headers, timeout=20, allow_redirects=True)
                response.encoding = response.apparent_encoding or 'utf-8'
                
                if _http_client._is_blocked(response):
                    print(f"⚠️ Blocked (attempt {attempt + 1})", flush=True)
                    continue
                
                if response.status_code != 200:
                    print(f"⚠️ HTTP {response.status_code} (attempt {attempt + 1})", flush=True)
                    continue
                
                # Validate content has actual articles
                if len(response.text) < 1000:
                    print(f"⚠️ Empty page (attempt {attempt + 1})", flush=True)
                    continue
                
                return BeautifulSoup(response.text, 'html.parser')
                
            finally:
                _http_client._return_session(session)
        except Exception as e:
            print(f"⚠️ Page fetch error: {e} (attempt {attempt + 1})", flush=True)
    
    return None


def _extract_articles(soup) -> List[Dict]:
    """Extract search result articles from a page"""
    # Try multiple selectors for different page layouts
    articles = soup.find_all('article', limit=30)
    if not articles:
        articles = soup.find_all('div', class_='post-item', limit=30)
    if not articles:
        articles = soup.find_all('div', class_=re.compile(r'post|item|result', re.I), limit=30)
    
    results = []
    seen = set()
    
    for article in articles:
        try:
            result = parse_search_article(article)
            if result and result['url'] not in seen:
                seen.add(result['url'])
                results.append(result)
        except:
            continue
    
    return results


def _get_next_page_url(soup) -> Optional[str]:
    """Extract next page URL from pagination"""
    # Method 1: <a class="next page-numbers">
    next_link = soup.find('a', class_='next')
    if next_link and next_link.get('href'):
        return next_link['href']
    
    # Method 2: "Next" text link
    for a in soup.find_all('a', class_='page-numbers'):
        if 'next' in a.get_text().lower():
            return a.get('href')
    
    # Method 3: numbered page links — get the next number
    page_links = soup.find_all('a', class_='page-numbers')
    current = soup.find('span', class_='page-numbers current')
    if current and page_links:
        current_num = int(re.search(r'\d+', current.get_text()).group()) if re.search(r'\d+', current.get_text()) else 1
        for link in page_links:
            num_match = re.search(r'\d+', link.get_text())
            if num_match and int(num_match.group()) == current_num + 1:
                return link.get('href')
    
    return None


def _build_query_variants(query: str):
    """
    Generate smart query variants in priority order.
    e.g. "Spider-Man Animated Series Season 2 1080p"
      → ["Spider-Man Animated Series Season 2 1080p",  (original)
         "Spider-Man Animated Series",                  (strip quality+season)
         "Spider-Man Animated",                         (first 3 words)
         "Spider-Man"]                                  (first 2 words)
    """
    import re as _re
    q = query.strip()
    variants = [q]

    # Strip quality tags (1080p, 720p, 4k etc)
    q_no_quality = _re.sub(r'\b(480p|720p|1080p|2160p|4k|uhd|hd|hdcam)\b', '', q, flags=_re.I).strip()

    # Strip Season/Episode suffixes
    q_no_season = _re.sub(
        r'\b(season\s*\d+|s\d{1,2}|episode\s*\d+|e\d{1,3}|complete|series|collection|dual audio|hindi|english|tamil|telugu)\b',
        '', q_no_quality, flags=_re.I
    ).strip()
    q_no_season = _re.sub(r'\s+', ' ', q_no_season).strip()

    if q_no_season and q_no_season.lower() != q.lower():
        variants.append(q_no_season)

    # First 3 words
    words = q_no_season.split()
    if len(words) > 3:
        variants.append(' '.join(words[:3]))
    if len(words) > 2:
        variants.append(' '.join(words[:2]))

    # De-dupe, preserve order
    seen = set()
    unique = []
    for v in variants:
        vl = v.lower()
        if vl not in seen and len(v) > 1:
            seen.add(vl)
            unique.append(v)
    return unique


def _run_search_pages(query: str, limit: int, seen_urls: set, results: list):
    """Fetch up to 3 pages for a given query string and append to results."""
    domain = _http_client._working_domain or BOLLYFLIX_BASE_URL
    if not _http_client._working_domain:
        _http_client._find_working_domain()
        domain = _http_client._working_domain or BOLLYFLIX_BASE_URL

    search_url = f"{domain.rstrip('/')}/?s={quote_plus(query)}"
    current_url = search_url

    for page_num in range(1, 4):  # up to 3 pages
        soup = _search_single_page(current_url)

        if not soup:
            if page_num == 1:
                # Try domain rotation once
                _http_client._working_domain = None
                new_domain = _http_client._find_working_domain()
                current_url = f"{new_domain.rstrip('/')}/?s={quote_plus(query)}"
                soup = _search_single_page(current_url)
                if not soup:
                    break
            else:
                break

        page_results = _extract_articles(soup)
        for r in page_results:
            if r['url'] not in seen_urls:
                seen_urls.add(r['url'])
                results.append(r)

        if len(results) >= limit:
            break

        next_url = _get_next_page_url(soup)
        if not next_url:
            break
        current_url = next_url
        # No artificial sleep — the HTTP round-trip is already a natural delay


def search_bollyflix(query: str, limit: int = MAX_SEARCH_RESULTS) -> List[Dict]:
    """
    Search BollyFlix with DEEP SEARCH:
    - Smart query cleaning + keyword fallback chain
    - Multi-page scraping (up to 3 pages per variant)
    - Cache with 30-minute TTL
    - Zero wasted sleep between pages
    """
    if not query or len(query.strip()) < 2:
        return []

    query = query.strip()
    cache_key = f"search:{query.lower()}:{limit}"

    cached = _search_cache.get(cache_key)
    if cached:
        print(f"📦 Cache hit: {query}", flush=True)
        return cached

    print(f"🔍 Deep Search: {query}", flush=True)

    all_results = []
    seen_urls = set()

    # Try each query variant until we get results
    variants = _build_query_variants(query)
    for attempt_num, variant in enumerate(variants):
        if attempt_num > 0:
            print(f"  🔄 Fallback query: '{variant}'", flush=True)

        _run_search_pages(variant, limit, seen_urls, all_results)

        if all_results:
            break  # Found results — no need for fallback queries

    # Trim to limit
    results = all_results[:limit]

    print(f"✅ Deep Search done: {len(results)} results for '{query}'", flush=True)

    if results:
        _search_cache.set(cache_key, results)

    return results



# =============================================================================
# SCRAPE FUNCTION
# =============================================================================

def scrape_content(url: str, poster: str = "") -> Optional[Dict]:
    if not url:
        return None
    
    cache_key = f"content:{generate_cache_key(url)}"
    
    cached = _content_cache.get(cache_key)
    if cached:
        print(f"📦 Cache hit: {url[:40]}...", flush=True)
        if poster and not cached.get('poster'):
            cached['poster'] = poster
        return cached
    
    print(f"📄 Scraping: {url[:50]}...", flush=True)
    
    response = _http_client.get(url)
    
    if not response:
        print(f"❌ Scrape failed", flush=True)
        return None
    
    if response.status_code != 200:
        print(f"❌ HTTP {response.status_code}", flush=True)
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    page_text = soup.get_text()
    
    content = {
        "url": url,
        "title": "",
        "clean_title": "",
        "year": "N/A",
        "genre": "N/A",
        "duration": "N/A",
        "rating": "7.5",
        "poster": poster,
        "is_series": False,
        "content_type": "movie",
        "download_links": {},
        "seasons": {},
        "qualities": [],
    }
    
    title_tag = soup.find('h1', class_='entry-title') or soup.find('h1')
    if title_tag:
        content["title"] = title_tag.get_text().strip()
        content["clean_title"] = clean_title(content["title"])
    else:
        content["clean_title"] = "Unknown"
    
    if not content["poster"]:
        content["poster"] = PosterExtractor.extract_from_page(soup)
    
    content["year"] = extract_year(content["title"], page_text)
    content["rating"] = extract_rating(page_text, soup)
    content["genre"] = extract_genre(page_text)
    content["duration"] = extract_duration(page_text)
    
    content["content_type"] = detect_content_type(content["title"], page_text)
    content["is_series"] = (content["content_type"] in ("series", "anime"))
    
    if content["is_series"]:
        content["seasons"] = extract_series_links(soup, page_text)
        all_qualities = set()
        for season_data in content["seasons"].values():
            all_qualities.update(season_data.keys())
        content["qualities"] = sort_qualities(list(all_qualities))
        print(f"📺 Series: {len(content['seasons'])} seasons", flush=True)
    else:
        content["download_links"] = extract_movie_links(soup, page_text)
        content["qualities"] = sort_qualities(list(content["download_links"].keys()))
        print(f"🎬 Movie: {len(content['qualities'])} qualities", flush=True)
    
    if not content["qualities"]:
        content["qualities"] = ["720p"]
        if not content["is_series"]:
            content["download_links"]["720p"] = url
    
    print(f"✅ Scraped: {content['clean_title']}", flush=True)
    
    _content_cache.set(cache_key, content)
    
    return content


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_seasons_list(seasons_data: Dict) -> List[str]:
    if not seasons_data:
        return []
    return sorted(seasons_data.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)


def search_batch(queries: List[str], limit: int = 5, max_workers: int = 5) -> Dict[str, List[Dict]]:
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(search_bollyflix, q, limit): q for q in queries}
        for future in as_completed(futures):
            query = futures[future]
            try:
                results[query] = future.result()
            except Exception as e:
                print(f"❌ Batch error for '{query}': {e}", flush=True)
                results[query] = []
    return results


def scrape_batch(urls: List[str], max_workers: int = 5) -> Dict[str, Optional[Dict]]:
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scrape_content, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except Exception as e:
                print(f"❌ Batch error: {e}", flush=True)
                results[url] = None
    return results


def warmup_pool():
    print("🔥 Warming up...", flush=True)
    _http_client._find_working_domain()
    print("✅ Warmup complete", flush=True)


def cleanup():
    print("🧹 Cleanup...", flush=True)
    _http_client.close()
    _search_cache.clear()
    _content_cache.clear()
    print("✅ Cleanup done", flush=True)


def get_scraper_stats() -> Dict:
    return {
        "http": _http_client.stats(),
        "search_cache": _search_cache.stats(),
        "content_cache": _content_cache.stats()
    }


def print_stats():
    stats = get_scraper_stats()
    print(f"\n📊 Stats: {stats}", flush=True)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'search_bollyflix',
    'scrape_content',
    'get_seasons_list',
    'search_batch',
    'scrape_batch',
    'warmup_pool',
    'cleanup',
    'get_scraper_stats',
    'print_stats',
    'SearchResult',
    'ContentInfo',
    'extract_movie_links',
    'extract_series_links',
]

print("✅ Scraper module loaded!", flush=True)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 50, flush=True)
    print("🚀 SCRAPER TEST", flush=True)
    print("=" * 50, flush=True)
    
    warmup_pool()
    
    print("\n🔍 Testing search...", flush=True)
    results = search_bollyflix("pushpa", limit=5)
    print(f"Found: {len(results)} results", flush=True)
    
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['clean_title']}", flush=True)
    
    if results:
        print("\n📄 Testing scrape...", flush=True)
        content = scrape_content(results[0]['url'])
        if content:
            print(f"Title: {content['clean_title']}", flush=True)
            print(f"Qualities: {content['qualities']}", flush=True)
    
    print_stats()
    cleanup()
    print("\n✅ Test complete!", flush=True)