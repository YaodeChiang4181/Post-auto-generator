import sys
from logger import get_logger
from modules.gov_api import get_random_company
from modules.news_api import fetch_all_metrics
from modules.formatter import format_daily_report
from modules.telegram_bot import send_to_telegram

from modules.state_manager import StateManager

logger = get_logger("main")

def main():
    logger.info("=== Starting Content Automation (Targeted Search Mode) ===")
    
    # 0. Init StateManager
    state_manager = StateManager()
    
    # 1. Get random company from government data
    company = get_random_company()
    
    if not company:
        logger.error("Failed to get a random company from government open data. Exiting.")
        sys.exit(1)
        
    stock_id = company['stock_id']
    logger.info(f"Selected company: {company['name']} ({stock_id}) - {company['market']}")
    
    # 2. Fetch all targeted metrics concurrently via Tavily
    logger.info("Fetching all 8 metric categories via search...")
    metrics = fetch_all_metrics(company)
    
    # 3. Format Data (With LLM JSON output)
    logger.info("Formatting daily report with Vocabulary and Proverb...")
    recent_history = state_manager.get_recent_history(days=30)
    post_draft, vocab_word, proverb_text = format_daily_report(company, metrics, recent_history)
    
    if not post_draft:
        logger.error("Failed to format report. Exiting.")
        sys.exit(1)
        
    # 4. Send to Telegram
    logger.info("Sending to Telegram...")
    success = send_to_telegram(post_draft)
    
    # 5. Output result & Save History
    if success:
        state_manager.save_history(vocab_word, proverb_text)
        logger.info("Workflow completed successfully. History saved.")
    else:
        logger.error("Workflow finished with errors (Telegram failed).")
        sys.exit(1)

if __name__ == "__main__":
    main()
