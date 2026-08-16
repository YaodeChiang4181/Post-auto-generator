from datetime import datetime

def format_daily_report(company_data, metrics):
    """
    將公司基本資料與搜尋結果整理為結構化的每日報告字串，準備發送至 Telegram。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    comp_name = company_data.get('name', '未知公司')
    stock_id = company_data.get('stock_id', '未知代碼')
    market = company_data.get('market', '未知市場')
    industry = company_data.get('industry', '未知產業')
    capital = company_data.get('capital', '未知')
    chairman = company_data.get('chairman', '未知')
    
    # 建立報告標題與基本資訊
    report = f"📊 【{comp_name} ({stock_id} {market}) 每日資訊彙整】\n"
    report += f"📅 日期：{today}\n"
    report += f"🏢 產業別：{industry}\n"
    report += "-" * 20 + "\n\n"

    # 1. 資本額
    report += "💰 1. 資本額\n"
    report += f"- 實收資本額：{capital} (資料來源: 政府開放資料)\n\n"

    # 2. 護城河
    report += "🏰 2. 護城河\n"
    report += f"{metrics.get('moat', '[資料不足]')}\n\n"

    # 3. 創業故事/背景/董事長創業故事/公司起源
    report += "📖 3. 創業故事/背景/董事長創業故事/公司起源\n"
    report += f"{metrics.get('story', '[資料不足]')}\n\n"

    # 4. 產品
    report += "📦 4. 產品\n"
    report += f"{metrics.get('products', '[資料不足]')}\n\n"

    # 5. 深耕領域
    report += "🌱 5. 深耕領域\n"
    report += f"{metrics.get('fields', '[資料不足]')}\n\n"

    # 6. 困境/未來挑戰
    report += "⚠️ 6. 困境/未來挑戰\n"
    report += f"{metrics.get('challenges', '[資料不足]')}\n"
    
    report += "\n" + "-" * 20 + "\n"
    report += "💡 本報告由自動化腳本直接透過搜尋引擎擷取，未經 AI 重組，請自主評估資料準確性。"
    
    return report
