import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Groq LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# App Config
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
COMPANIES_FILE = os.path.join(DATA_DIR, "companies.json")
DB_FILE = os.path.join(DATA_DIR, "state.db")

# Ensure required directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
