from google import genai
from config import GEMINI_API_KEY
from logger import get_logger
import os
import json
from pydantic import BaseModel, Field

import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = get_logger(__name__)

# 定義 Gemini 結構化輸出的 Pydantic Schema
class VocabularySchema(BaseModel):
    word: str = Field(description="英文單字")
    pos: str = Field(description="主要詞性 (例如: n., v., adj.)")
    pronunciation: str = Field(description="音標")
    definition: str = Field(description="釋義 (若有多種詞性請分行列出，例如：【動詞】：... \\n【名詞】：...)")
    example: str = Field(description="例句 (附中文翻譯)")

class ProverbSchema(BaseModel):
    text: str = Field(description="諺語 (英文或中文)")
    explanation: str = Field(description="解釋與由來")
    usage: str = Field(description="應用場景或如何與今日故事連結")

class DailyReportSchema(BaseModel):
    story: str = Field(description="你的商業故事主文 (包含標題、條列重點、hashtag)")
    vocabulary: VocabularySchema = Field(description="今日商務單字")
    proverb: ProverbSchema = Field(description="今日商業/處世諺語")

def get_system_prompt():
    base_prompt = """你是一位專業的資訊整理助理。請將以下定時抓取的原始資訊，整理成結構清楚、適合手機閱讀的繁體中文linkedin風格的文章。同時，你需要從這篇商業故事中提煉出一個核心的「商業英語單字」與一句契合故事主軸的「商業/處世諺語」。

排版原則 (僅針對 story 欄位)：
1. 給出清晰的核心標題
2. 每個點條列式整理 2~4 個重點摘要
3. 去除重複、雜訊或無意義字元
4. 結尾附上幾個hashtag"""

    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '統整格式模板.md')
    if os.path.exists(template_path):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read().strip()
            
            if template_content:
                base_prompt += f"\n\n以下是貼文的預期輸出格式參考 (請盡量依照此結構與風格生成文章)：\n\n=== 格式模板開始 ===\n{template_content}\n=== 格式模板結束 ==="
        except Exception as e:
            logger.error(f"讀取格式模板失敗: {e}")
            
    return base_prompt

@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    reraise=True
)
def _call_gemini_with_retry(client, full_prompt):
    """
    實際呼叫 API 的內部函數，若發生暫時性錯誤 (如 503) 會自動重試。
    """
    response = client.models.generate_content(
        model="gemini-3.6-flash", # 使用測試成功的 Gemini 模型
        contents=full_prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": DailyReportSchema,
            "temperature": 0.7,
        }
    )
    return response

def summarize_with_llm(company_data, metrics, recent_history=None):
    """
    呼叫 Gemini API 將抓取到的公司資訊與 metrics 進行統整，並產出單字與諺語
    """
    if not GEMINI_API_KEY:
        logger.error("未設定 GEMINI_API_KEY，無法呼叫 LLM 進行彙整")
        return None

    try:
        # Initialize Gemini SDK client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        comp_name = company_data.get('name', '未知公司')
        stock_id = company_data.get('stock_id', '未知代碼')
        market = company_data.get('market', '未知市場')
        industry = company_data.get('industry', '未知產業')
        capital = company_data.get('capital', '未知')
        
        user_content = f"【公司基本資訊】\n"
        user_content += f"名稱：{comp_name} ({stock_id} {market})\n"
        user_content += f"產業：{industry}\n"
        user_content += f"實收資本額：{capital}\n\n"
        
        user_content += "【搜尋到的相關情報】\n"
        user_content += f"- 護城河/競爭優勢：\n{metrics.get('moat', '無資料')}\n\n"
        user_content += f"- 創業故事/背景：\n{metrics.get('story', '無資料')}\n\n"
        user_content += f"- 產品/解決方案：\n{metrics.get('products', '無資料')}\n\n"
        user_content += f"- 深耕領域/發展方向：\n{metrics.get('fields', '無資料')}\n\n"
        user_content += f"- 面臨挑戰/風險：\n{metrics.get('challenges', '無資料')}\n\n"
        
        if recent_history:
            user_content += "【請避開以下近期已使用過的單字與諺語】\n"
            user_content += f"已用單字：{', '.join(recent_history.get('vocab', []))}\n"
            user_content += f"已用諺語：{', '.join(recent_history.get('proverb', []))}\n"
        
        logger.info(f"正在呼叫 Gemini 彙整 {comp_name} 的資料...")
        
        # Combine system prompt and user content
        full_prompt = f"{get_system_prompt()}\n\n{user_content}"
        
        # 呼叫重試機制
        response = _call_gemini_with_retry(client, full_prompt)
        
        # response.parsed returns the populated Pydantic object
        report: DailyReportSchema = response.parsed
        
        # Convert the Pydantic object to a standard dictionary to match existing formatter logic
        result_dict = report.model_dump()
        return result_dict
        
    except Exception as e:
        logger.error(f"呼叫 Gemini API 失敗 (或重試達上限): {e}")
        return None

class NewsItemSchema(BaseModel):
    rank: int = Field(description="排名 (1, 2, 3)")
    title: str = Field(description="精煉且吸引人的繁體中文商業標題")
    source_url: str = Field(description="該則新聞對應的原始連結")
    impact_reason: str = Field(description="用 1 句話（30 字以內）說明為何該事件具備重大商業影響力")
    summary: str = Field(description="80~130 字的精華脈絡摘要")

class TopNewsSchema(BaseModel):
    top_news: list[NewsItemSchema] = Field(description="精選出的 Top 3 新聞列表", min_length=3, max_length=3)

def select_top_news_with_llm(candidates):
    """
    呼叫 Gemini API 從候選名單中篩選出 Top 3 新聞，並生成短評及翻譯
    """
    if not GEMINI_API_KEY:
        logger.error("未設定 GEMINI_API_KEY，無法呼叫 LLM 進行新聞篩選")
        return None
        
    if not candidates:
        logger.warning("沒有候選新聞可供篩選")
        return None

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        system_prompt = (
            "你是一名兼具總體經濟與產業投資視野的「資深商業分析師與晨報主編」。\n"
            "你的任務是從輸入的今日候選新聞清單中，客觀評選出 3 則最關鍵、不可不知的重大商業事件，並提煉出結構扎實、脈絡清晰的精華摘要。\n\n"
            "【評選權重標準】\n"
            "1. 市場規模與資本流向：涉及巨額資本流動、央行政策、產業鏈核心異動者優先。\n"
            "2. 結構性變革：顛覆現有商業模式、重大法規更迭或關鍵技術落地者優先。\n"
            "3. 廣泛影響力：影響跨國市場或整體產業鏈，而非僅限單一小眾企業的日常營運。\n\n"
            "【負面排除條件（嚴禁選入）】\n"
            "- 單一企業的促銷宣傳、日常公關稿、贊助公告。\n"
            "- 演藝娛樂、消費性產品微小版本更新、獵奇社會新聞。\n"
            "- 彼此重覆的同一個新聞事件（若有多家報導同一事件，僅挑選最具代表性的一則）。\n\n"
            "【輸出原則】\n"
            "- 語言：統一輸出為繁體中文（台灣習慣用語，如「伺服器」、「演算法」、「半導體」）。若輸入為英文，請忠實轉換為專業流暢的中文表達。\n"
            "- 事實約束：摘要必須 100% 基於候選文本所提及的事實，嚴禁杜撰未提供的具體財務數據或官方決策。"
        )
        
        news_text_list = ""
        for idx, item in enumerate(candidates):
            news_text_list += f"[{idx+1}] 來源：{item['source']}\n標題：{item['title']}\n摘要：{item['summary']}\n連結：{item['link']}\n\n"
            
        user_content = (
            "以下是自各大財經與科技媒體收集到的今日候選新聞列表：\n\n"
            f"{news_text_list}\n"
            "請仔細審視上述候選清單，執行以下動作：\n"
            "1. 依據系統指令的權重標準，選出今日最具商業影響力的 Top 3 重大事件（排序 1 至 3）。\n"
            "2. 每則新聞輸出指定的 JSON 結構（rank, title, source_url, impact_reason, summary）。"
        )
        
        logger.info(f"正在呼叫 Gemini 篩選 Top 3 新聞 (候選數量: {len(candidates)})...")
        
        full_prompt = f"{system_prompt}\n\n{user_content}"
        
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=full_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": TopNewsSchema,
                "temperature": 0.5,
            }
        )
        
        report: TopNewsSchema = response.parsed
        return report.model_dump()
        
    except Exception as e:
        logger.error(f"呼叫 Gemini 篩選新聞失敗: {e}")
        return None
