"""
=============================================================================
BOLLYFLIX BOT - ENI's ULTRA BYPASS SYSTEM
=============================================================================
Advanced bypass system for OzoLinks, FastDL, GDFlix with:
- Timer Nuke (10 sec bypass vs 30-60 sec normal)
- Chain Extraction (OzoLinks → FastDL → GDFlix → Telegram)
- Telegram File Intercept (via Pyrogram userbot)
- Caching & Retry Logic

Compatible with Chrome 144+
=============================================================================
"""

import os
import re
import json
import time
import base64
import asyncio
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from config import (
    API_ID, API_HASH, SESSION_NAME,
    DATABASE_CHANNEL_ID,
    BYPASS_TIMEOUT, BOT_RESPONSE_TIMEOUT,
    MAX_RETRIES, RETRY_DELAY
)
from logger import (
    log_info, log_error, log_success,
    log_warning, log_working, log_waiting,
    log_bypass
)
from helpers import get_chrome_path, format_size, generate_cache_key, extract_tg_from_fastdl, extract_tg_from_fxlinks
from database import db


# =============================================================================
# CHECK AVAILABLE MODULES
# =============================================================================

UC_AVAILABLE = False
uc = None
By = None
WebDriverWait = None
EC = None

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    UC_AVAILABLE = True
    log_success("undetected_chromedriver loaded")
except ImportError:
    log_warning("undetected_chromedriver not installed - browser bypass disabled")

PYROGRAM_AVAILABLE = False
Client = None
FloodWait = None

try:
    from pyrogram import Client
    from pyrogram.errors import FloodWait
    PYROGRAM_AVAILABLE = True
    log_success("pyrogram loaded")
except ImportError:
    log_warning("pyrogram not installed - Telegram intercept disabled")


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class BypassResult:
    """Result of bypass operation"""
    success: bool = False
    original_url: str = ""
    fastdl_url: Optional[str] = None
    gdflix_url: Optional[str] = None
    telegram_link: Optional[str] = None
    final_url: Optional[str] = None
    file_info: Optional[Dict] = None
    bypass_time: float = 0.0
    stage_reached: str = "none"
    error: Optional[str] = None
    from_cache: bool = False
    
    @property
    def best_url(self) -> Optional[str]:
        return (
            self.telegram_link or
            self.gdflix_url or
            self.fastdl_url or
            self.final_url
        )


@dataclass
class FileInfo:
    """Intercepted file information"""
    file_id: str = ""
    file_name: str = ""
    file_size: int = 0
    file_type: str = ""
    message_id: int = 0
    chat_id: int = 0
    message: Any = None
    
    @property
    def size_human(self) -> str:
        return format_size(self.file_size)


# =============================================================================
# BROWSER MANAGER (Chrome 144 Compatible)
# =============================================================================

class BrowserManager:
    """Manage Chrome/Chromium browser instances - Chrome 144 compatible"""
    
    def __init__(self):
        self.driver = None
    
    def create(self, headless: bool = True) -> Optional[Any]:
        """Create new browser instance"""
        if not UC_AVAILABLE:
            log_error("Chrome driver not available!")
            return None
        
        try:
            options = uc.ChromeOptions()
            
            chrome_path = get_chrome_path()
            if chrome_path:
                options.binary_location = chrome_path
                log_info(f"Using Chrome: {chrome_path}")
            
            if headless:
                options.add_argument('--headless=new')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-infobars')
            options.add_argument('--blink-settings=imagesEnabled=false')
            options.add_argument('--disable-javascript-harmony-shipping')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/144.0.0.0 Safari/537.36'
            )
            
            # Chrome 144 specific
            self.driver = uc.Chrome(options=options, version_main=144)
            return self.driver
            
        except Exception as e:
            log_error(f"Browser creation failed: {e}")
            return None
    
    def close(self):
        """Close browser instance"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            finally:
                self.driver = None
    
    def __enter__(self):
        return self.create()
    
    def __exit__(self, *args):
        self.close()


# =============================================================================
# STAGE 1: OZOLINKS NUKER (Working Version from Bot)
# =============================================================================

class OzolinksNuker:
    """
    OzoLinks Bypass using Timer Nuke + LocalStorage Extract
    Speed: ~10 seconds (vs 30-60 seconds normal)
    """
    
    def __init__(self):
        self.driver = None
    
    def _create_browser(self):
        """Create stealth browser instance"""
        if not UC_AVAILABLE:
            return None
        
        options = uc.ChromeOptions()
        
        chrome_path = get_chrome_path()
        if chrome_path:
            options.binary_location = chrome_path
            log_info(f"Using Chrome: {chrome_path}")
        
        # Speed optimizations
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--blink-settings=imagesEnabled=false')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-notifications')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36')
        
        try:
            return uc.Chrome(options=options, version_main=144)
        except Exception as e:
            log_error(f"Browser creation failed: {e}")
            return None
    
    def bypass(self, url: str, timeout: int = BYPASS_TIMEOUT) -> Optional[str]:
        """Bypass OzoLinks and return FastDL/GDFlix URL"""
        if not UC_AVAILABLE:
            log_error("Chrome driver not available!")
            return None
        
        start_time = time.time()
        log_bypass("STAGE 1: OzoLinks Bypass (Timer Nuke)")
        log_info(f"URL: {url[:60]}...")
        
        try:
            self.driver = self._create_browser()
            if not self.driver:
                return None
            
            # Load page
            log_waiting("Loading OzoLinks page...")
            self.driver.get(url)
            time.sleep(0.5)
            
            # Wait for redirect
            for _ in range(30):
                current = self.driver.current_url
                if "ozolinks" not in current.lower() and "ouo" not in current.lower():
                    log_info(f"Redirected to: {current[:50]}...")
                    if self._is_target_url(current):
                        return current
                    break
                time.sleep(0.1)
            
            # TIMER NUKE - The magic! (Working JavaScript)
            log_working("🔥 NUKING TIMER...")
            try:
                self.driver.execute_script("""
                    // Kill all timers instantly
                    for(var i=1; i<99999; i++) {
                        try { clearInterval(i); } catch(e) {}
                        try { clearTimeout(i); } catch(e) {}
                    }
                    
                    // Force timer variables to 0
                    var timerVars = ['countdown', 'timer', 'seconds', 'timeLeft', 'count', 'sec', 'time'];
                    timerVars.forEach(function(v) {
                        try { window[v] = 0; } catch(e) {}
                        try { eval(v + ' = 0'); } catch(e) {}
                    });
                    
                    // Force generator functions
                    var genFuncs = ['wpsafegenerate', 'wpsafehuman', 'wpgenlink', 'generateLink', 'showLink', 'getLink'];
                    genFuncs.forEach(function(f) {
                        try { if(typeof window[f] === 'function') window[f](); } catch(e) {}
                    });
                    
                    // Click verification buttons
                    var btnTexts = ['continue', 'verify', 'get link', 'click here', 'proceed', 'i am human'];
                    document.querySelectorAll('button, a, input[type="button"], input[type="submit"], img').forEach(function(el) {
                        var text = (el.innerText || el.value || el.alt || '').toLowerCase();
                        btnTexts.forEach(function(t) {
                            if(text.indexOf(t) !== -1) {
                                try { el.click(); } catch(e) {}
                            }
                        });
                    });
                """)
            except Exception as e:
                log_warning(f"Timer nuke script warning: {e}")
            
            time.sleep(0.3)
            
            # Extract URL from localStorage
            log_waiting("Extracting from localStorage...")
            final_url = None
            
            max_attempts = int(timeout / 0.1)
            for attempt in range(max_attempts):
                # Method 1: soralinklite key (main method)
                try:
                    data = self.driver.execute_script("return localStorage.getItem('soralinklite');")
                    if data:
                        vault = json.loads(data)
                        for key in vault:
                            if isinstance(vault[key], dict) and 'link' in vault[key]:
                                final_url = base64.b64decode(vault[key]['link']).decode()
                                break
                        if final_url:
                            break
                except Exception as e:
                    if attempt == 0:
                        log_warning(f"localStorage parse: {e}")
                
                # Method 2: Check current URL
                if not final_url:
                    current = self.driver.current_url
                    if self._is_target_url(current):
                        final_url = current
                        break
                
                # Method 3: Check page links
                if not final_url:
                    try:
                        links = self.driver.execute_script("""
                            var l=[];
                            document.querySelectorAll('a').forEach(function(a){
                                if(a.href && (a.href.indexOf('fastdl')!==-1 || a.href.indexOf('gdflix')!==-1 || a.href.indexOf('hubcloud')!==-1 || a.href.indexOf('filepress')!==-1))
                                    l.push(a.href);
                            });
                            return l;
                        """)
                        if links and len(links) > 0:
                            final_url = links[0]
                            break
                    except:
                        pass
                
                # Re-nuke periodically
                if attempt % 20 == 0 and attempt > 0:
                    try:
                        self.driver.execute_script("""
                            for(var i=1; i<99999; i++) {
                                try { clearInterval(i); } catch(e) {}
                                try { clearTimeout(i); } catch(e) {}
                            }
                        """)
                    except:
                        pass
                
                time.sleep(0.1)
            
            elapsed = round(time.time() - start_time, 2)
            
            if final_url:
                log_success(f"Stage 1 complete in {elapsed}s")
                log_info(f"Got URL: {final_url[:60]}...")
                return final_url
            else:
                log_error(f"Failed to extract URL after {elapsed}s")
                return None
                
        except Exception as e:
            log_error(f"OzoLinks bypass error: {e}")
            return None
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    def _is_target_url(self, url: str) -> bool:
        """Check if URL is a target (FastDL, GDFlix, etc.)"""
        if not url:
            return False
        
        targets = ['fastdl', 'gdflix', 'hubcloud', 'filepress', 'hubdrive']
        url_lower = url.lower()
        
        return any(t in url_lower for t in targets)


# =============================================================================
# STAGE 2: CHAIN EXTRACTOR (Working Version from Bot)
# =============================================================================

class ChainExtractor:
    """Extract Telegram link from FastDL/GDFlix"""
    
    def __init__(self):
        self.driver = None
    
    def _create_browser(self):
        """Create stealth browser instance"""
        if not UC_AVAILABLE:
            return None
        
        options = uc.ChromeOptions()
        
        chrome_path = get_chrome_path()
        if chrome_path:
            options.binary_location = chrome_path
        
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--blink-settings=imagesEnabled=false')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36')
        
        try:
            return uc.Chrome(options=options, version_main=144)
        except Exception as e:
            log_error(f"Browser creation failed: {e}")
            return None
    
    def extract(self, url: str, timeout: int = BYPASS_TIMEOUT) -> Optional[str]:
        """Extract Telegram link from FastDL/GDFlix - INSTANT via HTTP (no browser needed)"""
        import requests as req
        
        start_time = time.time()
        log_bypass("STAGE 2: Extracting Telegram Link (Fast HTTP)")
        log_info(f"URL: {url[:60]}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            res = req.get(url, headers=headers, timeout=timeout)
            html = res.text
            telegram_link = None
            
            # Method 1: Find filesgram.site links (most common on GDFlix)
            fg_match = re.search(r'https?://filesgram\.site/[^\s"\'<>]+', html)
            if fg_match:
                raw_link = fg_match.group(0).replace('&amp;', '&')
                s = re.search(r'start=([^&]+)', raw_link)
                b = re.search(r'bot=([^&\s"\'<>]+)', raw_link)
                if s and b:
                    telegram_link = f"https://t.me/{b.group(1)}?start={s.group(1)}"
                else:
                    telegram_link = raw_link
            
            # Method 2: Find direct t.me links with start parameter
            if not telegram_link:
                tme_match = re.search(r'https?://t\.me/[^\s"\'<>]*start=[^\s"\'<>]+', html)
                if tme_match:
                    telegram_link = tme_match.group(0).replace('&amp;', '&')
            
            # Method 3: Find any t.me bot links
            if not telegram_link:
                tme_match = re.search(r'https?://t\.me/\w+bot\w*', html, re.IGNORECASE)
                if tme_match:
                    telegram_link = tme_match.group(0)
            
            elapsed = round(time.time() - start_time, 2)
            
            if telegram_link:
                log_success(f"Stage 2 complete in {elapsed}s")
                log_info(f"Telegram Link: {telegram_link}")
                return telegram_link
            else:
                log_warning(f"No Telegram link found in HTML after {elapsed}s")
                log_info("Falling back to browser extraction...")
                return self._browser_extract(url, timeout)
                
        except Exception as e:
            log_error(f"HTTP extraction failed: {e}")
            return self._browser_extract(url, timeout)
    
    def _browser_extract(self, url: str, timeout: int = BYPASS_TIMEOUT) -> Optional[str]:
        """Fallback: Browser-based Telegram link extraction (single attempt)"""
        if not UC_AVAILABLE:
            return None
        
        try:
            self.driver = self._create_browser()
            if not self.driver:
                return None
            
            self.driver.get(url)
            time.sleep(0.5)
            
            telegram_link = None
            try:
                links = self.driver.execute_script("""
                    var tg=[];
                    document.querySelectorAll('a').forEach(function(a){
                        if(a.href && a.href.indexOf('t.me') !== -1 && a.href.indexOf('start=') !== -1)
                            tg.push(a.href);
                        if(a.href && a.href.indexOf('filesgram.site') !== -1)
                            tg.push(a.href);
                    });
                    var html = document.body.innerHTML;
                    var pattern = /https?:\\/\\/t\\.me\\/[^"'\\s]+start=[^"'\\s]+/g;
                    var m = html.match(pattern);
                    if(m) { for(var i=0; i<m.length; i++) { tg.push(m[i]); } }
                    var unique = [];
                    for(var i=0; i<tg.length; i++) {
                        if(unique.indexOf(tg[i]) === -1) unique.push(tg[i]);
                    }
                    return unique;
                """)
                
                if links and len(links) > 0:
                    telegram_link = links[0]
                    if 'filesgram' in telegram_link.lower():
                        s = re.search(r'start=([^&]+)', telegram_link)
                        b = re.search(r'bot=([^&]+)', telegram_link)
                        if s and b:
                            telegram_link = f"https://t.me/{b.group(1)}?start={s.group(1)}"
            except Exception as e:
                log_warning(f"Browser scan error: {e}")
            
            return telegram_link
            
        except Exception as e:
            log_error(f"Browser extraction error: {e}")
            return None
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None


# =============================================================================
# STAGE 3: TELEGRAM INTERCEPTOR
# =============================================================================

class TelegramInterceptor:
    """Intercept files from Telegram bots using Pyrogram userbot"""
    
    def __init__(self):
        self.client: Optional[Any] = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Pyrogram client from saved session"""
        if not PYROGRAM_AVAILABLE:
            log_error("Pyrogram not installed!")
            return False
        
        if self.initialized and self.client:
            return True
        
        try:
            log_working("Initializing Telegram userbot...")
            
            # Try loading session from database (set via /login)
            session_string = None
            try:
                from login import get_active_session_string
                session_string = get_active_session_string()
            except ImportError:
                pass
            
            if session_string:
                # Use in-memory session from database
                self.client = Client(
                    "bollyflix_userbot",
                    api_id=int(API_ID) if API_ID else 0,
                    api_hash=API_HASH or "",
                    session_string=session_string
                )
            else:
                # Fallback to file-based session
                if not API_ID or not API_HASH:
                    log_warning("No session found. Use /login to set up.")
                    return False
                self.client = Client(
                    SESSION_NAME,
                    api_id=int(API_ID),
                    api_hash=API_HASH
                )
            
            await self.client.start()
            
            me = await self.client.get_me()
            log_success(f"Logged in as: {me.first_name} (@{me.username})")
            
            self.initialized = True
            return True
            
        except Exception as e:
            log_error(f"Telegram init error: {e}")
            return False
    
    async def intercept(
        self,
        telegram_link: str,
        timeout: int = BOT_RESPONSE_TIMEOUT
    ) -> Optional[FileInfo]:
        """Intercept file from Telegram bot"""
        if not await self.initialize():
            return None
        
        log_bypass("STAGE 3: Telegram File Intercept")
        
        match = re.search(r't\.me/([^/?]+)\?start=([^&\s]+)', telegram_link)
        if not match:
            log_error("Invalid Telegram link format!")
            return None
        
        bot_username = match.group(1)
        start_param = match.group(2)
        
        log_info(f"Bot: @{bot_username}")
        log_info(f"Param: {start_param[:30]}...")
        
        try:
            log_waiting(f"Sending /start to @{bot_username}...")
            await self.client.send_message(bot_username, f"/start {start_param}")
            
            log_waiting("Waiting for file...")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    async for msg in self.client.get_chat_history(bot_username, limit=5):
                        if msg.document or msg.video or msg.audio:
                            if msg.date:
                                msg_age = time.time() - msg.date.timestamp()
                                if msg_age < 120:
                                    file_info = self._extract_file_info(msg)
                                    if file_info:
                                        log_success("File intercepted!")
                                        return file_info
                
                except FloodWait as e:
                    log_warning(f"FloodWait: {e.value}s")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    log_warning(f"Error checking messages: {e}")
                
                await asyncio.sleep(2)
            
            log_error("Timeout waiting for file!")
            return None
            
        except Exception as e:
            log_error(f"Intercept error: {e}")
            return None
    
    def _extract_file_info(self, msg) -> Optional[FileInfo]:
        """Extract file info from Pyrogram message"""
        try:
            info = FileInfo(
                message_id=msg.id,
                chat_id=msg.chat.id,
                message=msg
            )
            
            if msg.document:
                info.file_type = 'document'
                info.file_name = msg.document.file_name or 'file'
                info.file_size = msg.document.file_size or 0
                info.file_id = msg.document.file_id
                
            elif msg.video:
                info.file_type = 'video'
                info.file_name = msg.video.file_name or 'video.mp4'
                info.file_size = msg.video.file_size or 0
                info.file_id = msg.video.file_id
                
            elif msg.audio:
                info.file_type = 'audio'
                info.file_name = msg.audio.file_name or 'audio.mp3'
                info.file_size = msg.audio.file_size or 0
                info.file_id = msg.audio.file_id
                
            else:
                return None
            
            log_info(f"File: {info.file_name} ({info.size_human})")
            return info
            
        except Exception as e:
            log_error(f"Extract file info error: {e}")
            return None
    
    async def forward_to_user(
        self,
        file_info: FileInfo,
        user_id: int,
        caption: str = None
    ) -> bool:
        """Forward file to user"""
        try:
            msg = file_info.message
            if not msg:
                return False
            
            if caption:
                await self.client.copy_message(
                    chat_id=user_id,
                    from_chat_id=msg.chat.id,
                    message_id=msg.id,
                    caption=caption
                )
            else:
                await self.client.forward_messages(
                    chat_id=user_id,
                    from_chat_id=msg.chat.id,
                    message_ids=msg.id
                )
            
            log_success(f"File sent to user {user_id}")
            return True
            
        except Exception as e:
            log_error(f"Forward error: {e}")
            return False
    
    async def save_to_database(self, file_info: FileInfo) -> bool:
        """Save file to database channel"""
        try:
            msg = file_info.message
            if not msg:
                return False
            
            await msg.forward(DATABASE_CHANNEL_ID)
            log_success("Saved to database channel!")
            return True
            
        except Exception as e:
            log_error(f"Database save error: {e}")
            return False
    
    async def close(self):
        """Close Pyrogram client"""
        if self.client:
            try:
                await self.client.stop()
            except:
                pass
            finally:
                self.client = None
                self.initialized = False


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

ozolinks_nuker = OzolinksNuker()
chain_extractor = ChainExtractor()
telegram_interceptor = TelegramInterceptor()


# =============================================================================
# MAIN BYPASS FUNCTION (Working Version from Bot)
# =============================================================================

def full_bypass(
    url: str,
    max_retries: int = MAX_RETRIES,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Full bypass with retry logic
    
    Args:
        url: Original download URL
        max_retries: Maximum retry attempts
        use_cache: Use cached results
    
    Returns:
        Dict with bypass result
    """
    result = {
        'success': False,
        'telegram_link': None,
        'gdflix_url': None,
        'fastdl_url': None,
        'final_url': None,
        'error': None,
        'bypass_time': 0.0,
        'from_cache': False,
        'stage_reached': 'none'
    }
    
    start_time = time.time()
    
    # Check cache first
    if use_cache:
        cache_key = generate_cache_key(url)
        cached = db.get_cache(cache_key)
        if cached:
            log_success("Cache hit! Using cached URL")
            result['success'] = True
            result['from_cache'] = True
            result['stage_reached'] = 'cache'
            
            if 't.me' in cached:
                result['telegram_link'] = cached
            elif 'gdflix' in cached.lower():
                result['gdflix_url'] = cached
            else:
                result['fastdl_url'] = cached
            
            result['final_url'] = cached
            return result
    
    # Retry loop
    for attempt in range(max_retries):
        log_info(f"Bypass attempt {attempt + 1}/{max_retries}")
        
        try:
            current_url = url
            url_lower = url.lower()
            
            # ── FAST PATH: fxlinks / fastdl / gdflix / hubcloud ──────────────
            # These URLs don't need Stage 1 (Ozolinks nuke) at all.
            # Go directly to Stage 2 HTTP extraction.
            if any(x in url_lower for x in ['fxlinks', 'fastdl', 'gdflix', 'hubcloud', 'filepress']):
                log_working("Direct URL detected — skipping to Stage 2 (Fast HTTP)...")
                
                tg_link = None
                if 'fxlinks' in url_lower:
                    # fxlinks → fastdlserver.life → filesgram → t.me
                    fastdl_url, tg_link = extract_tg_from_fxlinks(url)
                    if fastdl_url:
                        result['fastdl_url'] = fastdl_url
                        result['stage_reached'] = 'stage1'
                else:
                    # fastdl / gdflix / hubcloud direct → filesgram → t.me
                    tg_link = extract_tg_from_fastdl(url)
                    if 'gdflix' in url_lower:
                        result['gdflix_url'] = url
                    else:
                        result['fastdl_url'] = url
                    result['stage_reached'] = 'stage1'
                
                if tg_link:
                    result['telegram_link'] = tg_link
                    result['stage_reached'] = 'stage2'
                    result['success'] = True
                    result['final_url'] = tg_link
                    if use_cache:
                        db.set_cache(cache_key, tg_link)
                    break
                else:
                    # Fallback to fastdl/gdflix URL if TG extraction fails
                    fallback = result.get('fastdl_url') or result.get('gdflix_url') or url
                    result['success'] = True
                    result['final_url'] = fallback
                    if use_cache:
                        db.set_cache(cache_key, fallback)
                    break

            # ── STAGE 1: OzoLinks / ouo bypass ───────────────────────────────
            if 'ozolinks' in url_lower or 'ouo' in url_lower:
                log_working("Running Stage 1: OzoLinks Nuke...")
                
                fastdl = ozolinks_nuker.bypass(url)
                
                if fastdl:
                    result['fastdl_url'] = fastdl
                    result['stage_reached'] = 'stage1'
                    current_url = fastdl
                    
                    if 'gdflix' in fastdl.lower():
                        result['gdflix_url'] = fastdl
                else:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        result['error'] = "Stage 1 failed"
                        break
            
            # ── STAGE 2: Extract Telegram link ────────────────────────────────
            if 't.me' not in current_url.lower():
                log_working("Running Stage 2: Fast HTTP Extraction...")
                
                tg_link = None
                if 'fxlinks' in current_url.lower():
                    fastdl_extracted, tg_link = extract_tg_from_fxlinks(current_url)
                    if fastdl_extracted:
                        result['fastdl_url'] = fastdl_extracted
                else:
                    tg_link = extract_tg_from_fastdl(current_url)
                
                # Fallback to browser if HTTP fails
                if not tg_link:
                    log_info("HTTP extraction missed, trying browser fallback...")
                    tg_link = chain_extractor.extract(current_url)
                
                if tg_link:
                    result['telegram_link'] = tg_link
                    result['stage_reached'] = 'stage2'
                    result['success'] = True
                    result['final_url'] = tg_link
                    if use_cache:
                        db.set_cache(cache_key, tg_link)
                    break
                else:
                    # Return fastdl/gdflix as fallback
                    if result['gdflix_url'] or result['fastdl_url']:
                        result['success'] = True
                        result['final_url'] = result['gdflix_url'] or result['fastdl_url']
                        if use_cache:
                            db.set_cache(cache_key, result['final_url'])
                        break
            else:
                # URL is already a Telegram link
                result['telegram_link'] = current_url
                result['success'] = True
                result['final_url'] = current_url
                result['stage_reached'] = 'direct'
                break


        except Exception as e:
            result['error'] = str(e)
            log_error(f"Attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(0.5)
    
    result['bypass_time'] = round(time.time() - start_time, 2)
    
    if not result['success'] and not result['error']:
        result['error'] = "All bypass attempts failed"
    
    return result


def full_bypass_with_retry(url: str, max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
    """Alias for full_bypass (backward compatibility)"""
    return full_bypass(url, max_retries)


def bypass_ozolinks(url: str) -> Optional[str]:
    """Bypass OzoLinks only"""
    return ozolinks_nuker.bypass(url)


def extract_telegram_link(url: str) -> Optional[str]:
    """Extract Telegram link from FastDL/GDFlix"""
    return chain_extractor.extract(url)


def is_bypass_available() -> bool:
    """Check if bypass system is available"""
    return UC_AVAILABLE


def is_telegram_available() -> bool:
    """Check if Telegram intercept is available"""
    return PYROGRAM_AVAILABLE


def get_bypass_status() -> Dict[str, bool]:
    """Get status of bypass components"""
    return {
        'chrome_available': UC_AVAILABLE,
        'pyrogram_available': PYROGRAM_AVAILABLE,
        'bypass_ready': UC_AVAILABLE
    }


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BYPASS SYSTEM DEMO (Chrome 144 Compatible)")
    print("=" * 60)
    
    status = get_bypass_status()
    print(f"\n📊 System Status:")
    print(f"  Chrome: {'✅' if status['chrome_available'] else '❌'}")
    print(f"  Pyrogram: {'✅' if status['pyrogram_available'] else '❌'}")
    print(f"  Bypass Ready: {'✅' if status['bypass_ready'] else '❌'}")
    
    if not status['bypass_ready']:
        print("\n❌ Bypass system not available!")
        print("Install: pip install undetected-chromedriver")
    else:
        print("\n✅ Bypass system ready!")
        print("\nUsage:")
        print("  from bypass import full_bypass")
        print("  result = full_bypass('https://ozolinks.com/...')")
        print("  if result['success']:")
        print("      print(result['telegram_link'])")
    
    print(f"\n{'=' * 60}")