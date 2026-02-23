import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_vegamovies_bypass(url):
    print(f"[*] Starting VegaMovies Bypass Test on: {url}")
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=144)
        print("[*] Browser initialized")
        
        # 1. Load vcloud.zip
        driver.get(url)
        print(f"[*] Loaded URL: {driver.current_url}")
        
        # Check if we are on vcloud.zip and need to click generate
        if "vcloud.zip" in driver.current_url:
            print("[*] On vcloud.zip, waiting for button...")
            try:
                # vcloud usually has a button like "Generate Download Link"
                btn = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'generate')] | //*[contains(@class, 'btn')]"))
                )
                print(f"[*] Found button: {btn.text}. Clicking...")
                btn.click()
            except Exception as e:
                print(f"[!] Could not find generate button on vcloud.zip: {e}")
        
        # Wait for redirect to carnewz.site or similar
        print("[*] Waiting for redirect...")
        time.sleep(5)
        print(f"[*] Current URL after redirect: {driver.current_url}")
        
        # Handle carnewz.site timer and buttons
        if "carnewz" in driver.current_url or "fastdl" in driver.current_url:
            print("[*] Reached intermediate gateway. Looking for continuation buttons...")
            # Try to find common "Click to get link", "Fast Download", "Click Here"
            main_window = driver.current_window_handle
            for attempts in range(30):
                try:
                    btns = driver.find_elements(By.TAG_NAME, "a") + driver.find_elements(By.TAG_NAME, "button")
                    clicked = False
                    for btn in btns:
                        text = btn.text.lower()
                        if "get link" in text or "fast server" in text or "continue" in text or "start verification" in text or "verify to continue" in text:
                            if btn.is_displayed():
                                print(f"[*] Found candidate button: {text}. Clicking...")
                                driver.execute_script("arguments[0].click();", btn)
                                clicked = True
                                time.sleep(3)
                                # Handle popup tabs
                                if len(driver.window_handles) > 1:
                                    for handle in driver.window_handles:
                                        if handle != main_window:
                                            driver.switch_to.window(handle)
                                            driver.close()
                                    driver.switch_to.window(main_window)
                                break
                    if clicked and "carnewz" not in driver.current_url:
                        break
                except Exception as e:
                    pass
                time.sleep(2)
        
        # Wait for final redirect
        print("[*] Waiting for final landing page...")
        time.sleep(10)
        
        # Switch to last tab in case of popups or open in new tab
        driver.switch_to.window(driver.window_handles[-1])
        print(f"[*] Final URL reached: {driver.current_url}")
        
        # Search for actual download links
        links = driver.find_elements(By.TAG_NAME, "a")
        found_links = []
        for link in links:
            href = link.get_attribute("href")
            if href and ("pixeldrain" in href or "r2.dev" in href or "hubcdn" in href or "cloud" in href or "drive" in href):
                found_links.append(href)
        
        if found_links:
            print("\n[SUCCESS] Successfully Bypassed VegaMovies!")
            print("Extracted Links:")
            for l in set(found_links):
                print(f"  -> {l}")
        else:
            print("[-] Reached final page but couldn't parse direct links. Check screenshot.")
            
        driver.save_screenshot("vegamovies_debug.png")
        print("[*] Saved debug screenshot to vegamovies_debug.png")
            
    except Exception as e:
        print(f"[ERROR] Bypass failed: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    test_vegamovies_bypass("https://vcloud.zip/_s_lwkgvg2bbi11")
