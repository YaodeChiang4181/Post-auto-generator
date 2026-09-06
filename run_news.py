import sys
from logger import get_logger
from modules.llm_api import select_top_news_with_llm, generate_tag_explanation
from modules.telegram_bot import send_to_telegram
from modules.state_manager import StateManager
from modules.news_aggregator import get_daily_news_candidates

logger = get_logger("run_news")

def run():
    logger.info("=== Starting InsightOrbit News Automation ===")
    state_manager = StateManager()
    
    logger.info("Starting Daily Top 3 News Highlights...")
    news_candidates = get_daily_news_candidates()
    top_news_data = select_top_news_with_llm(news_candidates)
    
    if top_news_data and "top_news" in top_news_data:
        news_msg = "📰 【每日重大新聞快訊 Top 3】\n\n"
        top_news_data["top_news"].sort(key=lambda x: x.get('rank', 99))
        
        for item in top_news_data["top_news"]:
            news_msg += f"[{item['rank']}] {item['title']}\n"
            news_msg += f"💡 關鍵影響：{item['impact_reason']}\n"
            news_msg += f"📝 摘要：{item['summary']}\n"
            tags_str = ", ".join([f"#{t['name']}" for t in item.get('tags', [])])
            news_msg += f"🏷 標籤：{tags_str}\n"
            news_msg += f"🔗 原文連結：{item['source_url']}\n\n"
            
            # InsightOrbit: Generate tag explanations and save to DB
            enriched_tags = []
            for tag in item.get('tags', []):
                explanation_data = generate_tag_explanation(tag['name'])
                enriched_tags.append({
                    'name': tag['name'],
                    'type': tag.get('type', 'Entity'),
                    'explanation': explanation_data.get('explanation', '') if explanation_data else '',
                    'takeaway': explanation_data.get('takeaway', '') if explanation_data else ''
                })
            
            article_data = {
                'title': item['title'],
                'summary': item['summary'],
                'source_url': item['source_url'],
                'source': 'News Aggregator'
            }
            state_manager.save_article_with_tags(article_data, enriched_tags)
            
        logger.info("Sending Top 3 News to Telegram...")
        news_success = send_to_telegram(news_msg.strip())
        if news_success:
            logger.info("News workflow completed successfully.")
        else:
            logger.error("News Telegram failed.")
    else:
        logger.warning("Failed to generate Top 3 News.")
        
if __name__ == "__main__":
    run()
