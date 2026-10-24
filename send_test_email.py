"""
【每日時務商報】即時發信功能驗證腳本
==========================================
不消耗 Tavily / Gemini API 額度，直接透過本地已授權的 token.json
發送一封完整的【每日時務商報】範例電子報至指定信箱，確認排版與發信正常。

使用方式：
    python send_test_email.py [收件人信箱，選填]
"""

import sys
import os
from dotenv import load_dotenv

# 確保 Windows 終端機能正確輸出 UTF-8 字元
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

from modules.gmail_sender import send_newsletter

def main():
    # 決定測試收件人
    recipient = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        recipient = sys.argv[1].strip()
    else:
        env_recipients = os.getenv("NEWSLETTER_RECIPIENTS", "")
        if env_recipients:
            recipient = env_recipients.split(",")[0].strip()

    if not recipient:
        print("❌ 未指定收件人！請透過參數指定，例如：")
        print("   python send_test_email.py your_email@gmail.com")
        sys.exit(1)

    # 讀取當前期數與篇數 (47, 63)
    try:
        from modules.state_manager import StateManager
        sm = StateManager()
        nl_issue, st_issue = sm.get_next_counters()
    except Exception:
        nl_issue, st_issue = 47, 63

    print("=" * 60)
    print(" 開始發送【每日時務商報】測試信件")
    print(f" 目標收件信箱: {recipient}")
    print(f" 預設期數: 第 {nl_issue} 期，商業故事篇數: 第 {st_issue} 篇")
    print("=" * 60)

    # 模擬一份簡約、無 Emoji、真實人文排版的範例資料
    sample_story = {
        "company_name": "系統測試專案（9999）",
        "story": "這是一篇排版驗證文章，展示簡約、無 Emoji、無 AI 產出感的經典報刊風格。\n\n**微米級製程與核心架構**全面上線，系統已具備無人值守排程能力。\n*今日排版重點*：經典報刊抬頭、標準橘色超連結、深藍色重點強調與雙相容降級文字。\n\n#系統上線 #全自動排程 #每日時務商報",
        "vocab": {
            "word": "seamless",
            "pos": "adj.",
            "pronunciation": "ˈsiːm.ləs",
            "definition": "無縫的、順暢的、天衣無縫的",
            "example": "The automated newsletter delivery system works in a seamless manner."
        },
        "proverb": {
            "text": "Well begun is half done.",
            "explanation": "好的開始是成功的一半。源自亞里斯多德的名言，代表妥善的準備是邁向成果的關鍵契機。",
            "usage": "完成全自動發信與簡約排版升級，為後續每日無人值守排程奠定了穩健基礎。"
        },
        "german": {
            "word": "der Erfolg",
            "pos": "m.",
            "pronunciation": "ɛɐ̯ˈfɔlk",
            "definition": "成功、成果",
            "example": "Das neu gestaltete System ist ein großer Erfolg."
        }
    }

    sample_news = {
        "top_news": [
            {
                "rank": 1,
                "title": "每日時務商報極簡排版與發信管線驗證",
                "source_url": "https://yaodechiang4181.github.io/Post-auto-generator/",
                "impact_reason": "驗證 Gmail API 直接發信管道暢通，橘色超連結與藍色強調字體皆完美呈現",
                "summary": "這是一則測試摘要。若您能在信箱中順利開啟並看到清晰報刊抬頭、無 Emoji 之專業排版與完整文字，代表您的 Gmail API 授權與排版引擎皆 100% 運作正常。",
                "tags": [{"name": "系統測試"}, {"name": "自動發信"}, {"name": "InsightOrbit"}]
            }
        ]
    }

    # 強制開啟發信設定進行測試 (不修改外部計數器)
    os.environ["EMAIL_AUTO_SEND"] = "true"
    os.environ["NEWSLETTER_RECIPIENTS"] = recipient
    os.environ["EMAIL_SEND_MODE"] = "individual"

    res = send_newsletter(sample_story, sample_news, issue_number=nl_issue, story_number=st_issue)

    print()
    if res.get("success") and res.get("mode") == "sent":
        print("發送成功！")
        print(f"   主旨: {res.get('subject')}")
        print(f"   已寄送給: {recipient}")
        print("   請至您的收件匣（或垃圾郵件匣確認）查看排版效果！")
    else:
        print("發送未完成或已切換為草稿，詳細結果:")
        print(res)

if __name__ == "__main__":
    main()
