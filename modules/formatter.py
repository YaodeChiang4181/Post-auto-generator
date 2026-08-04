from datetime import datetime

def format_daily_report(company_data, news_content, story_content):
    """
    將公司基本資料與新聞內容整理為結構化的每日報告字串，準備發送至 Telegram。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    company_name = company_data.get('company_name', '未知公司')
    stock_id = company_data.get('stock_id', '未知代碼')
    industry = company_data.get('industry', '未知產業')
    
    # 建立報告標題與基本資訊
    report = f"📊 【{company_name} ({stock_id}) 每日資訊彙整】\n"
    report += f"📅 日期：{today}\n"
    report += f"🏢 產業別：{industry}\n"
    report += "-" * 20 + "\n\n"
    
    # 加入故事資訊
    report += "📖 【公司商業故事 / 發展背景】\n"
    if not story_content or story_content.strip() == "":
        report += "無相關商業故事。\n"
    else:
        report += f"{story_content}\n"
    report += "\n"
    
    # 加入新聞資訊
    report += "📰 【最新商業新聞與動態】\n"
    if not news_content or news_content.strip() == "":
        report += "目前無最新重大新聞。\n"
    else:
        report += f"{news_content}\n"
        
    report += "\n" + "-" * 20 + "\n"
    report += "💡 本報告由自動化腳本產生，無 AI 介入"
    
    return report
