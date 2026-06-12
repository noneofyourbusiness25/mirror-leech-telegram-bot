import requests
from bs4 import BeautifulSoup
import re
import time
import os
import json
import urllib.parse
from email.utils import formatdate

# --- Configuration ---
TARGET_SITE = "https://vegamovie.pe/"
FLARESOLVERR_API = "http://localhost:8191/v1"
SESSION_ID = "vegamovies_master"
CHECK_INTERVAL = 300  

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "scrapers")
os.makedirs(DATA_DIR, exist_ok=True)

def _file(filename):
    return os.path.join(DATA_DIR, filename)

print("🚀 Starting Vegamovies V3 (Isolated Episodic Memory & Hybrid Bypasser)...")

# Initialize a persistent browser session
try:
    requests.post(FLARESOLVERR_API, json={"cmd": "sessions.create", "session": SESSION_ID}, timeout=10)
except:
    pass

def fetch_html(url, delay=6000):
    try:
        payload = {"cmd": "request.get", "url": url, "maxTimeout": 60000, "delay": delay, "session": SESSION_ID}
        resp = requests.post(FLARESOLVERR_API, json=payload, timeout=65)
        data = resp.json()
        if data.get("status") == "ok":
            return data["solution"]
    except Exception as e:
        print(f"[!] FlareSolverr Error on {url}: {e}")
    return None

def is_under_4gb(text):
    match = re.search(r'(\d+(?:\.\d+)?)\s*(MB|GB)', text.upper())
    if match:
        size = float(match.group(1))
        unit = match.group(2)
        if unit == 'MB': return True
        if unit == 'GB' and size < 4.0: return True
    return False

def get_gatekeepers_from_hub(hub_url):
    print(f"   [*] Scanning Hub for episodes: {hub_url}")
    hub_solution = fetch_html(hub_url)
    gatekeepers = []
    if not hub_solution: return gatekeepers
    
    hub_soup = BeautifulSoup(hub_solution["response"], "html.parser")
    for a in hub_soup.find_all("a"):
        btn_text = a.text.lower()
        if "g-direct" in btn_text:
            href = a.get("href")
            if href and href not in gatekeepers:
                gatekeepers.append(href)
    
    print(f"   [*] Found {len(gatekeepers)} total episodes/links in Hub.")
    return gatekeepers

def bypass_cloudflare(gatekeeper_url):
    print(f"   [*] Picklocking Cloudflare: {gatekeeper_url}")
    gate_solution = fetch_html(gatekeeper_url, delay=8000)
    if not gate_solution: return gatekeeper_url
    
    gate_html = gate_solution["response"]
    gate_soup = BeautifulSoup(gate_html, "html.parser")
    
    form = gate_soup.find("form")
    if form:
        action = form.get("action", "")
        action_url = urllib.parse.urljoin(gatekeeper_url, action)
            
        inputs = form.find_all("input")
        post_data_dict = {inp.get("name"): inp.get("value", "") for inp in inputs if inp.get("name")}
            
        if post_data_dict:
            session = requests.Session()
            parsed_gate = urllib.parse.urlparse(gatekeeper_url)
            session.headers.update({
                "User-Agent": gate_solution["userAgent"],
                "Referer": gatekeeper_url,
                "Origin": f"{parsed_gate.scheme}://{parsed_gate.netloc}",
                "Content-Type": "application/x-www-form-urlencoded"
            })
            cookie_dict = {c["name"]: c["value"] for c in gate_solution["cookies"]}
            session.cookies.update(cookie_dict)
            
            try:
                post_resp = session.post(action_url, data=post_data_dict, allow_redirects=True, timeout=20)
                resolved_url = post_resp.url
                gate_html = post_resp.text
                gate_soup = BeautifulSoup(gate_html, "html.parser")
                
                if "googleusercontent.com" in resolved_url or "drive.google" in resolved_url:
                    return resolved_url
            except Exception as e:
                print(f"   [!] Native Python POST failed: {e}")

    for a in gate_soup.find_all("a"):
        href = a.get("href", "")
        if "googleusercontent.com" in href or "drive.google" in href:
            return href
            
        text = a.text.lower()
        if ("download" in text or "get link" in text) and "t.me" not in href:
            if href and "http" in href and "fast-dl" not in href:
                try:
                    if 'session' in locals():
                        final_resp = session.get(href, allow_redirects=True, timeout=15)
                        for fa in BeautifulSoup(final_resp.text, "html.parser").find_all("a"):
                            if "googleusercontent.com" in fa.get("href", ""): return fa.get("href")
                        return final_resp.url
                except:
                    pass
                
    return gatekeeper_url

def build_rss(items):
    xml = '<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n'
    xml += '<title>Vegamovies Auto Feed</title>\n<link>http://localhost</link>\n<description>Automated DDL Feed</description>\n'
    
    for item in items:
        xml += '<item>\n'
        xml += f'  <title>{item["title"]}</title>\n'
        xml += f'  <link>{item["link"]}</link>\n'
        xml += f'  <guid>{item["link"]}</guid>\n'
        xml += f'  <pubDate>{item["date"]}</pubDate>\n'
        xml += '</item>\n'
        
    xml += '</channel>\n</rss>'
    # ISOLATED FEED FILE
    with open(_file("vega_feed.xml"), "w", encoding="utf-8") as f:
        f.write(xml)

# Load databases - ISOLATED FILE NAMES
history_titles = set(open(_file("vega_history_titles.txt")).read().splitlines()) if os.path.exists(_file("vega_history_titles.txt")) else set()
history_gatekeepers = set(open(_file("vega_history_gatekeepers.txt")).read().splitlines()) if os.path.exists(_file("vega_history_gatekeepers.txt")) else set()
movies_db = json.load(open(_file("vega_db.json"))) if os.path.exists(_file("vega_db.json")) else []

while True:
    print(f"\n--- ⏰ Scanning Vegamovies Index: {time.ctime()} ---")
    feed_updated = False
    
    sol = fetch_html(TARGET_SITE)
    if sol:
        soup = BeautifulSoup(sol["response"], "html.parser")
        new_posts = []
        
        for a_tag in soup.select("h3 a"): 
            post_title = a_tag.text.strip()
            post_url = a_tag.get("href")
            
            if post_url and post_title not in history_titles:
                new_posts.append((post_title, post_url))
        
        if new_posts:
            print(f"[+] Found {len(new_posts)} new or updated posts! Processing...")
            
            for post_title, post_url in new_posts:
                print(f"[*] Analyzing: {post_title}")
                post_sol = fetch_html(post_url)
                post_soup = BeautifulSoup(post_sol["response"], "html.parser")
                
                target_hub_link = None
                
                for btn in post_soup.find_all("a"):
                    btn_text = btn.text.upper()
                    btn_href = btn.get("href", "")
                    if "CLICK HERE TO DOWNLOAD" in btn_text:
                        if is_under_4gb(btn_text):
                            if not target_hub_link or "1080P" in btn_text:
                                target_hub_link = btn_href
                
                if target_hub_link:
                    gatekeepers = get_gatekeepers_from_hub(target_hub_link)
                    
                    for gate_url in gatekeepers:
                        if gate_url not in history_gatekeepers:
                            final_link = bypass_cloudflare(gate_url)
                            
                            if final_link:
                                print(f"✅ Added to Feed: {final_link}")
                                movies_db.append({"title": post_title, "link": final_link, "date": formatdate(localtime=False)})
                                feed_updated = True
                                
                            history_gatekeepers.add(gate_url)
                            # ISOLATED GATEKEEPER MEMORY
                            with open(_file("vega_history_gatekeepers.txt"), "a") as f:
                                f.write(gate_url + "\n")
                                
                history_titles.add(post_title)
                # ISOLATED TITLE MEMORY
                with open(_file("vega_history_titles.txt"), "a") as f:
                    f.write(post_title + "\n")
                    
    if feed_updated:
        if len(movies_db) > 200: movies_db = movies_db[-200:]
        # ISOLATED DATABASE FILE
        with open(_file("vega_db.json"), "w") as f: json.dump(movies_db, f)
        build_rss(movies_db)
            
    print(f"💤 Standby mode active for 5 minutes...")
    time.sleep(CHECK_INTERVAL)

