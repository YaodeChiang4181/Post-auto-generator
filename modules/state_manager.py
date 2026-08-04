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
