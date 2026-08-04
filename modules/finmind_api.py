import requests
from logger import get_logger

logger = get_logger(__name__)

def fetch_company_data(stock_id):
    """
    從 FinMind API 抓取公司基本資訊
    """
    logger.info(f"Fetching basic info for stock_id: {stock_id}")
    
    info_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo&data_id={stock_id}"
    try:
        response = requests.get(info_url, timeout=10)
        response.raise_for_status()
        res_info = response.json()
        
        if not res_info.get("data"):
            logger.warning(f"No basic info found for {stock_id}")
            return None
            
        info_data = res_info["data"][0]
        
        company_name = info_data.get("stock_name", "未知公司")
        industry = info_data.get("industry_category", "通用產業")
        
        logger.info(f"Successfully fetched info for {company_name} ({stock_id})")
        return {
            "stock_id": stock_id,
            "company_name": company_name,
            "industry": industry,
        }
    except requests.RequestException as e:
        logger.error(f"Error fetching data from FinMind for {stock_id}: {e}")
        return None
