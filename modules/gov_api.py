import requests
import random
import json
from logger import get_logger

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)

def get_random_company():
    """
    從政府開放資料平台抓取上市 (TWSE) 與上櫃 (TPEx) 公司名單，
    並隨機抽取一間公司，返回其基本資料字典。
    """
    logger.info("Fetching TWSE and TPEx company lists from Gov OpenAPI...")
    all_companies = []
    
    # 1. 抓取上市公司 (TWSE)
    twse_url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
    try:
        res_twse = requests.get(twse_url, timeout=15)
        res_twse.encoding = 'utf-8'  # 強制使用 utf-8 避免亂碼
        twse_data = res_twse.json()
        
        for item in twse_data:
            stock_id = item.get("公司代號", "").strip()
            name = item.get("公司名稱", "").strip()
            if stock_id and name:
                all_companies.append({
                    "stock_id": stock_id,
                    "name": name,
                    "market": "上市",
                    "industry": item.get("產業別", "未知"),
                    "capital": item.get("實收資本額", "未知"),
                    "chairman": item.get("董事長", "未知"),
                    "found_date": item.get("成立日期", "未知")
                })
        logger.info(f"Loaded {len(twse_data)} TWSE companies.")
    except Exception as e:
        logger.error(f"Error fetching TWSE data: {e}")

    # 2. 抓取上櫃公司 (TPEx)
    tpex_url = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
    try:
        res_tpex = requests.get(tpex_url, timeout=15, verify=False)
        res_tpex.encoding = 'utf-8'
        tpex_data = res_tpex.json()
        
        for item in tpex_data:
            # TPEx 的欄位是英文的
            stock_id = item.get("SecuritiesCompanyCode", "").strip()
            name = item.get("CompanyName", "").strip()
            if stock_id and name:
                all_companies.append({
                    "stock_id": stock_id,
                    "name": name,
                    "market": "上櫃",
                    "industry": item.get("SecuritiesIndustryCode", "未知"),
                    "capital": item.get("Paidin.Capital.NTDollars", "未知"),
                    "chairman": item.get("Chairman", "未知"),
                    "found_date": item.get("DateOfIncorporation", "未知")
                })
        logger.info(f"Loaded {len(tpex_data)} TPEx companies.")
    except Exception as e:
        logger.error(f"Error fetching TPEx data: {e}")

    if not all_companies:
        logger.error("Failed to load any companies from Gov OpenAPI.")
        return None

    # 3. 隨機抽取一間
    chosen_company = random.choice(all_companies)
    logger.info(f"Randomly chosen company: {chosen_company['name']} ({chosen_company['stock_id']})")
    
    return chosen_company
