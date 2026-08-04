import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from logger import get_logger

logger = get_logger(__name__)

def send_to_telegram(message):
    """
    將生成的草稿傳送到 Telegram 進行人工審核
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials are not set.")
        return False
        
    logger.info("Sending message to Telegram Bot...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Telegram 限制單則訊息最長 4096 字元，稍微做個截斷保護
    safe_message = message[:4000]
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🚀 【每日資訊彙整成功！】\n\n{safe_message}",
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Successfully sent to Telegram!")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send message to Telegram: {e}")
        return False
