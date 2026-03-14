import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URLS = [
    "https://www.bestinsingapore.co/guide-to-kidsstop-singapore/",
    "https://www.bestinsingapore.co/best-cpap-singapore/",
    "https://www.bestinsingapore.co/best-bass-guitars-singapore/",
    "https://www.bestinsingapore.co/best-dish-racks-singapore/",
    "https://www.bestinsingapore.co/best-calligraphy-pens-singapore/",
]

OUTPUT_JSON = "selenium_scraped_pages.json"


def make_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,2200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=en-US")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def wait_for_page_ready(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def slow_scroll(driver, pause=1.0, max_rounds=20):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)


def get_visible_text(driver):
    script = """
    function isVisible(el) {
        const style = window.getComputedStyle(el);
        if (!style) return false;
        if (style.display === 'none' || style.visibility === 'hidden') return false;
        if (parseFloat(style.opacity) === 0) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    const tags = ['h1','h2','h3','h4','h5','h6','p','li','blockquote','figcaption','td','th','span','a'];
    const nodes = Array.from(document.body.querySelectorAll(tags.join(',')));

    const texts = [];
    const seen = new Set();

    for (const el of nodes) {
        if (!isVisible(el)) continue;
        const txt = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
        if (!txt) continue;
        if (txt.length < 2) continue;
        if (!seen.has(txt)) {
            seen.add(txt);
            texts.push(txt);
        }
    }
    return texts;
    """
    return driver.execute_script(script)


def get_instagram_embed_text(driver):
    texts = []

    selectors = [
        "blockquote.instagram-media",
        ".instagram-media",
        "iframe[title*='Instagram']",
        "iframe[src*='instagram.com']",
    ]

    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for el in elements:
            try:
                txt = (el.text or "").strip()
                if txt:
                    texts.append(txt)
            except Exception:
                pass

    # Try reading accessible iframe text when same-origin access is allowed
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for iframe in iframes:
        try:
            src = iframe.get_attribute("src") or ""
            title = iframe.get_attribute("title") or ""
            if "instagram" not in src.lower() and "instagram" not in title.lower():
                continue

            driver.switch_to.frame(iframe)
            body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
            if body_text:
                texts.append(body_text)
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()

    # Deduplicate
    out = []
    seen = set()
    for t in texts:
        t = " ".join(t.split())
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def get_instagram_images(driver):
    image_urls = []

    candidates = driver.find_elements(By.CSS_SELECTOR, "img")
    for img in candidates:
        try:
            src = img.get_attribute("src") or ""
            alt = img.get_attribute("alt") or ""
            if "instagram" in src.lower() or "instagram" in alt.lower():
                image_urls.append(src)
        except Exception:
            pass

    # deduplicate
    image_urls = [u for u in dict.fromkeys(image_urls) if u]
    return image_urls


def scrape_page(driver, url):
    driver.get(url)
    wait_for_page_ready(driver, timeout=25)

    # wait for body and possible content area
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    time.sleep(3)
    slow_scroll(driver, pause=1.2, max_rounds=15)
    time.sleep(2)

    title = driver.title
    page_text_blocks = get_visible_text(driver)
    instagram_text_blocks = get_instagram_embed_text(driver)
    instagram_images = get_instagram_images(driver)

    all_text_blocks = []
    seen = set()

    for block in page_text_blocks + instagram_text_blocks:
        block = " ".join(block.split())
        if block and block not in seen:
            seen.add(block)
            all_text_blocks.append(block)

    joined_text = "\n".join(all_text_blocks)

    return {
        "url": url,
        "title": title,
        "text_blocks": all_text_blocks,
        "full_text": joined_text,
        "instagram_text_blocks": instagram_text_blocks,
        "instagram_image_urls": instagram_images,
    }


def main():
    driver = make_driver(headless=True)
    results = []

    try:
        for url in URLS:
            print(f"Scraping: {url}")
            try:
                item = scrape_page(driver, url)
                results.append(item)
                print(f"  done, {len(item['text_blocks'])} text blocks")
            except Exception as e:
                print(f"  failed: {e}")
                results.append({
                    "url": url,
                    "error": str(e),
                })
    finally:
        driver.quit()

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Saved to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()