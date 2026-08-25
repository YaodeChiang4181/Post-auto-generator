import requests
import concurrent.futures
from datetime import datetime
from config import TAVILY_API_KEY
from logger import get_logger
from bs4 import BeautifulSoup

logger = get_logger(__name__)

def _deep_crawl(url):
    """
    對指定 URL 進行二次深度爬取，抓取主要文字內容。
    特別處理 Telegraph 等長文平台，並將內容限制在合理範圍內以避免 LLM Context 溢出。
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 移除 script, style, header, footer, nav 等雜訊
        for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            element.decompose()
            
        # 針對 Telegraph 特製化抓取
        if 'telegra.ph' in url:
            article = soup.find('article')
            if article:
                text = article.get_text(separator='\n')
            else:
                text = soup.get_text(separator='\n')
        else:
            # 一般網頁抓取：嘗試抓取段落
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = '\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            else:
                text = soup.get_text(separator='\n')
                
        # 清理多餘空白與斷行
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # 避免文字太長，保留前 2000 字
        if len(text) > 2000:
            text = text[:2000] + "...(以下省略)"
            
        return text
    except Exception as e:
        logger.warning(f"深度爬取失敗 ({url}): {e}")
        return ""

def _search_tavily(query, max_results=2, days=None):
    """Helper function to call Tavily API"""
    if not TAVILY_API_KEY:
        return "API Key 未設定"

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
    }
    if days:
        payload["days"] = days

    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        if not results:
            return ""
            
        snippets = []
        for res in results:
            content = res.get('content', '').replace('\n', ' ').strip()
            res_url = res.get('url', '')
            
            # 外部連結與 Telegraph 二次深度爬取
            deep_content = ""
            if res_url:
                deep_content = _deep_crawl(res_url)
                
            # 若深度爬取有內容，優先使用；否則退回原本的 snippet (放寬字數限制)
            if deep_content:
                final_content = deep_content
            else:
                if len(content) > 500:
                    final_content = content[:500] + "..."
                else:
                    final_content = content
            
            snippet_text = f"【來源連結】: {res_url}\n{final_content}"
            snippets.append(snippet_text)
        
        # 連續訊息合併
        return "\n\n---\n\n".join(snippets)
    except Exception as e:
        logger.error(f"Tavily search failed for '{query}': {e}")
        return ""

def fetch_all_metrics(company):
    """
    針對 8 大指標進行多維度的 Tavily 搜尋。
    回傳一個 dict，包含所有指標的搜尋結果。
    """
    comp_name = company.get("name", "該公司")
    today = datetime.now().strftime("%Y年%m月")
    
    # 建立搜尋任務 (包含查詢字串, max_results, days時效性限制)
    queries_config = {
        "moat": (f"{comp_name} 護城河 規模經濟 競爭優勢", 3, None),
        "story": (f"{comp_name} 創業故事 背景 董事長創業故事 公司起源", 3, None),
        "products": (f"{comp_name} 近期 最新 主要產品 服務 解決方案", 4, 365), # 加強近期與數量
        "fields": (f"{comp_name} 深耕領域 核心事業 未來 發展方向", 3, 730), # 兩年內的發展方向
        "challenges": (f"{comp_name} 近期 困境 未來挑戰 面臨風險 危機", 4, 365) # 挑戰須具備強烈的時效性
    }

    results = {}
    
    # 使用 ThreadPool 平行搜尋以節省時間
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_key = {}
        for key, config in queries_config.items():
            query_str, max_res, days_limit = config
            future = executor.submit(_search_tavily, query_str, max_res, days_limit)
            future_to_key[future] = key

        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                res = future.result()
                results[key] = res if res else "[資料不足，需自主判斷]"
            except Exception as exc:
                logger.error(f"Search for {key} generated an exception: {exc}")
                results[key] = "[搜尋失敗，需自主判斷]"

    return results
