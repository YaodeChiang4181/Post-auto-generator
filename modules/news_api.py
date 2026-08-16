import requests
import concurrent.futures
from datetime import datetime
from config import TAVILY_API_KEY
from logger import get_logger

logger = get_logger(__name__)

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
            url = res.get('url', '')
            if len(content) > 150:
                content = content[:150] + "..."
            
            snippet_text = f"- {content}"
            if url:
                snippet_text += f"\n  🔗 連結: {url}"
            snippets.append(snippet_text)
        
        return "\n".join(snippets)
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
    
    # 建立搜尋任務
    queries = {
        "moat": f"{comp_name} 護城河 規模經濟 競爭優勢",
        "story": f"{comp_name} 創業故事 背景 董事長創業故事 公司起源",
        "products": f"{comp_name} 主要產品 服務 解決方案",
        "fields": f"{comp_name} 深耕領域 核心事業 發展方向",
        "challenges": f"{comp_name} 困境 未來挑戰 面臨風險"
    }

    results = {}
    
    # 使用 ThreadPool 平行搜尋以節省時間
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_key = {}
        for key, query in queries.items():
            future = executor.submit(_search_tavily, query, 2, None)
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
