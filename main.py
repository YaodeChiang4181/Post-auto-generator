import sys
from logger import get_logger
from modules.gov_api import get_random_company
from modules.news_api import fetch_all_metrics
from modules.formatter import format_daily_report
from modules.llm_api import select_top_news_with_llm, generate_tag_explanation, generate_tag_explanations_batch
from modules.telegram_bot import send_to_telegram
from modules.state_manager import StateManager
from modules.news_aggregator import get_daily_news_candidates
from modules.gmail_sender import send_newsletter_as_draft


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
    logger.info("Formatting daily report with Vocabulary, Proverb, and German word...")
    recent_history = state_manager.get_recent_history(days=30)
    post_draft, vocab_word, proverb_text, german_word, json_data = format_daily_report(company, metrics, recent_history)
    
    if not post_draft:
        logger.error("Failed to format report. Exiting.")
        sys.exit(1)
        
    # 4. Send to Telegram
    logger.info("Sending Business Story to Telegram...")
    success = send_to_telegram(post_draft)
    
    # --- News Module ---
    logger.info("Starting Daily Top 3 News Highlights...")
    news_candidates = get_daily_news_candidates()
    top_news_data = select_top_news_with_llm(news_candidates)
    
    news_success = True
    processed_news_data = {"top_news": []}  # 用於 Gmail 草稿
    if top_news_data and "top_news" in top_news_data:
        news_msg = "📰 【每日重大新聞快訊 Top 3】\n\n"
        processed_news_data = top_news_data  # 保留完整結構供 Gmail 使用
        
        # Sort by rank just in case LLM shuffles them
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
            tags_to_generate = []
            for tag in item.get('tags', []):
                existing_tag = state_manager.get_tag_details(tag['name'])
                if existing_tag and existing_tag.get('glossary') and existing_tag.get('related_keywords'):
                    enriched_tags.append({
                        'name': tag['name'],
                        'type': existing_tag.get('type', tag.get('type', 'Entity'))
                    })
                else:
                    tags_to_generate.append(tag)
                    
            if tags_to_generate:
                batch_explanations = generate_tag_explanations_batch([t['name'] for t in tags_to_generate])
                expl_map = {ex['tag_name']: ex for ex in batch_explanations}
                
                for tag in tags_to_generate:
                    explanation_data = expl_map.get(tag['name'])
                    enriched_tags.append({
                        'name': tag['name'],
                        'type': tag.get('type', 'Entity'),
                        'explanation': explanation_data.get('explanation', '') if explanation_data else '',
                        'takeaway': explanation_data.get('takeaway', '') if explanation_data else '',
                        'related_keywords': explanation_data.get('related_keywords', []) if explanation_data else []
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
    else:
        logger.warning("Failed to generate Top 3 News.")
        news_success = False
    
    # 5. 建立 Gmail 草稿 (Telegram 成功後執行)
    if success and news_success:
        logger.info("Building Gmail draft...")
        try:
            # 組合 story_data 傳入 gmail_sender
            story_data_for_gmail = {
                "company_name": company['name'],
                "story": post_draft,
                "vocab": json_data.get("vocabulary", {}) if json_data else {},
                "proverb": json_data.get("proverb", {}) if json_data else {},
                "german": json_data.get("german_vocab", {}) if json_data else {},
            }
            gmail_ok = send_newsletter_as_draft(story_data_for_gmail, processed_news_data)
            if gmail_ok:
                logger.info("Gmail draft created successfully.")
            else:
                logger.warning("Gmail draft creation failed (non-critical, continuing).")
        except Exception as e:
            logger.warning(f"Gmail draft step skipped due to error: {e}")

    # 6. Output result & Save History
    if success and news_success:
        state_manager.save_history(vocab_word, proverb_text, german_word)
        logger.info("Workflow completed successfully. History saved.")
    else:
        logger.error("Workflow finished with errors (Story or News Telegram failed).")
        sys.exit(1)

if __name__ == "__main__":
    main()
