import sqlite3
import json
from config import DB_FILE, COMPANIES_FILE
from logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

class StateManager:
    def __init__(self):
        self.db_path = DB_FILE
        self._init_db()
        self._load_initial_data()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    stock_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    last_posted_at TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vocabulary_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP
                )
            ''')
            
            # InsightOrbit Tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    tag_type TEXT NOT NULL,
                    explanation TEXT,
                    takeaway TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS article_tags (
                    article_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (article_id, tag_id),
                    FOREIGN KEY (article_id) REFERENCES articles(id),
                    FOREIGN KEY (tag_id) REFERENCES tags(id)
                )
            ''')
            conn.commit()

    def _load_initial_data(self):
        """Load from companies.json if the database is empty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM companies')
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info(f"Database is empty. Loading from {COMPANIES_FILE}...")
                try:
                    with open(COMPANIES_FILE, 'r', encoding='utf-8') as f:
                        companies = json.load(f)
                    
                    for comp in companies:
                        cursor.execute(
                            'INSERT INTO companies (stock_id, name) VALUES (?, ?)',
                            (comp['stock_id'], comp['name'])
                        )
                    conn.commit()
                    logger.info(f"Loaded {len(companies)} companies into the database.")
                except Exception as e:
                    logger.error(f"Failed to load initial data: {e}")

    def get_next_company(self):
        """Get the next company that hasn't been posted recently (or at all)."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Find the company with the oldest last_posted_at, prioritizing NULL
            cursor.execute('''
                SELECT * FROM companies 
                ORDER BY last_posted_at ASC NULLS FIRST 
                LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def mark_as_posted(self, stock_id):
        """Mark a company as posted with the current timestamp."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                'UPDATE companies SET last_posted_at = ? WHERE stock_id = ?',
                (now, stock_id)
            )
            conn.commit()
            logger.info(f"Marked {stock_id} as posted at {now}")

    def get_recent_history(self, days=30):
        """Fetch vocabularies and proverbs used in the last `days` days."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT type, content FROM vocabulary_history
                WHERE created_at >= date('now', ?)
            ''', (f'-{days} days',))
            rows = cursor.fetchall()
            
            history = {"vocab": [], "proverb": [], "german": []}
            for row in rows:
                if row[0] == 'vocab':
                    history["vocab"].append(row[1])
                elif row[0] == 'proverb':
                    history["proverb"].append(row[1])
                elif row[0] == 'german':
                    history["german"].append(row[1])
                    
            return history

    def save_history(self, vocab, proverb, german=None):
        """Save a new vocabulary, proverb and german word to the history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            if vocab:
                cursor.execute(
                    'INSERT INTO vocabulary_history (type, content, created_at) VALUES (?, ?, ?)',
                    ('vocab', vocab, now)
                )
            if proverb:
                cursor.execute(
                    'INSERT INTO vocabulary_history (type, content, created_at) VALUES (?, ?, ?)',
                    ('proverb', proverb, now)
                )
            if german:
                cursor.execute(
                    'INSERT INTO vocabulary_history (type, content, created_at) VALUES (?, ?, ?)',
                    ('german', german, now)
                )
            conn.commit()
            logger.info(f"Saved vocabulary '{vocab}', proverb '{proverb}' and german '{german}' to history.")

    # --- InsightOrbit Methods ---
    def save_article_with_tags(self, article, tags_info):
        """
        Save an article and its related tags.
        `article`: dict with title, summary, source_url, source_name, created_at
        `tags_info`: list of dicts with name, type, explanation, takeaway
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # Insert article
            cursor.execute('''
                INSERT INTO articles (title, summary, source_url, source_name, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (article['title'], article['summary'], article['source_url'], article.get('source', 'Unknown'), article.get('created_at', now)))
            article_id = cursor.lastrowid
            
            for tag in tags_info:
                # Insert or ignore tag
                cursor.execute('''
                    INSERT OR IGNORE INTO tags (name, tag_type, explanation, takeaway)
                    VALUES (?, ?, ?, ?)
                ''', (tag['name'], tag.get('type', 'Entity'), tag.get('explanation', ''), tag.get('takeaway', '')))
                
                # Retrieve tag_id (it might already exist)
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag['name'],))
                tag_id = cursor.fetchone()[0]
                
                # If explanation is missing but provided now, update it
                if tag.get('explanation'):
                    cursor.execute('''
                        UPDATE tags SET explanation = ?, takeaway = ? WHERE id = ? AND (explanation IS NULL OR explanation = '')
                    ''', (tag['explanation'], tag.get('takeaway', ''), tag_id))
                
                # Link article and tag
                cursor.execute('''
                    INSERT OR IGNORE INTO article_tags (article_id, tag_id)
                    VALUES (?, ?)
                ''', (article_id, tag_id))
            
            conn.commit()
            logger.info(f"Saved InsightOrbit article '{article['title']}' with {len(tags_info)} tags.")
            return article_id
            
    def get_tag_details(self, tag_name):
        """Get tag explanation and its related historical articles."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get Tag
            cursor.execute('SELECT * FROM tags WHERE name = ?', (tag_name,))
            tag_row = cursor.fetchone()
            if not tag_row:
                return None
                
            tag_data = dict(tag_row)
            
            # Get Timeline (Historical Articles)
            cursor.execute('''
                SELECT a.title as headline, a.summary, a.source_url as source, a.created_at as date
                FROM articles a
                JOIN article_tags at ON a.id = at.article_id
                WHERE at.tag_id = ?
                ORDER BY a.created_at DESC
            ''', (tag_data['id'],))
            
            articles = [dict(row) for row in cursor.fetchall()]
            
            return {
                "type": tag_data['tag_type'],
                "title": tag_data['name'],
                "glossary": tag_data['explanation'],
                "takeaway": tag_data['takeaway'],
                "tags": [tag_data['name']], # In real usage, maybe fetch related tags
                "timeline": articles
            }

