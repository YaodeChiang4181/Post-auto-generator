"""
Static Data Exporter for GitHub Pages (InsightOrbit)
===================================================
Exports database records into a single static JSON file (docs/data/orbit_data.json)
and updates embedded __INITIAL_DATA__ in index.html for instant static rendering.
"""

import json
import os
import re
from logger import get_logger

logger = get_logger("static_exporter")

def _update_html_file(file_path: str, json_str: str):
    """Injects fresh data into the embedded window.__INITIAL_DATA__ in HTML."""
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = r"window\.__INITIAL_DATA__\s*=\s*\{.*?\};\n\s*</script>"
        replacement = f"window.__INITIAL_DATA__ = {json_str};\n    </script>"
        new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        logger.info(f"Updated embedded initial data in {file_path}")
    except Exception as e:
        logger.warning(f"Failed to update embedded data in {file_path}: {e}")

def export_orbit_static_data(output_file: str = None) -> bool:
    """
    Exports latest Top 3 articles and ALL historical tags with timelines
    to a static JSON file for GitHub Pages hosting.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    if output_file is None:
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
                # 1. Fetch latest 3 articles for main Orbit bubble view
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
                    orbit_articles.append(article)

                # 2. Fetch details and complete historical timeline for ALL tags in database!
                cursor.execute('SELECT name FROM tags')
                all_tags_rows = cursor.fetchall()
                all_tag_names = [r['name'] for r in all_tags_rows]
                logger.info(f"Exporting historical timelines for {len(all_tag_names)} tags across all past weeks...")

                tags_data = {}
                for tag_name in all_tag_names:
                    details = sm.get_tag_details(tag_name)
                    if details:
                        tags_data[tag_name] = details

                export_payload = {
                    "orbit": orbit_articles,
                    "tags": tags_data
                }

                json_str = json.dumps(export_payload, ensure_ascii=False, indent=2)

                # Write to docs/data/orbit_data.json
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(json_str)

                # Also update embedded HTML files
                _update_html_file(os.path.join(base_dir, "index.html"), json_str)
                _update_html_file(os.path.join(base_dir, "docs", "index.html"), json_str)
                _update_html_file(os.path.join(base_dir, "templates", "insight_orbit_panel.html"), json_str)

                logger.info(f"✅ Successfully exported {len(all_tag_names)} tags and static data to {output_file}")
                return True

    except Exception as e:
        logger.error(f"Error during static orbit data export: {e}")
        return False

if __name__ == "__main__":
    export_orbit_static_data()
