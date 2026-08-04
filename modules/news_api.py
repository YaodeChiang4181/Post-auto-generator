import requests
from config import TAVILY_API_KEY
from logger import get_logger

logger = get_logger(__name__)

def fetch_company_news(company_name):
    """
    使用 Tavily API 抓取該公司最新商業新聞
    """
    if not TAVILY_API_KEY:
        return "無最新新聞資料 (API Key 未設定)"

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": f"{company_name} 最新商業新聞 發展動態",
        "search_depth": "basic",
        "max_results": 3
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if not results:
            return "無相關新聞"
            
        news_summaries = []
        for res in results:
            title = res.get('title', '無標題')
            content = res.get('content', '')
            url = res.get('url', '')
            
            content_clean = content.replace('\n', ' ').strip()
            # 放寬字數限制到 250 字
            if len(content_clean) > 250:
                content_clean = content_clean[:250] + "..."
            
            news_summaries.append(f"🔹 【{title}】\n   {content_clean}\n   🔗 連結：{url}")
            
        return "\n\n".join(news_summaries)
    except Exception as e:
        logger.error(f"Error fetching news for {company_name}: {e}")
        return f"新聞抓取失敗"

def fetch_company_story(company_name):
    """
    使用 Tavily API 抓取公司的商業模式或品牌故事
    """
    if not TAVILY_API_KEY:
        return "無故事資料"

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": f"{company_name} 商業模式 品牌故事 發展歷史",
        "search_depth": "basic",
        "max_results": 1
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if not results:
            return "無相關故事"
            
        content = results[0].get('content', '')
        url = results[0].get('url', '')
        content_clean = content.replace('\n', ' ').strip()
        if len(content_clean) > 300:
            content_clean = content_clean[:300] + "..."
            
        return f"{content_clean}\n   🔗 來源連結：{url}"
    except Exception as e:
        logger.error(f"Error fetching story for {company_name}: {e}")
        return f"故事抓取失敗"
