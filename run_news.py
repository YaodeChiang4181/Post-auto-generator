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
            all_related_keywords = []
            
            for tag in item.get('tags', []):
                existing_tag = state_manager.get_tag_details(tag['name'])
                if existing_tag and existing_tag.get('glossary') and existing_tag.get('related_keywords') is not None:
                    enriched_tags.append({
                        'name': tag['name'],
                        'type': existing_tag.get('type', tag.get('type', 'Entity'))
                    })
                    all_related_keywords.extend(existing_tag.get('related_keywords', []))
                else:
                    explanation_data = generate_tag_explanation(tag['name'])
                    rel_kws = explanation_data.get('related_keywords', []) if explanation_data else []
                    enriched_tags.append({
                        'name': tag['name'],
                        'type': tag.get('type', 'Entity'),
                        'explanation': explanation_data.get('explanation', '') if explanation_data else '',
                        'takeaway': explanation_data.get('takeaway', '') if explanation_data else '',
                        'related_keywords': rel_kws
                    })
                    all_related_keywords.extend(rel_kws)
            
            article_data = {
                'title': item['title'],
                'summary': item['summary'],
                'source_url': item['source_url'],
                'source': 'News Aggregator'
            }
            state_manager.save_article_with_tags(article_data, enriched_tags)
            
            # Pre-generate Layer 3 tags (Drawer keywords)
            unique_kws = list(set(all_related_keywords))
            if unique_kws:
                logger.info(f"Pre-fetching {len(unique_kws)} Layer 3 related keywords...")
                for kw in unique_kws:
                    kw_details = state_manager.get_tag_details(kw)
                    if not kw_details or kw_details.get('related_keywords') is None:
                        kw_exp = generate_tag_explanation(kw)
                        if kw_exp:
                            import json
                            with state_manager._get_connection() as conn:
                                with conn.cursor() as cursor:
                                    if not kw_details:
                                        cursor.execute('''
                                            INSERT INTO tags (name, tag_type, explanation, takeaway, related_keywords)
                                            VALUES (%s, %s, %s, %s, %s)
                                            ON CONFLICT (name) DO NOTHING
                                        ''', (kw, 'Concept', kw_exp.get('explanation', ''), kw_exp.get('takeaway', ''), json.dumps(kw_exp.get('related_keywords', []))))
                                    else:
                                        cursor.execute('''
                                            UPDATE tags SET explanation = %s, takeaway = %s, related_keywords = %s WHERE name = %s
                                        ''', (kw_exp.get('explanation', ''), kw_exp.get('takeaway', ''), json.dumps(kw_exp.get('related_keywords', [])), kw))
                                conn.commit()
            
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
