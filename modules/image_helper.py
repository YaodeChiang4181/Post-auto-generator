import os
import re
import requests
from config import TAVILY_API_KEY
from logger import get_logger

logger = get_logger(__name__)

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def detect_image_mime(data: bytes) -> str:
    """
    透過二進位 Magic Bytes 檢測圖片真實 MIME 類型，
    避免因缺少副檔名（如 German-Dictionary）而無法判斷。
    """
    if len(data) >= 12:
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'image/webp'
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
        if data[:3] == b'\xff\xd8\xff':
            return 'image/jpeg'
        if data[:6] in (b'GIF87a', b'GIF89a'):
            return 'image/gif'
    return 'image/jpeg'  # 預設備援


def resolve_local_image(target_name: str) -> dict:
    """
    智慧解析專案內的本機圖片，支援：
    1. 精確檔名或無副檔名檔案 (如 'German-Dictionary')
    2. 帶副檔名檔案 (如 'dictionary_Photo.webp')
    3. 資料夾模式 (若目標為資料夾，選取內部第一張圖檔)

    Returns:
        dict: {"bytes": bytes, "mime_type": str, "filename": str} 或 None
    """
    # 候選路徑：優先根目錄，次之 assets/ 或 static/ 目錄
    search_dirs = [WORKSPACE_DIR, os.path.join(WORKSPACE_DIR, "assets"), os.path.join(WORKSPACE_DIR, "data")]

    resolved_path = None

    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue

        # 1. 直接精確比對
        direct_path = os.path.join(s_dir, target_name)
        if os.path.isfile(direct_path):
            resolved_path = direct_path
            break
        elif os.path.isdir(direct_path):
            # 若為資料夾，挑選內部第一個圖檔
            for sub_f in os.listdir(direct_path):
                sub_path = os.path.join(direct_path, sub_f)
                if os.path.isfile(sub_path) and sub_f.lower().endswith(('.webp', '.png', '.jpg', '.jpeg', '.gif')):
                    resolved_path = sub_path
                    break
            if resolved_path:
                break

        # 2. 前綴模糊比對 (例如尋找 dictionary_Photo.webp / dictionary_Photo.png)
        for item in os.listdir(s_dir):
            item_path = os.path.join(s_dir, item)
            base_name, _ = os.path.splitext(item)
            if base_name.lower() == target_name.lower() or item.lower() == target_name.lower():
                if os.path.isfile(item_path):
                    resolved_path = item_path
                    break
                elif os.path.isdir(item_path):
                    for sub_f in os.listdir(item_path):
                        sub_path = os.path.join(item_path, sub_f)
                        if os.path.isfile(sub_path) and sub_f.lower().endswith(('.webp', '.png', '.jpg', '.jpeg', '.gif')):
                            resolved_path = sub_path
                            break
                    if resolved_path:
                        break
        if resolved_path:
            break

    if not resolved_path or not os.path.exists(resolved_path):
        logger.warning(f"未能找到本機圖檔資產: {target_name}")
        return None

    try:
        with open(resolved_path, "rb") as f:
            data = f.read()

        mime_type = detect_image_mime(data)
        filename = os.path.basename(resolved_path)
        logger.info(f"成功加載本機圖檔 [{target_name}] -> {filename} ({len(data)} bytes, mime: {mime_type})")
        return {
            "bytes": data,
            "mime_type": mime_type,
            "filename": filename
        }
    except Exception as e:
        logger.error(f"讀取本機圖檔失敗 ({resolved_path}): {e}")
        return None


def fetch_company_photo(company_name: str, stock_id: str = "") -> dict:
    """
    動態檢索並下載商業故事中該間公司的代表性照片 (廠房、總部或官方識別)。
    雙層檢索架構：
    1. Tavily Search API (include_images=True)
    2. 中文維基百科 API (Wikipedia Pageimages API)
    若皆檢索失敗則平滑降級回傳 None。
    """
    if not company_name:
        return None

    # 清洗公司名稱，移除股票代號括弧以利搜尋，例如「普誠科技（6129）」->「普誠科技」
    clean_name = re.sub(r'[\(（].*?[\)）]', '', company_name).strip()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # --- 策略 1: Tavily Search API ---
    if TAVILY_API_KEY:
        try:
            logger.info(f"透過 Tavily API 檢索公司照片: {clean_name} ...")
            tavily_url = "https://api.tavily.com/search"
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": f"{clean_name} 公司 總部 OR 廠房 OR logo 照片",
                "search_depth": "basic",
                "max_results": 3,
                "include_images": True
            }
            res = requests.post(tavily_url, json=payload, timeout=8)
            if res.status_code == 200:
                images = res.json().get("images", [])
                for img_url in images:
                    if not img_url or not isinstance(img_url, str):
                        continue
                    if not img_url.startswith("http"):
                        continue
                    # 避免 svg 等不適合內嵌的格式
                    if img_url.lower().endswith(".svg"):
                        continue
                    try:
                        img_res = requests.get(img_url, headers=headers, timeout=5)
                        if img_res.status_code == 200 and len(img_res.content) > 1500:
                            data = img_res.content
                            mime = detect_image_mime(data)
                            logger.info(f"成功自 Tavily 下載公司照片: {img_url} ({len(data)} bytes, mime: {mime})")
                            return {
                                "bytes": data,
                                "mime_type": mime,
                                "filename": f"company_{stock_id or 'photo'}.jpg"
                            }
                    except Exception as download_err:
                        logger.debug(f"下載 Tavily 圖片失敗 ({img_url}): {download_err}")
        except Exception as e:
            logger.warning(f"Tavily 檢索公司照片發生錯誤: {e}")

    # --- 策略 2: 中文維基百科 Pageimages API 備援 ---
    try:
        logger.info(f"嘗試自維基百科 API 檢索公司照片: {clean_name} ...")
        wiki_api_url = (
            f"https://zh.wikipedia.org/w/api.php?action=query&titles={clean_name}&prop=pageimages"
            f"&format=json&pithumbsize=600"
        )
        wiki_res = requests.get(wiki_api_url, headers=headers, timeout=6)
        if wiki_res.status_code == 200:
            pages = wiki_res.json().get("query", {}).get("pages", {})
            for _, page_info in pages.items():
                thumbnail = page_info.get("thumbnail", {})
                img_url = thumbnail.get("source")
                if img_url:
                    img_res = requests.get(img_url, headers=headers, timeout=5)
                    if img_res.status_code == 200 and len(img_res.content) > 1500:
                        data = img_res.content
                        mime = detect_image_mime(data)
                        logger.info(f"成功自維基百科下載公司照片: {img_url} ({len(data)} bytes, mime: {mime})")
                        return {
                            "bytes": data,
                            "mime_type": mime,
                            "filename": f"company_{stock_id or 'photo'}.jpg"
                        }
    except Exception as e:
        logger.warning(f"維基百科檢索公司照片失敗: {e}")

    logger.info(f"未檢索到公司 [{clean_name}] 之合格照片，啟動平滑降級（不附照片）。")
    return None


def get_newsletter_images(story_data: dict) -> dict:
    """
    一站式收集電子報所需的所有圖片資產字典：
    - company_photo: 商業故事公司代表照片 (動態檢索)
    - vocab_photo: 英語區商務單字字典圖 (本機 dictionary_Photo)
    - german_photo: 德語區字典圖 (本機 German-Dictionary)
    注意：不包含英文商業諺語區。

    Returns:
        dict: {
            "company_photo": dict or None,
            "vocab_photo": dict or None,
            "german_photo": dict or None
        }
    """
    company_name = story_data.get("company_name", "")
    stock_id = ""
    # 嘗試從 company_name 提取代號
    match = re.search(r'[\(（](\d{4,5})[\)）]', company_name)
    if match:
        stock_id = match.group(1)

    images = {
        "company_photo": fetch_company_photo(company_name, stock_id),
        "vocab_photo": resolve_local_image("dictionary_Photo"),
        "german_photo": resolve_local_image("German-Dictionary")
    }
    return images
