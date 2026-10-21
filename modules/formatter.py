import os
import json
import re
from modules.llm_api import summarize_with_llm, regenerate_field_with_llm
from config import DATA_DIR
from logger import get_logger

logger = get_logger(__name__)

def format_daily_report(company_data, metrics, state_manager):
    """
    將公司基本資料與搜尋結果透過 LLM 整理為結構化的每日報告。
    回傳 (post_draft, vocab_word, proverb_text, german_word, json_data)
    若 LLM 呼叫失敗，將回傳 (None, None, None, None, None)。
    """
    recent_history = state_manager.get_recent_history(days=30)
    json_data = summarize_with_llm(company_data, metrics, recent_history)
    
    if not json_data:
        return None, None, None, None, None
        
    try:
        story = json_data.get("story", "")
        vocab = json_data.get("vocabulary", {})
        proverb = json_data.get("proverb", {})
        german = json_data.get("german_vocab", {})
        
        # 進行單字/諺語/德文重複檢測與受控重新生成 (Bounded Retry Loop, max 3 attempts)
        max_retries = 3

        # 1. 檢驗並重試英文單字 (Vocabulary)
        vocab_rejected = []
        for attempt in range(max_retries):
            current_word = vocab.get('word', '') if vocab else ''
            if current_word and state_manager.check_vocabulary_exists(current_word, 'vocab'):
                logger.info(f"Vocabulary '{current_word}' is a duplicate (attempt {attempt+1}/{max_retries}). Regenerating...")
                vocab_rejected.append(current_word)
                new_vocab = regenerate_field_with_llm('vocab', vocab_rejected, story)
                if new_vocab and new_vocab.get('word'):
                    vocab = new_vocab
                    json_data["vocabulary"] = new_vocab
                else:
                    logger.warning("Regenerating vocabulary returned empty result.")
                    break
            else:
                break

        # 2. 檢驗並重試商業諺語 (Proverb)
        proverb_rejected = []
        for attempt in range(max_retries):
            current_proverb = proverb.get('text', '') if proverb else ''
            if current_proverb and state_manager.check_vocabulary_exists(current_proverb, 'proverb'):
                logger.info(f"Proverb '{current_proverb}' is a duplicate (attempt {attempt+1}/{max_retries}). Regenerating...")
                proverb_rejected.append(current_proverb)
                new_proverb = regenerate_field_with_llm('proverb', proverb_rejected, story)
                if new_proverb and new_proverb.get('text'):
                    proverb = new_proverb
                    json_data["proverb"] = new_proverb
                else:
                    logger.warning("Regenerating proverb returned empty result.")
                    break
            else:
                break

        # 3. 檢驗並重試德文單字 (German Word)
        german_rejected = []
        for attempt in range(max_retries):
            current_german = german.get('word', '') if german else ''
            if current_german and state_manager.check_vocabulary_exists(current_german, 'german'):
                logger.info(f"German word '{current_german}' is a duplicate (attempt {attempt+1}/{max_retries}). Regenerating...")
                german_rejected.append(current_german)
                new_german = regenerate_field_with_llm('german', german_rejected, story)
                if new_german and new_german.get('word'):
                    german = new_german
                    json_data["german_vocab"] = new_german
                else:
                    logger.warning("Regenerating german word returned empty result.")
                    break
            else:
                break
        
        # 1. 產生 Telegram 版的 Markdown 內容
        markdown_content = f"{story}\n\n"
        markdown_content += f"💡 **【今日商務單字】**\n"
        markdown_content += f"🔹 **{vocab.get('word', '')}** ({vocab.get('pos', '')}) /{vocab.get('pronunciation', '')}/\n"
        markdown_content += f"👉 釋義：\n{vocab.get('definition', '')}\n\n"
        markdown_content += f"👉 例句：{vocab.get('example', '')}\n\n"
        
        markdown_content += f"🇩🇪 **【德語小教室】**\n"
        markdown_content += f"🔹 **{german.get('word', '')}** ({german.get('pos', '')}) /{german.get('pronunciation', '')}/\n"
        markdown_content += f"👉 釋義：{german.get('definition', '')}\n\n"
        markdown_content += f"👉 例句：{german.get('example', '')}\n\n"

        markdown_content += f"📜 **【今日商業/處世諺語】**\n"
        markdown_content += f"🔹 **{proverb.get('text', '')}**\n"
        markdown_content += f"👉 解析：{proverb.get('explanation', '')}\n"
        markdown_content += f"👉 應用：{proverb.get('usage', '')}"
        
        # 2. 產生電子報版的 HTML 內容並存檔
        # 處理 Markdown 粗體與斜體
        story_html = story
        story_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', story_html)
        story_html = re.sub(r'\*(.*?)\*', r'<span style="color:rgb(37,110,225)"><i>\1</i></span>', story_html)
        story_html = re.sub(r'\b_(.*?)_\b', r'<span style="color:rgb(37,110,225)"><i>\1</i></span>', story_html)
        
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
                {story_html.replace(chr(10), '<br>')}
            </div>
            
            <div class="vocab-box">
                <h2>💡 今日商務單字</h2>
                <p><span class="word">{vocab.get('word', '')}</span> <span class="pronunciation">({vocab.get('pos', '')}) /{vocab.get('pronunciation', '')}/</span></p>
                <p>👉 <strong>釋義：</strong><br>{vocab.get('definition', '').replace(chr(10), '<br>')}</p>
                <p>👉 <strong>例句：</strong><br>{vocab.get('example', '').replace(chr(10), '<br>')}</p>
            </div>
            
            <div class="vocab-box">
                <h2>🇩🇪 德語小教室</h2>
                <p><span class="word">{german.get('word', '')}</span> <span class="pronunciation">({german.get('pos', '')}) /{german.get('pronunciation', '')}/</span></p>
                <p>👉 <strong>釋義：</strong><br>{german.get('definition', '').replace(chr(10), '<br>')}</p>
                <p>👉 <strong>例句：</strong><br>{german.get('example', '').replace(chr(10), '<br>')}</p>
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
            
        return markdown_content, vocab.get('word', ''), proverb.get('text', ''), german.get('word', ''), json_data
        
    except Exception as e:
        logger.error(f"Error parsing LLM JSON output: {e}")
        return None, None, None, None, None
