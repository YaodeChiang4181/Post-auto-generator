from datetime import datetime

def format_daily_report(company_data, metrics):
    """
    將公司基本資料與 8 大維度的搜尋結果整理為結構化的每日報告字串，準備發送至 Telegram。
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

    # 1. 規模級別數據
    report += "🏢 1. 規模級別數據\n"
    report += f"- 實收資本額：{capital} (資料來源: 政府開放資料)\n"
    report += f"{metrics.get('scale', '[資料不足]')}\n\n"

    # 2. 市場影響力數據
    report += "🌍 2. 市場影響力數據 (市占率/客戶/合作夥伴)\n"
    report += f"{metrics.get('influence', '[資料不足]')}\n\n"

    # 3. 隱形冠軍屬性標籤
    report += "🏆 3. 隱形冠軍屬性標籤 (關鍵零組件/專利/龍頭)\n"
    report += f"{metrics.get('hidden_champ', '[資料不足]')}\n\n"

    # 4. 創辦人/關鍵人物的「印記事件」
    report += "👤 4. 關鍵人物印記 (董事長: {chairman})\n"
    report += f"{metrics.get('founder', '[資料不足]')}\n\n"

    # 5. 創業期極限生存故事
    report += "📖 5. 創業期極限生存故事\n"
    report += f"{metrics.get('survival', '[資料不足]')}\n\n"

    # 6. 護城河類型
    report += "🏰 6. 護城河類型 (規模經濟/進入障礙/品牌)\n"
    report += f"{metrics.get('moat', '[資料不足]')}\n\n"

    # 7. 市場獨佔性/不可替代性
    report += "🔒 7. 市場獨佔性/不可替代性\n"
    report += f"{metrics.get('monopoly', '[資料不足]')}\n\n"

    # 8. 外部危機與宏觀衝突
    report += "⚠️ 8. 外部危機與宏觀衝突\n"
    report += f"{metrics.get('crisis', '[資料不足]')}\n\n"

    # 最新新聞
    report += "📰 【今日最新新聞動態】\n"
    report += f"{metrics.get('latest_news', '目前無最新重大新聞。')}\n"
    
    report += "\n" + "-" * 20 + "\n"
    report += "💡 本報告由自動化腳本直接透過搜尋引擎擷取，未經 AI 重組，請自主評估資料準確性。"
    
    return report
