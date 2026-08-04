import sys
from logger import get_logger
from modules.state_manager import StateManager
from modules.finmind_api import fetch_company_data
from modules.news_api import fetch_company_news
from modules.formatter import format_daily_report
from modules.telegram_bot import send_to_telegram

logger = get_logger("main")

def main():
    logger.info("=== Starting Content Automation (No AI) ===")
    
    # 1. Get next company
    state_mgr = StateManager()
    company = state_mgr.get_next_company()
    
    if not company:
        logger.error("No companies found in database or queue. Exiting.")
        sys.exit(1)
        
    stock_id = company['stock_id']
    logger.info(f"Selected company: {company['name']} ({stock_id})")
    
    # 2. Fetch basic data (FinMind)
    basic_data = fetch_company_data(stock_id)
    if not basic_data:
        logger.error(f"Failed to fetch basic data for {stock_id}. Exiting.")
        sys.exit(1)
        
    # 3. Fetch news and story (Tavily)
    from modules.news_api import fetch_company_story
    logger.info(f"Fetching news and story for: {basic_data['company_name']}")
    news_content = fetch_company_news(basic_data['company_name'])
    story_content = fetch_company_story(basic_data['company_name'])
    
    # 4. Format Data (Without AI)
    logger.info("Formatting daily report...")
    post_draft = format_daily_report(basic_data, news_content, story_content)
    if not post_draft:
        logger.error("Failed to format report. Exiting.")
        sys.exit(1)
        
    # 5. Send to Telegram
    success = send_to_telegram(post_draft)
    
    # 6. Update state if successful
    if success:
        state_mgr.mark_as_posted(stock_id)
        logger.info("Workflow completed successfully.")
    else:
        logger.error("Workflow finished with errors (Telegram failed). State not updated.")
        sys.exit(1)

if __name__ == "__main__":
    main()
