import requests
import re
from bs4 import BeautifulSoup

url = "https://fxlinks.rest/elinks/dex27390/"
print(f"[*] Fetching: {url}")

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    res = requests.get(url, headers=headers, timeout=15)
    print(f"Status codes: {res.status_code} | Final URL: {res.url}")
    
    html = res.text
    
    # Check what extract_tg_from_fxlinks regex looks for
    pat = re.compile(r'https?://fastdlserver\.life/?\?id=[^"\'\s]+', re.IGNORECASE)
    match = pat.search(html)
    print(f"[Regex Check] fastdlserver.life pattern 1: {match}")
    
    # Broaden search to ANY fastdl or gdflix or hubcloud link
    pat2 = re.compile(r'https?://(?:fastdl|gdflix|hubcloud|filepress)[^\s"\'<>]*', re.IGNORECASE)
    matches2 = pat2.findall(html)
    print(f"[Regex Check] Any target domain: {matches2}")
    
    # Try finding buttons
    soup = BeautifulSoup(html, 'html.parser')
    print("\n--- BUTTONS / LINKS ---")
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.text.strip()
        if href and not href.startswith('#') and 'fxlinks' not in href and 'telegram' not in href.lower() and 't.me' not in href:
            print(f" Link: '{text}' -> {href}")
            
except Exception as e:
    print(f"Error: {e}")
