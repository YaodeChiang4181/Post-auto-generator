import psycopg2
import psycopg2.extras
import json
import os
from config import DATABASE_URL, COMPANIES_FILE
from logger import get_logger
from datetime import datetime, timedelta

COUNTERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'counters.json')

logger = get_logger(__name__)

import re

POS_TAGS = {"n", "v", "adj", "adv", "prep", "pron", "conj", "interj", "vt", "vi"}

def normalize_text(text: str) -> str:
    """
    Standardize text by lowercasing, removing extra whitespaces,
    stripping punctuation, parenthetical annotations (e.g. '(n.)', '(v.)'),
    and leading English articles ('a', 'an', 'the').
    """
    if not text:
        return ""
    # Strip parenthetical annotations
    cleaned = re.sub(r'[\(\[\{（【].*?[\)\]\}）】]', '', text)
    cleaned = cleaned.lower()
    # Strip leading English articles
    cleaned = re.sub(r'^(?:a|an|the)\s+', '', cleaned)
    # Strip non-alphanumeric/non-cjk chars to single spaces
    cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def get_canonical_variants(text: str) -> set[str]:
    """
    Generate canonical variants (including stems for plurals, verb endings, and bracketed sub-terms).
    For example:
      'synergies' -> {'synergies', 'synergy'}
      'hedging' -> {'hedging', 'hedge', 'hedg'}
      '軋空 (Short Squeeze)' -> {'軋空', 'short squeeze'}
    """
    if not text:
        return set()
    
    variants = set()
    # Extract inner content from brackets if meaningful (e.g., English translation or term)
    bracket_matches = re.findall(r'[\(\[\{（【](.*?)[\)\]\}）】]', text)
    for bm in bracket_matches:
        norm_b = normalize_text(bm)
        if norm_b and norm_b not in POS_TAGS:
            variants.add(norm_b)

    base = normalize_text(text)
    if base:
        variants.add(base)
        
    if not variants:
        return set()
    
    # Check single English words for inflections
    for v in list(variants):
        words = v.split()
        if len(words) == 1:
            w = words[0]
            # Plurals: -ies -> -y
            if w.endswith('ies') and len(w) > 4:
                variants.add(w[:-3] + 'y')
            elif w.endswith('es') and len(w) > 3:
                variants.add(w[:-2])
                variants.add(w[:-1])
            elif w.endswith('s') and not w.endswith('ss') and len(w) > 3:
                variants.add(w[:-1])
            # Verb endings: -ing -> base, base+e
            if w.endswith('ing') and len(w) > 4:
                variants.add(w[:-3])
                variants.add(w[:-3] + 'e')
            # Verb endings: -ed -> base, base+e
            if w.endswith('ed') and len(w) > 3:
                variants.add(w[:-2])
                variants.add(w[:-1])
    
    return {v for v in variants if v}

class StateManager:
    def __init__(self, db_url=None):
        raw_url = db_url or DATABASE_URL
        if not raw_url:
            raise ValueError("DATABASE_URL must be set in the environment or .env file")
        self.db_url = raw_url.strip("\"' ")
        self._init_db()
        self._load_initial_data()

    def _get_connection(self):
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # connect_timeout=15 ensures it doesn't hang indefinitely before retrying
                return psycopg2.connect(self.db_url, connect_timeout=15)
            except psycopg2.OperationalError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database connection failed (attempt {attempt+1}/{max_retries}), retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    logger.error("Failed to connect to the database after multiple attempts.")
                    raise

    def _init_db(self):
        """Initialize the PostgreSQL database schema."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS companies (
                        stock_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        last_posted_at TIMESTAMP
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS vocabulary_history (
                        id SERIAL PRIMARY KEY,
                        type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP
                    )
                ''')
                
                # InsightOrbit Tables
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS articles (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        source_url TEXT NOT NULL,
                        source_name TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tags (
                        id SERIAL PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        tag_type TEXT NOT NULL,
                        explanation TEXT,
                        takeaway TEXT,
                        related_keywords TEXT
                    )
                ''')
                # For existing databases, add the column if missing
                cursor.execute('''
                    ALTER TABLE tags ADD COLUMN IF NOT EXISTS related_keywords TEXT
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
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_counters (
                        key TEXT PRIMARY KEY,
                        value INTEGER NOT NULL,
                        updated_at TIMESTAMP
                    )
                ''')
            conn.commit()

    def _load_initial_data(self):
        """Load from companies.json if the database is empty."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM companies')
                count = cursor.fetchone()[0]
                
                if count == 0:
                    logger.info(f"Database is empty. Loading from {COMPANIES_FILE}...")
                    try:
                        with open(COMPANIES_FILE, 'r', encoding='utf-8') as f:
                            companies = json.load(f)
                        
                        for comp in companies:
                            cursor.execute(
                                'INSERT INTO companies (stock_id, name) VALUES (%s, %s)',
                                (comp['stock_id'], comp['name'])
                            )
                        conn.commit()
                        logger.info(f"Loaded {len(companies)} companies into the database.")
                    except Exception as e:
                        logger.error(f"Failed to load initial data: {e}")

    def get_next_company(self):
        """Get the next company that hasn't been posted recently (or at all)."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # PostgreSQL NULLS FIRST
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
            with conn.cursor() as cursor:
                now = datetime.now()
                cursor.execute(
                    'UPDATE companies SET last_posted_at = %s WHERE stock_id = %s',
                    (now, stock_id)
                )
            conn.commit()
            logger.info(f"Marked {stock_id} as posted at {now}")

    def get_recent_history(self, days=30):
        """Fetch vocabularies and proverbs used in the last `days` days, ordered from newest to oldest."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cutoff = datetime.now() - timedelta(days=days)
                cursor.execute('''
                    SELECT type, content FROM vocabulary_history
                    WHERE created_at >= %s
                    ORDER BY created_at DESC
                ''', (cutoff,))
                rows = cursor.fetchall()
                
                history = {"vocab": [], "proverb": [], "german": [], "finance_term": []}
                for row in rows:
                    if row[0] == 'vocab':
                        history["vocab"].append(row[1])
                    elif row[0] == 'proverb':
                        history["proverb"].append(row[1])
                    elif row[0] == 'german':
                        history["german"].append(row[1])
                    elif row[0] == 'finance_term':
                        history["finance_term"].append(row[1])
                        
                return history

    def check_vocabulary_exists(self, content, vocab_type='vocab'):
        """
        Check if a specific vocabulary/proverb/german word/finance term already exists in history.
        Uses normalization and canonical variant matching to catch inflections, articles, and casing.
        Maintains independent namespace per vocab_type.
        """
        if not content:
            return False

        content_variants = get_canonical_variants(content)
        if not content_variants:
            content_variants = {content.strip().lower()}

        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT content FROM vocabulary_history
                    WHERE type = %s
                ''', (vocab_type,))
                history_rows = cursor.fetchall()
                
                for row in history_rows:
                    hist_content = row[0]
                    if not hist_content:
                        continue
                    # Fast exact case-insensitive match
                    if content.strip().lower() == hist_content.strip().lower():
                        return True
                    # Variant / inflection intersection match
                    hist_variants = get_canonical_variants(hist_content)
                    if content_variants.intersection(hist_variants):
                        return True

                return False

    def save_history(self, vocab=None, proverb=None, german=None, finance_term=None):
        """Save a new vocabulary, proverb, german word, or finance term to the history."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                now = datetime.now()
                if vocab:
                    cursor.execute(
                        'INSERT INTO vocabulary_history (type, content, created_at) VALUES (%s, %s, %s)',
                        ('vocab', vocab, now)
                    )
                if proverb:
                    cursor.execute(
                        'INSERT INTO vocabulary_history (type, content, created_at) VALUES (%s, %s, %s)',
                        ('proverb', proverb, now)
                    )
                if german:
                    cursor.execute(
                        'INSERT INTO vocabulary_history (type, content, created_at) VALUES (%s, %s, %s)',
                        ('german', german, now)
                    )
                if finance_term:
                    cursor.execute(
                        'INSERT INTO vocabulary_history (type, content, created_at) VALUES (%s, %s, %s)',
                        ('finance_term', finance_term, now)
                    )
            conn.commit()
            logger.info(f"Saved vocabulary '{vocab}', proverb '{proverb}', german '{german}', finance_term '{finance_term}' to history.")

    def get_next_counters(self) -> tuple[int, int]:
        """
        取得下一期電子報期數與下一篇商業故事篇數 (目前為 46 與 62，明天自動加 1 進位至 47 與 63)。
        優先讀取資料庫 system_counters，若不存在則以 data/counters.json 或基準值 (46, 62) 為基礎。
        回傳 (next_newsletter_issue, next_story_issue)
        """
        curr_nl = 46
        curr_st = 62

        # 嘗試從 local counters.json 讀取基準值
        if os.path.exists(COUNTERS_FILE):
            try:
                with open(COUNTERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    curr_nl = data.get("newsletter_issue", curr_nl)
                    curr_st = data.get("story_issue", curr_st)
            except Exception as e:
                logger.warning(f"讀取 {COUNTERS_FILE} 失敗: {e}")

        # 嘗試從資料庫讀取並同步
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT key, value FROM system_counters WHERE key IN ('newsletter_issue', 'story_issue')")
                    rows = dict(cursor.fetchall())
                    
                    if 'newsletter_issue' in rows:
                        curr_nl = rows['newsletter_issue']
                    else:
                        cursor.execute(
                            "INSERT INTO system_counters (key, value, updated_at) VALUES (%s, %s, %s) ON CONFLICT (key) DO NOTHING",
                            ('newsletter_issue', curr_nl, datetime.now())
                        )

                    if 'story_issue' in rows:
                        curr_st = rows['story_issue']
                    else:
                        cursor.execute(
                            "INSERT INTO system_counters (key, value, updated_at) VALUES (%s, %s, %s) ON CONFLICT (key) DO NOTHING",
                            ('story_issue', curr_st, datetime.now())
                        )
                conn.commit()
        except Exception as e:
            logger.warning(f"從資料庫讀取 system_counters 失敗，使用本機設定: {e}")

        # 明天的流程順著加 1
        return curr_nl + 1, curr_st + 1

    def increment_counters(self, new_newsletter_issue: int, new_story_issue: int):
        """
        成功發送與完成每日流程後，更新並持久化期數與篇數 (寫入 DB 與 data/counters.json)。
        """
        now = datetime.now()
        # 1. 寫入資料庫
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO system_counters (key, value, updated_at)
                        VALUES ('newsletter_issue', %s, %s)
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                    ''', (new_newsletter_issue, now))
                    cursor.execute('''
                        INSERT INTO system_counters (key, value, updated_at)
                        VALUES ('story_issue', %s, %s)
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                    ''', (new_story_issue, now))
                conn.commit()
                logger.info(f"已更新資料庫計數器: 電子報期數 #{new_newsletter_issue}, 商業故事篇數 #{new_story_issue}")
        except Exception as e:
            logger.error(f"寫入資料庫計數器失敗: {e}")

        # 2. 寫入本地檔案 data/counters.json (供 Git commit 同步備援)
        try:
            os.makedirs(os.path.dirname(COUNTERS_FILE), exist_ok=True)
            with open(COUNTERS_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "newsletter_issue": new_newsletter_issue,
                    "story_issue": new_story_issue
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"已同步更新 {COUNTERS_FILE}")
        except Exception as e:
            logger.error(f"寫入 {COUNTERS_FILE} 失敗: {e}")

    # --- InsightOrbit Methods ---
    def save_article_with_tags(self, article, tags_info):
        """
        Save an article and its related tags.
        """
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                now = datetime.now()
                
                # Insert article and get id
                cursor.execute('''
                    INSERT INTO articles (title, summary, source_url, source_name, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (article['title'], article['summary'], article['source_url'], article.get('source', 'Unknown'), article.get('created_at', now)))
                article_id = cursor.fetchone()[0]
                
                for tag in tags_info:
                    # Insert or ignore tag
                    cursor.execute('''
                        INSERT INTO tags (name, tag_type, explanation, takeaway, related_keywords)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (name) DO NOTHING
                    ''', (tag['name'], tag.get('type', 'Entity'), tag.get('explanation', ''), tag.get('takeaway', ''), json.dumps(tag.get('related_keywords', []))))
                    
                    # Retrieve tag_id
                    cursor.execute('SELECT id FROM tags WHERE name = %s', (tag['name'],))
                    tag_id = cursor.fetchone()[0]
                    
                    # If explanation is missing but provided now, update it
                    if tag.get('explanation'):
                        cursor.execute('''
                            UPDATE tags SET explanation = %s, takeaway = %s, related_keywords = %s WHERE id = %s AND (explanation IS NULL OR explanation = '' OR related_keywords IS NULL)
                        ''', (tag['explanation'], tag.get('takeaway', ''), json.dumps(tag.get('related_keywords', [])), tag_id))
                    
                    # Link article and tag
                    cursor.execute('''
                        INSERT INTO article_tags (article_id, tag_id)
                        VALUES (%s, %s)
                        ON CONFLICT (article_id, tag_id) DO NOTHING
                    ''', (article_id, tag_id))
                
            conn.commit()
            logger.info(f"Saved InsightOrbit article '{article['title']}' with {len(tags_info)} tags.")
            return article_id
            
    def get_tag_details(self, tag_name):
        """Get tag explanation and its related historical articles."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                # Get Tag
                cursor.execute('SELECT * FROM tags WHERE name = %s', (tag_name,))
                tag_row = cursor.fetchone()
                if not tag_row:
                    return None
                    
                tag_data = dict(tag_row)
                
                # Get Timeline (Historical Articles)
                cursor.execute('''
                    SELECT a.id, a.title as headline, a.summary, a.source_url as source, a.created_at as date
                    FROM articles a
                    JOIN article_tags at ON a.id = at.article_id
                    WHERE at.tag_id = %s
                    ORDER BY a.created_at DESC
                ''', (tag_data['id'],))
                
                articles = [dict(row) for row in cursor.fetchall()]
                # Format dates and fetch tags for each historical article
                for a in articles:
                    cursor.execute('''
                        SELECT t.name, t.tag_type as type
                        FROM tags t
                        JOIN article_tags at ON t.id = at.tag_id
                        WHERE at.article_id = %s
                    ''', (a['id'],))
                    a['tags'] = [dict(t_row) for t_row in cursor.fetchall()]
                    a['date'] = a['date'].isoformat() if a['date'] else ''
                
                related_keywords = None
                if tag_data.get('related_keywords') is not None:
                    try:
                        related_keywords = json.loads(tag_data['related_keywords'])
                    except:
                        related_keywords = []

                return {
                    "type": tag_data['tag_type'],
                    "title": tag_data['name'],
                    "glossary": tag_data['explanation'],
                    "takeaway": tag_data['takeaway'],
                    "related_keywords": related_keywords,
                    "tags": [tag_data['name']],
                    "timeline": articles
                }

    def get_todays_news_context(self):
        """Fetch the latest 3 articles to use as news context."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute('''
                    SELECT title, summary, source_url 
                    FROM articles
                    ORDER BY created_at DESC
                    LIMIT 3
                ''')
                rows = cursor.fetchall()
                if not rows:
                    return None
                context_str = ""
                for idx, row in enumerate(rows):
                    context_str += f"[{idx+1}] {row['title']}\n摘要：{row['summary']}\n連結：{row['source_url']}\n\n"
                return context_str.strip()

    def get_recent_article_titles(self, days=2):
        """Fetch article titles from the last `days` days to check for duplicates."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cutoff = datetime.now() - timedelta(days=days)
                cursor.execute('''
                    SELECT title, source_name, created_at 
                    FROM articles
                    WHERE created_at >= %s
                    ORDER BY created_at DESC
                ''', (cutoff,))
                rows = cursor.fetchall()
                titles = []
                for row in rows:
                    titles.append(f"【{row[1]}】{row[0]} (發布時間: {row[2].strftime('%Y-%m-%d %H:%M')})")
                return titles
