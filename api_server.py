from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import psycopg2.extras
from typing import List, Optional

from modules.state_manager import StateManager
from logger import get_logger
from apscheduler.schedulers.background import BackgroundScheduler
import run_news as scraper_news

logger = get_logger(__name__)

app = FastAPI(title="InsightOrbit API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run the news automation script every day at 00:00 UTC (8:00 AM TW time)
    scheduler.add_job(scraper_news.run, 'cron', hour=0, minute=0)
    scheduler.start()
    logger.info("Background scheduler started (cron set to 00:00 UTC).")

state_manager = StateManager()

# Mount templates/static directory
templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
if os.path.exists(templates_dir):
    app.mount("/static", StaticFiles(directory=templates_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the InsightOrbit Demo Panel directly from root for easy access."""
    panel_path = os.path.join(templates_dir, "insight_orbit_panel.html")
    if os.path.exists(panel_path):
        with open(panel_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>InsightOrbit API is running. Panel HTML not found.</h1>"

@app.get("/api/today")
async def get_today_orbit():
    """
    Get today's Top 3 news and their associated tags for the Level 1 Bubble View.
    """
    with state_manager._get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Get the latest 3 articles
            cursor.execute('''
                SELECT id, title, summary, source_url, source_name, created_at
                FROM articles
                ORDER BY created_at DESC
                LIMIT 3
            ''')
            articles_rows = cursor.fetchall()
            
            orbit_data = []
            for row in articles_rows:
                article = dict(row)
                article['created_at'] = article['created_at'].isoformat() if article.get('created_at') else ''
                
                # Fetch tags for this article
                cursor.execute('''
                    SELECT t.name, t.tag_type
                    FROM tags t
                    JOIN article_tags at ON t.id = at.tag_id
                    WHERE at.article_id = %s
                ''', (article['id'],))
                
                tags = [dict(t_row) for t_row in cursor.fetchall()]
                article['tags'] = tags
                orbit_data.append(article)
            
        return {"orbit": orbit_data}

@app.get("/api/tags/{tag_name}")
async def get_tag_detail(tag_name: str):
    """
    Get tag glossary and historical timeline for Level 3 Deep Dive.
    """
    details = state_manager.get_tag_details(tag_name)
    if not details:
        raise HTTPException(status_code=404, detail="Tag not found")
        
    # Backfill logic for old tags without related_keywords
    if not details.get('related_keywords'):
        from modules.llm_api import generate_tag_explanation
        import json
        logger.info(f"Tag '{tag_name}' is missing related_keywords. Regenerating...")
        new_data = generate_tag_explanation(tag_name)
        if new_data:
            with state_manager._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE tags SET explanation = %s, takeaway = %s, related_keywords = %s WHERE name = %s
                    ''', (new_data.get('explanation', details.get('glossary', '')), 
                          new_data.get('takeaway', details.get('takeaway', '')), 
                          json.dumps(new_data.get('related_keywords', [])), 
                          tag_name))
                conn.commit()
            details['glossary'] = new_data.get('explanation', details.get('glossary', ''))
            details['takeaway'] = new_data.get('takeaway', details.get('takeaway', ''))
            details['related_keywords'] = new_data.get('related_keywords', [])
            
    return details

if __name__ == "__main__":
    import uvicorn
    # Start the server on port defined by Render (default 8000)
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting InsightOrbit API Server on port {port}...")
    uvicorn.run("api_server:app", host="0.0.0.0", port=port, reload=False)
