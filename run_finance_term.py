import sys
from logger import get_logger
from modules.state_manager import StateManager
from modules.llm_api import generate_finance_term
from modules.telegram_bot import send_to_telegram

logger = get_logger("run_finance_term")

def run():
    logger.info("=== Starting Professional Financial Vocabulary Analysis ===")
    state_manager = StateManager()
    
    logger.info("Fetching today's news context from database...")
    news_context = state_manager.get_todays_news_context()
    
    if not news_context:
        logger.warning("No news context found for today. Exiting.")
        sys.exit(0)
        
    logger.info("Fetching recent history to avoid duplicates...")
    recent_history = state_manager.get_recent_history(days=30)
        
    logger.info("Generating financial term deep dive...")
    term_data = generate_finance_term(news_context, recent_history=recent_history)
    
    if term_data:
        msg = "💡 【今日金融名詞拆解】\n\n"
        msg += f"🔥 焦點名詞：{term_data['focus_term']}\n\n"
        msg += f"🗞️ 新聞發生了什麼事？\n{term_data['news_context']}\n\n"
        msg += f"🧠 3 分鐘白話降維解析：\n{term_data['simple_explanation']}\n\n"
        msg += "📈 實質影響：\n"
        for idx, impact in enumerate(term_data['impact']):
            msg += f"{idx+1}. {impact}\n"
        msg += f"\n✍️ 主編金句：\n「{term_data['takeaway_quote']}」"
        
        logger.info("Sending Financial Term Deep Dive to Telegram...")
        success = send_to_telegram(msg.strip())
        
        if success:
            state_manager.save_history(vocab=None, proverb=None, finance_term=term_data['focus_term'])
            logger.info("Financial Term workflow completed successfully.")
        else:
            logger.error("Financial Term Telegram failed.")
            sys.exit(1)
    else:
        logger.error("Failed to generate Financial Term Deep Dive.")
        sys.exit(1)

if __name__ == "__main__":
    run()
