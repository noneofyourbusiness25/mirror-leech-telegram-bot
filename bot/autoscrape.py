import requests
import re
import time
import os
import json
import urllib.parse
from email.utils import formatdate

# --- Configuration ---
TARGET_SITES = [
    "https://www.1tamilmv.cards/",
    "https://www.1tamilblasters.study/"
]
FLARESOLVERR_API = "http://localhost:8191/v1"
CHECK_INTERVAL = 300  

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "scrapers")
os.makedirs(DATA_DIR, exist_ok=True)

def _file(filename):
    return os.path.join(DATA_DIR, filename)

print("🚀 Starting Ultimate Multi-Site Auto-RSS Engine...")

def fetch_html(url):
    try:
        resp = requests.post(FLARESOLVERR_API, json={"cmd": "request.get", "url": url, "maxTimeout": 60000}, timeout=65)
        if resp.json().get("status") == "ok":
            return resp.json()["solution"]["response"]
    except Exception as e:
        pass
    return ""

def get_root_title(raw_title):
    # 1. Get the base name and year
    year_match = re.search(r'^(.*?\(\d{4}\))', raw_title)
    base_name = year_match.group(1) if year_match else re.split(r'[\[\-\(]', raw_title)[0]
    
    # 2. Add episode number if it's a series
    no_spaces = raw_title.replace(" ", "").upper()
    ep_match = re.search(r'(S\d+EP?\(?[\d\-]+\)?)', no_spaces)
    if ep_match: base_name += " " + ep_match.group(1)
    
    # 3. Clean special characters
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', base_name).lower()
    root = " ".join(clean.split())
    
    # 4. Extract Quality & Size to allow different versions!
    lower_raw = raw_title.lower()
    quality_tag = ""
    
    # Grab resolution if it exists
    res_match = re.search(r'(1080p|720p|480p|2160p|4k)', lower_raw)
    if res_match:
        quality_tag += " " + res_match.group(1)
        
    # Grab file size to catch versions without a resolution listed (like BR-Rips)
    size_match = re.search(r'(\d+(?:\.\d+)?\s*(?:mb|gb))', lower_raw)
    if size_match:
        quality_tag += " " + size_match.group(1).replace(" ", "")
        
    return root + quality_tag

def build_rss(items):
    xml = '<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0">\n<channel>\n'
    xml += '<title>Ultimate Multi-Site Auto Feed</title>\n<link>http://localhost</link>\n<description>Automated Feed with Duplicate Protection</description>\n'
    
    for item in reversed(items):
        xml += '<item>\n'
        xml += f'  <title>{item["title"]}</title>\n'
        xml += f'  <link>{item["magnet"]}</link>\n'
        xml += f'  <guid>{item["magnet"]}</guid>\n'
        xml += f'  <pubDate>{item["date"]}</pubDate>\n'
        xml += '</item>\n'
        
    xml += '</channel>\n</rss>'
    with open(_file("feed.xml"), "w", encoding="utf-8") as f:
        f.write(xml)

# --- Flood Protection Baseline Logic ---
if not os.path.exists(_file("history_urls.txt")):
    print("[*] First run detected. Creating a baseline index of BOTH sites to prevent bot flooding...")
    with open(_file("history_urls.txt"), "w") as f:
        for site in TARGET_SITES:
            html = fetch_html(site)
            if html:
                # Regex modified to catch both mv and blasters topic URLs dynamically
                topics = set(re.findall(r'https://www\.1tamil(?:mv|blasters)\.[a-z]+/index\.php\?/forums/topic/[^\s"\'><]+', html))
                for t in topics:
                    f.write(t + "\n")
    print("✅ Baseline established! Bot will only parse topics posted from this moment forward.")

# Load active state databases
history_urls = set(open(_file("history_urls.txt")).read().splitlines()) if os.path.exists(_file("history_urls.txt")) else set()
history_titles = set(open(_file("history_titles.txt")).read().splitlines()) if os.path.exists(_file("history_titles.txt")) else set()
magnets_db = json.load(open(_file("db.json"))) if os.path.exists(_file("db.json")) else []

while True:
    print(f"\n--- ⏰ Scanning Index: {time.ctime()} ---")
    feed_updated = False
    
    for site_url in TARGET_SITES:
        html = fetch_html(site_url)
        
        if html:
            topics = set(re.findall(r'https://www\.1tamil(?:mv|blasters)\.[a-z]+/index\.php\?/forums/topic/[^\s"\'><]+', html))
            new_topics = topics - history_urls
            
            if new_topics:
                print(f"[+] Found {len(new_topics)} new posts on {site_url}! Processing...")
                
                for topic in new_topics:
                    page_html = fetch_html(topic)
                    if not page_html:
                        continue
                    raw_magnets = set(re.findall(r'magnet:\?xt=urn:btih:[^\s"\'><]+', page_html))
                    
                    for mag in raw_magnets:
                        clean_mag = mag.replace("&amp;", "&")
                        
                        match = re.search(r'dn=([^&]+)', clean_mag)
                        title = urllib.parse.unquote_plus(match.group(1)) if match else "Unknown Release"
                        
                        # Clean out site names from the title tag
                        title = re.sub(r'www\.1Tamil(?:MV|Blasters)\.[a-z]+\s*-\s*', '', title, flags=re.IGNORECASE)
                        title_lower = title.lower()
                        
                        # Apply your custom 4K and Size Filters
                        if any(resolution in title_lower for resolution in ["4k", "2160p", "uhd"]):
                            print(f"⏩ Filtered Out (4K): {title}")
                            continue
                            
                        size_match = re.search(r'(\d+(?:\.\d+)?)\s*(gb|mb)', title_lower)
                        if size_match:
                            if size_match.group(2) == "gb" and float(size_match.group(1)) > 4.0:
                                print(f"⏩ Filtered Out (Oversized {size_match.group(1)}GB): {title}")
                                continue
                        
                        # Check the Cross-Site Duplicate Filter!
                        root_title = get_root_title(title)
                        
                        if root_title not in history_titles and root_title != "unknown release":
                            print(f"✅ Added to Feed: {title}")
                            magnets_db.append({"title": title, "magnet": clean_mag, "date": formatdate(localtime=False)})
                            feed_updated = True
                            
                            # Save to Title memory
                            history_titles.add(root_title)
                            with open(_file("history_titles.txt"), "a") as f:
                                f.write(root_title + "\n")
                        else:
                            print(f"🛑 Ignored Duplicate Across Sites: {title}")
                    
                    # Save the URL so we never open this thread again
                    history_urls.add(topic)
                    with open(_file("history_urls.txt"), "a") as f:
                        f.write(topic + "\n")
                
    if feed_updated:
        if len(magnets_db) > 100: 
            magnets_db = magnets_db[-100:]
        with open(_file("db.json"), "w") as f:
            json.dump(magnets_db, f)
        build_rss(magnets_db)
            
    print(f"💤 Standby mode active for 5 minutes...")
    time.sleep(CHECK_INTERVAL)
