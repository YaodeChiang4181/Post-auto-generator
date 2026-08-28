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
    pos: str = Field(description="詞性 (例如: n., v., adj.)")
    pronunciation: str = Field(description="音標")
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
