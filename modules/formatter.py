import os
import json
from modules.llm_api import summarize_with_llm
from config import DATA_DIR
from logger import get_logger

logger = get_logger(__name__)

def format_daily_report(company_data, metrics, recent_history=None):
    """
    將公司基本資料與搜尋結果透過 LLM 整理為結構化的每日報告。
    回傳 (post_draft, vocab_word, proverb_text)
    若 LLM 呼叫失敗，將回傳 (None, None, None)。
    """
    json_data = summarize_with_llm(company_data, metrics, recent_history)
    
    if not json_data:
        return None, None, None
        
    try:
        story = json_data.get("story", "")
        vocab = json_data.get("vocabulary", {})
        proverb = json_data.get("proverb", {})
        
        # 1. 產生 Telegram 版的 Markdown 內容
        markdown_content = f"{story}\n\n"
        markdown_content += f"💡 **【今日商務單字】**\n"
        markdown_content += f"🔹 **{vocab.get('word', '')}** ({vocab.get('pos', '')}) /{vocab.get('pronunciation', '')}/\n"
        markdown_content += f"👉 釋義：\n{vocab.get('definition', '')}\n\n"
        markdown_content += f"👉 例句：{vocab.get('example', '')}\n\n"
        markdown_content += f"📜 **【今日商業/處世諺語】**\n"
        markdown_content += f"🔹 **{proverb.get('text', '')}**\n"
        markdown_content += f"👉 解析：{proverb.get('explanation', '')}\n"
        markdown_content += f"👉 應用：{proverb.get('usage', '')}"
        
        # 2. 產生電子報版的 HTML 內容並存檔
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
                h2 {{ color: #2C3E50; }}
                .vocab-box, .proverb-box {{ background-color: #f9f9f9; border-left: 4px solid #3498db; padding: 15px; margin: 20px 0; }}
                .word {{ font-size: 1.2em; font-weight: bold; color: #e74c3c; }}
                .pronunciation {{ color: #7f8c8d; font-style: italic; }}
            </style>
        </head>
        <body>
            <div class="story">
                {story.replace(chr(10), '<br>')}
            </div>
            
            <div class="vocab-box">
                <h2>💡 今日商務單字</h2>
                <p><span class="word">{vocab.get('word', '')}</span> <span class="pronunciation">({vocab.get('pos', '')}) /{vocab.get('pronunciation', '')}/</span></p>
                <p>👉 <strong>釋義：</strong><br>{vocab.get('definition', '').replace(chr(10), '<br>')}</p>
                <p>👉 <strong>例句：</strong><br>{vocab.get('example', '').replace(chr(10), '<br>')}</p>
            </div>
            
            <div class="proverb-box">
                <h2>📜 今日商業/處世諺語</h2>
                <p><span class="word">{proverb.get('text', '')}</span></p>
                <p>👉 <strong>解析：</strong><br>{proverb.get('explanation', '').replace(chr(10), '<br>')}</p>
                <p>👉 <strong>應用：</strong><br>{proverb.get('usage', '').replace(chr(10), '<br>')}</p>
            </div>
        </body>
        </html>
        '''
        
        html_path = os.path.join(DATA_DIR, "latest_newsletter.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Generated HTML newsletter at {html_path}")
            
        return markdown_content, vocab.get('word', ''), proverb.get('text', '')
        
    except Exception as e:
        logger.error(f"Error parsing LLM JSON output: {e}")
        return None, None, None
