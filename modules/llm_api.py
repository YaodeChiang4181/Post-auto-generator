from groq import Groq
from config import GROQ_API_KEY
from logger import get_logger
import os

logger = get_logger(__name__)

def get_system_prompt():
    base_prompt = """你是一位專業的資訊整理助理。請將以下定時抓取的原始資訊，整理成結構清楚、適合手機閱讀的繁體中文linkedin風格的文章。

排版原則：
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

def summarize_with_llm(company_data, metrics):
    """
    呼叫 Groq API 將抓取到的公司資訊與 metrics 進行統整
    """
    if not GROQ_API_KEY:
        logger.error("未設定 GROQ_API_KEY，無法呼叫 LLM 進行彙整")
        return None

    try:
        client = Groq(api_key=GROQ_API_KEY)
        
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
        user_content += f"- 面臨挑戰/風險：\n{metrics.get('challenges', '無資料')}\n"
        
        logger.info(f"正在呼叫 Groq 彙整 {comp_name} 的資料...")
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": get_system_prompt(),
                },
                {
                    "role": "user",
                    "content": user_content,
                }
            ],
            model="openai/gpt-oss-20b", # Groq 最新的預設開源模型
            temperature=0.7,
        )
        
        result_text = response.choices[0].message.content
        return result_text
        
    except Exception as e:
        logger.error(f"呼叫 Groq API 失敗: {e}")
        return None
