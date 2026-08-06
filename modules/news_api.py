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
    
    # 建立 8 個維度的搜尋任務
    queries = {
        "scale": f"{comp_name} 2024 營收 市值 員工人數",
        "influence": f"{comp_name} 台灣市占率 全球排名 主要客戶 合作夥伴",
        "hidden_champ": f"{comp_name} 隱形冠軍 核心技術 專利 關鍵零組件 龍頭",
        "founder": f"{comp_name} 董事長 創辦人 關鍵決策 轉型 理念",
        "survival": f"{comp_name} 創業初期 挑戰 虧損 轉虧為盈 突破困境",
        "moat": f"{comp_name} 規模經濟 進入障礙 客戶黏著度 品牌優勢",
        "monopoly": f"{comp_name} 獨家供應 技術門檻 難以複製 供應鏈關鍵",
        "crisis": f"{comp_name} 地緣政治 景氣循環 衝擊 危機 關稅 法規",
        # 額外的最新新聞
        "latest_news": f"{comp_name} {today} 最新新聞 發展動態"
    }

    results = {}
    
    # 使用 ThreadPool 平行搜尋以節省時間
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_key = {}
        for key, query in queries.items():
            # 最新新聞加上 days 限制 (例如過去 7 天)，其它則全域搜尋
            days_limit = 7 if key == "latest_news" else None
            future = executor.submit(_search_tavily, query, 2, days_limit)
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
