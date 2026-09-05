import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import get_logger

logger = get_logger(__name__)

RSS_FEEDS = [
    {"name": "鉅亨網", "url": "https://rss.cnyes.com/news/cat/headline"},
    {"name": "科技新報", "url": "https://technews.tw/feed/"},
    {"name": "數位時代", "url": "https://www.bnext.com.tw/rss"},
    {"name": "BBC Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "Google News (財經)", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

TIMEOUT = 10
MAX_PER_SOURCE = 4

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return text[:200] + "..." if len(text) > 200 else text

def fetch_feed(source):
    results = []
    try:
        response = requests.get(source["url"], headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        
        now = datetime.now(timezone.utc)
        count = 0
        
        for entry in feed.entries:
            if count >= MAX_PER_SOURCE:
                break
                
            # Parse published time
            pub_time = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_time = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                
            if pub_time:
                # 過濾超過 24 小時的新聞
                if now - pub_time > timedelta(hours=24):
                    continue
            
            title = entry.get('title', '')
            link = entry.get('link', '')
            summary = entry.get('summary', '') or entry.get('description', '')
            clean_summary = clean_html(summary)
            
            if title and link:
                results.append({
                    "source": source["name"],
                    "title": title,
                    "summary": clean_summary,
                    "link": link
                })
                count += 1
                
        logger.info(f"Successfully fetched {count} news from {source['name']}")
    except Exception as e:
        logger.error(f"Failed to fetch {source['name']} ({source['url']}): {e}")
        
    return results

def get_daily_news_candidates():
    logger.info("Starting concurrent RSS fetching for news candidates...")
    candidates = []
    
    with ThreadPoolExecutor(max_workers=len(RSS_FEEDS)) as executor:
        future_to_source = {executor.submit(fetch_feed, source): source for source in RSS_FEEDS}
        for future in as_completed(future_to_source):
            try:
                data = future.result()
                candidates.extend(data)
            except Exception as e:
                logger.error(f"Thread execution failed: {e}")
                
    logger.info(f"Total {len(candidates)} news candidates fetched.")
    return candidates
