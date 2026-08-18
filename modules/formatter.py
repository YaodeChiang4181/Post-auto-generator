from modules.llm_api import summarize_with_llm

def format_daily_report(company_data, metrics):
    """
    將公司基本資料與搜尋結果透過 LLM 整理為結構化的每日報告字串。
    若 LLM 呼叫失敗，將回傳 None，交由 main.py 處理。
    """
    return summarize_with_llm(company_data, metrics)
