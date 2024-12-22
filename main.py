import os
import re
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import threading

##################################################
# User configurations
##################################################
BASE_URL = "https://www.cigarpage.com"
BRANDS_PAGE = f"{BASE_URL}/brands"

BRANDS_TO_SCRAPE = ["Drew Estate", "Arturo Fuente"]
HTML_DEBUG_DIR = "html_debug"
OUTPUT_JSON_DIR = "brand_data"

INITIAL_PAGE_LOAD_WAIT = 8
SCROLL_ATTEMPTS = 5
SCROLL_PAUSE_SEC = 3

# Limit concurrency to avoid resource overuse or detection
MAX_THREADS = 3

##################################################
# Selenium Utilities
##################################################
driver_init_lock = threading.Lock()

def create_driver():
    with driver_init_lock:
        chrome_options = Options()
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        )
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--lang=en-US")
        
        driver = uc.Chrome(options=chrome_options)
        return driver

def scroll_to_bottom(driver, pause_sec=2, max_attempts=3):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_attempts):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_sec)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

##################################################
# Scrape Functions
##################################################
def fetch_brands_page_html():
    driver = create_driver()
    try:
        driver.get(BRANDS_PAGE)
        time.sleep(INITIAL_PAGE_LOAD_WAIT)
        scroll_to_bottom(driver, pause_sec=SCROLL_PAUSE_SEC, max_attempts=SCROLL_ATTEMPTS)

        return driver.page_source
    finally:
        driver.quit()

def parse_brands(html_source):
    soup = BeautifulSoup(html_source, "html.parser")
    brand_links = []
    for a in soup.find_all("a", href=True):
        brand_text = a.get_text(strip=True)
        link_url = a["href"]
        if not brand_text:
            continue
        if "cigarpage.com" not in link_url and not link_url.startswith("/"):
            continue
        brand_links.append((brand_text, link_url))
    return brand_links

def fetch_brand_page_html(brand_url):
    driver = create_driver()
    try:
        if brand_url.startswith("/"):
            full_url = BASE_URL + brand_url
        else:
            full_url = brand_url

        driver.get(full_url)
        time.sleep(INITIAL_PAGE_LOAD_WAIT)
        scroll_to_bottom(driver, pause_sec=SCROLL_PAUSE_SEC, max_attempts=SCROLL_ATTEMPTS)

        return driver.page_source
    finally:
        driver.quit()

def parse_cigar_grid(html_source):
    soup = BeautifulSoup(html_source, "html.parser")
    table = soup.find("table", class_="cigar-grid")
    if not table:
        print("No cigar-grid table found on this page.")
        return []

    rows = table.find_all("tr")
    data = []
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 5:
            continue

        main_td = tds[0]
        pack_td = tds[1]
        stock_td = tds[2]
        price_td = tds[3]

        name_div = main_td.find("div", class_="cigar-alt-name")
        name = name_div.get_text(strip=True) if name_div else "N/A"

        pack = pack_td.get_text(strip=True) or "N/A"

        stock_span = stock_td.find("span", style="color:green")
        stock_status = stock_span.get_text(strip=True) if stock_span else "Out of Stock"

        price_span = price_td.find("span", class_="price")
        price = price_span.get_text(strip=True) if price_span else "N/A"

        msrp_div = price_td.find("div", class_="msrp")
        msrp = "N/A"
        if msrp_div:
            msrp_text = msrp_div.get_text(strip=True).replace("MSRP", "").strip()
            msrp = msrp_text

        data.append({
            "Name": name,
            "Pack": pack,
            "Stock Status": stock_status,
            "Price": price,
            "MSRP": msrp
        })
    return data

##################################################
# Thread Function
##################################################
def scrape_one_brand(page_brand_text, brand_url):
    """
    Each thread calls this:
      1) Create driver
      2) Load brand page
      3) Save brand-page HTML
      4) Parse data
      5) Write JSON immediately
    Return a small summary (brand_text, number_of_items)
    """
    brand_html = fetch_brand_page_html(brand_url)

    # Save debug HTML
    safe_brand = re.sub(r"\W+", "_", page_brand_text.lower())
    brand_html_path = os.path.join(HTML_DEBUG_DIR, f"{safe_brand}.html")
    with open(brand_html_path, "w", encoding="utf-8") as f:
        f.write(brand_html)
    print(f"[DEBUG] Saved brand page HTML for '{page_brand_text}' to {brand_html_path}")

    # Parse
    brand_data = parse_cigar_grid(brand_html)

    # Immediately write JSON
    out_path = os.path.join(OUTPUT_JSON_DIR, f"{safe_brand}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(brand_data, f, indent=2)
    print(f"[THREAD] Wrote {len(brand_data)} items to {out_path} for '{page_brand_text}'")

    # Return just summary
    return (page_brand_text, len(brand_data))

##################################################
# Main
##################################################
def main():
    os.makedirs(HTML_DEBUG_DIR, exist_ok=True)
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

    # 1) Grab the /brands page
    brands_html = fetch_brands_page_html()
    with open(os.path.join(HTML_DEBUG_DIR, "brands.html"), "w", encoding="utf-8") as f:
        f.write(brands_html)
    print("[DEBUG] Saved /brands HTML to brands.html")

    # 2) Parse brand links
    all_brand_links = parse_brands(brands_html)
    if not all_brand_links:
        print("No brand links found.")
        return

    # 3) Filter by partial brand name
    relevant_map = {}
    for brand_text, link_url in all_brand_links:
        brand_lower = brand_text.lower()
        for brand_needed in BRANDS_TO_SCRAPE:
            if brand_needed.lower() in brand_lower:
                relevant_map[brand_text] = link_url
                break

    if not relevant_map:
        print("No matching brand variations found.")
        return

    # 4) Multithread brand scraping
    from concurrent.futures import ThreadPoolExecutor, as_completed

    futures = []
    results = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for page_brand_text, brand_url in relevant_map.items():
            print(f"Submitting brand '{page_brand_text}' => {brand_url}")
            fut = executor.submit(scrape_one_brand, page_brand_text, brand_url)
            futures.append(fut)

        # Collect results
        for fut in as_completed(futures):
            (brand_text_done, count_items) = fut.result()
            results.append((brand_text_done, count_items))

    # 5) Final summary in main thread
    for brand_text_done, count_items in results:
        print(f"[DONE] Brand '{brand_text_done}' => {count_items} items.")


if __name__ == "__main__":
    main()
