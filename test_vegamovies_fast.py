import requests
import re

def fast_bypass_vegamovies(url):
    print(f"\n[*] Starting Instant Nuke on: {url}")
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://vegamovies.cologne/'
    }
    session.headers.update(headers)
    
    # Step 1: Get the hidden API URL from vcloud.zip
    try:
        res1 = session.get(url, timeout=10)
        match1 = re.search(r'var\s+url\s*=\s*[\'"](.*?)[\'"];', res1.text, re.IGNORECASE)
        if not match1:
            print("[-] Error: Could not find first API URL.")
            return
            
        api_url = match1.group(1)
        print(f"[+] Found API: {api_url}")
        
        # Step 2: Hit API, follow redirect to carnewz, get the final worker URL
        res2 = session.get(api_url, timeout=10)
        match2 = re.search(r'var\s+url\s*=\s*[\'"](https://.*?workers\.dev/.*?)[\'"];', res2.text, re.IGNORECASE)
        if not match2:
            # Maybe it uses a let or const
            match2 = re.search(r'(?:let|const)\s+url\s*=\s*[\'"](https://.*?workers\.dev/.*?)[\'"];', res2.text, re.IGNORECASE)
            
        if not match2:
            print("[-] Error: Could not find the final Cloudflare worker URL.")
            return
            
        worker_url = match2.group(1)
        print(f"[+] Found Final Worker: {worker_url}")
        
        # Step 3: Trigger the worker to get the direct download links
        print("[*] Hitting Worker to extract Direct Links...")
        res3 = session.get(worker_url, timeout=15)
        
        # The worker might return JSON, a direct file, or a page with PixelDrain links
        if res3.headers.get('Content-Type', '').startswith('application/json'):
            print(f"[+] Worker JSON: {res3.json()}")
        else:
            # Parse final HTML for direct links
            links = []
            for m in re.finditer(r'href=[\'"](https://(pixeldrain\.dev|.*?hubcdn.*?|.*?r2\.dev).*?)[\'"]', res3.text, re.IGNORECASE):
                links.append(m.group(1))
                
            if links:
                print("\n[SUCCESS] NUKE COMPLETE IN ~2 SECONDS!")
                print("Direct Links Extracted:")
                for l in set(links):
                    print(f" -> {l}")
            else:
                print(f"[?] Reached end but no recognized host links found. Final URL: {res3.url}")
                
    except Exception as e:
        print(f"[!] Exception during bypass: {e}")

if __name__ == "__main__":
    t_url = 'https://vcloud.zip/2a2waxgu001oqxy'
    fast_bypass_vegamovies(t_url)
