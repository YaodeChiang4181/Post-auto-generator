"""
Static Data Exporter for GitHub Pages (InsightOrbit)
===================================================
Exports database records into a single static JSON file (docs/data/orbit_data.json)
so that the frontend InsightOrbit panel can run completely serverless on GitHub Pages.
"""

import json
import os
from logger import get_logger

logger = get_logger("static_exporter")

def export_orbit_static_data(output_file: str = None) -> bool:
    """
    Exports latest Top 3 articles and all related tags (with their historical timelines)
    to a static JSON file for GitHub Pages hosting.
    """
    if output_file is None:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        output_file = os.path.join(base_dir, "docs", "data", "orbit_data.json")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    try:
        from modules.state_manager import StateManager
        sm = StateManager()
    except Exception as e:
        logger.warning(f"Could not connect to database for static export: {e}")
        return False

    try:
        import psycopg2.extras
        with sm._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # 1. Fetch latest 3 articles
                cursor.execute('''
                    SELECT id, title, summary, source_url, source_name, created_at
                    FROM articles
                    ORDER BY created_at DESC
                    LIMIT 3
                ''')
                articles_rows = cursor.fetchall()
                if not articles_rows:
                    logger.warning("No articles found in database to export.")
                    return False

                orbit_articles = []
                all_tag_names = set()

                for row in articles_rows:
                    article = dict(row)
                    article['created_at'] = article['created_at'].isoformat() if article.get('created_at') else ''
                    
                    # Fetch tags for this article
                    cursor.execute('''
                        SELECT t.name, t.tag_type as type
                        FROM tags t
                        JOIN article_tags at ON t.id = at.tag_id
                        WHERE at.article_id = %s
                    ''', (article['id'],))
                    tags = [dict(t_row) for t_row in cursor.fetchall()]
                    article['tags'] = tags
                    for t in tags:
                        all_tag_names.add(t['name'])
                    orbit_articles.append(article)

                # 2. Fetch details and historical timeline for all related tags
                tags_data = {}
                for tag_name in all_tag_names:
                    details = sm.get_tag_details(tag_name)
                    if details:
                        tags_data[tag_name] = details
                        # Also include related keywords in tags_data if available
                        for rel_kw in details.get('related_keywords', []):
                            if rel_kw not in tags_data:
                                rel_details = sm.get_tag_details(rel_kw)
                                if rel_details:
                                    tags_data[rel_kw] = rel_details

                export_payload = {
                    "orbit": orbit_articles,
                    "tags": tags_data
                }

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_payload, f, ensure_ascii=False, indent=2)

                logger.info(f"✅ Successfully exported static orbit data to {output_file}")
                return True

    except Exception as e:
        logger.error(f"Error during static orbit data export: {e}")
        return False

if __name__ == "__main__":
    export_orbit_static_data()
