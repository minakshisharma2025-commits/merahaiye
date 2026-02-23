"""
Deep test: Simulate the EXACT bypass flow the bot does.
1. Test FastDL URLs (what Stage 1 actually returns)
2. Test GDFlix URLs
3. Test various URL patterns to find where the telegram link lives
"""
import requests
import re
import time

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
})

def test_url(url, label=""):
    print(f"\n{'='*60}")
    print(f"[TEST] {label}: {url}")
    print(f"{'='*60}")
    start = time.time()
    
    try:
        res = session.get(url, timeout=15, allow_redirects=True)
        elapsed = round(time.time() - start, 3)
        print(f"Status: {res.status_code} | Final URL: {res.url} | Time: {elapsed}s")
        print(f"Content Length: {len(res.text)} chars")
        
        html = res.text
        
        # Search for ALL possible telegram-related patterns
        patterns = {
            'filesgram.site': r'https?://filesgram\.site/[^\s"\'<>]+',
            't.me with start': r'https?://t\.me/[^\s"\'<>]*start=[^\s"\'<>]+',
            't.me any bot': r'https?://t\.me/\w+bot[^\s"\'<>]*',
            't.me any link': r'https?://t\.me/[^\s"\'<>]+',
            'gdflix link': r'https?://[^\s"\'<>]*gdflix[^\s"\'<>]*',
            'fastdl link': r'https?://[^\s"\'<>]*fastdl[^\s"\'<>]*',
            'hubcloud link': r'https?://[^\s"\'<>]*hubcloud[^\s"\'<>]*',
            'filepress link': r'https?://[^\s"\'<>]*filepress[^\s"\'<>]*',
        }
        
        found_any = False
        for name, pattern in patterns.items():
            matches = list(set(re.findall(pattern, html)))
            if matches:
                found_any = True
                for m in matches[:3]:
                    clean = m.replace('&amp;', '&')
                    print(f"  [{name}] -> {clean}")
        
        if not found_any:
            print("  [NONE] No telegram/filesgram/gdflix patterns found!")
            # Show snippet of page to understand what we got
            # Look for download buttons
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            buttons = []
            for el in soup.find_all(['a', 'button']):
                text = el.text.strip()[:50]
                href = el.get('href', '')[:80]
                if text and ('download' in text.lower() or 'telegram' in text.lower() or 'fast' in text.lower() or 'get' in text.lower() or 'file' in text.lower()):
                    buttons.append(f"    '{text}' -> {href}")
            if buttons:
                print("  Relevant buttons found:")
                for b in buttons:
                    print(b)
            else:
                # Show title and first few links
                title = soup.title.string if soup.title else 'No title'
                print(f"  Page title: {title}")
                links = soup.find_all('a')[:5]
                for l in links:
                    print(f"    Link: {l.get('href', '')[:80]}")
                    
    except Exception as e:
        print(f"  ERROR: {e}")

# Test 1: Direct GDFlix URL (we know this works)
test_url("https://new14.gdflix.net/file/AfAvrPS7xiLMQJvr1Tjy", "Direct GDFlix")

# Test 2: Common FastDL patterns the bot encounters
fastdl_patterns = [
    "https://fastdl.lol",
    "https://fastlinks.lol", 
    "https://hubcloud.lol",
]
for u in fastdl_patterns:
    test_url(u, "FastDL Base")

# Test 3: Let's also check what happens with a typical gdflix domain with different subdomain
test_url("https://new13.gdflix.net", "GDFlix Homepage")

# Test 4: Check fxlinks pattern (from helpers.py)
print("\n\n=== CHECKING HELPERS FOR ADDITIONAL EXTRACTION METHODS ===")
try:
    from helpers import extract_tg_from_fastdl, extract_tg_from_fxlinks
    print(f"extract_tg_from_fastdl available: {extract_tg_from_fastdl}")
    print(f"extract_tg_from_fxlinks available: {extract_tg_from_fxlinks}")
except Exception as e:
    print(f"Import error: {e}")
