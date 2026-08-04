# 自動化內容行銷（Content Automation）流程

這是一個非常經典且效益極高的自動化內容行銷流程，目標是建立一個**每日定時執行的自動化工作流程**，用來自動產出並發佈 LinkedIn 文章。

## 系統架構與流程設計

整體架構包含四個主要模組：**資料抓取 $\rightarrow$ 資訊整理與 AI 分析 $\rightarrow$ 產出 LinkedIn 文章 $\rightarrow$ 自動或半自動發佈**。

```text
[ 定時觸發 (Cron Job) ]
       │
       ▼
[ 1. 上市櫃公司輪播邏輯 ] ──(傳入公司代碼)
       │
       ▼
[ 2. 資料爬蟲/API 模組 ] ──(抓取 財務、新聞、競品資料)
       │
       ▼
[ 3. LLM AI 分析模組 (GPT-4o / Gemini) ] ──(進行摘要與競品對比)
       │
       ▼
[ 4. LinkedIn 文章生成器 ] ──(輸出 Hook + 內文 + Hashtags)
       │
       ▼
[ 5. 排程發佈 / Telegram 審核推送 ]
```

## 步驟一：資料來源與爬取方式（Data Gathering）

對於台灣上市櫃公司（TWSE / TPEx），**儘量優先使用公開 API，真的沒有才用爬蟲**，以確保系統穩定。

1. **基本資料與財務數據**：
   * **公開資訊觀測站 (MOPS)**：有提供官方 API，或可爬取其標準頁面。
   * **台灣證券交易所 (TWSE) OpenAPI**：提供每日收盤、公司基本資料、產業分類等 API，完全免費且不用爬蟲。
   * **第三方金融 API**：例如 `FinMind`（提供 Python SDK，非常適合抓取台股財務報表與基本面）。

2. **競品分析與最新動態**：
   * **Google News RSS / SerpAPI**：輸入 `公司名稱 + 競品/競爭對手` 或是 `公司名稱 + 產業` 抓取最新新聞。
   * **Tavily API / Perplexity API**：這類專為 AI 設計的搜尋 API 非常適合拿來做「競品搜尋」，可以直接傳回網路整理好的競爭對手與產業地位。

## 步驟二：串接 LLM（AI）進行競品分析與文案生成

拿到原始資料（營收、產品、新聞）後，將資料丟給 LLM（如 OpenAI API 或 Google Gemini API），並透過 Prompt 進行處理：

### 核心 Prompt 範例：

> 「你是一位資深的產業與股票分析師。請根據以下這家上市櫃公司的資料：
> 【公司資料】：{company_info}
> 【競品與新聞】：{competitor_info}
> 
> 請幫我撰寫一篇適合發在 LinkedIn 的商業剖析文章。格式要求：
> 1. **Hook (前兩行)**：用一個強烈的商業洞察或數據吸引點擊。
> 2. **公司核心業務**：一句話講清楚這家公司靠什麼賺錢。
> 3. **競品對比與護城河**：與主要競爭對手相比，它的優劣勢是什麼？
> 4. **個人觀點/未來看點**：3 個條列式的商業洞察。
> 5. **互動結尾 + 3-5 個相關 Hashtags**。」

## 步驟三：自動化排程與發佈機制

要讓這套程序「每天」自己跑，有兩種實現途徑：

### 途徑 A：全程式碼實作（適合作者有程式背景）

* **託播平台**：使用 **GitHub Actions**（免費）或 **Google Cloud Run / AWS Lambda** 搭配 Cron 排程。
* **發佈至 LinkedIn**：
  * **LinkedIn API**：可以申請 LinkedIn Share API 直接自動 Po 文。
  * *建議替代方案（半自動/人為審核）*：程式跑完後，將產出的文章自動發到你的 **Telegram Bot** 或 **Discord**，點擊確認無誤後，再一鍵複製發到 LinkedIn（避免 AI 產生幻覺發出錯誤資料）。

### 途徑 B：無程式碼 / 低程式碼工具（No-Code Automation）

可以使用 **Make.com** 或 **Zapier**：

1. **Google Sheets**：建一份上市櫃公司清單（清單包含台股代號）。
2. **Make.com 排程**：每天抓取清單中的下一家公司。
3. **HTTP / Webhook 模組**：打 FinMind / Google News API 拿資料。
4. **OpenAI 模組**：自動生成 LinkedIn 文章。
5. **LinkedIn 模組**：自動將產出的內容發佈到你的 LinkedIn 個人頁面。

## 實作範例：Python 自動化腳本

這個腳本模擬了完整的工作流程：**讀取目標公司 $\rightarrow$ 透過免費 API 抓取基本面資料 $\rightarrow$ 呼叫 OpenAI 生成 LinkedIn 貼文 $\rightarrow$ 發送至你的 Telegram Bot 供你審核**。

### 預先準備作業

在運行腳本前，你需要準備以下金鑰（API Keys）：

1. **OpenAI API Key**：用於生成貼文。
2. **Telegram Bot Token & Chat ID**：
   * 在 Telegram 搜尋 `@BotFather` 建立一個新 Bot 並取得 `TOKEN`。
   * 開啟與新 Bot 的對話並發送任意訊息。
   * 搜尋 `@userinfobot` 取得你的 `Chat ID`。
3. **安裝依賴套件**：
   ```bash
   pip install requests openai
   ```

### Python 腳本範例 (`company_to_linkedin.py`)

```python
import os
import requests
from openai import OpenAI

# ==========================================
# 1. 設定 API 金鑰與參數
# ==========================================
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

client = OpenAI(api_key=OPENAI_API_KEY)

# 本次要分析的目標台股公司 (例如：2330 台積電)
STOCK_ID = "2330"

# ==========================================
# 2. 抓取公司基本資料 (使用 FinMind 免費 API)
# ==========================================
def fetch_company_data(stock_id):
    """從 FinMind API 抓取公司基本資訊與最新月營收數據"""
    print(f"正在抓取股票代號 {stock_id} 的資料...")
    
    # 抓取公司基本資訊
    info_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo&data_id={stock_id}"
    res_info = requests.get(info_url).json()
    
    if not res_info.get("data"):
        return None
    
    info_data = res_info["data"][0]
    
    company_name = info_data.get("stock_name", "未知公司")
    industry = info_data.get("industry_category", "通用產業")
    
    # 這裡可以擴充抓取新聞、財務報表等數據，這裡簡化傳回核心欄位
    return {
        "stock_id": stock_id,
        "company_name": company_name,
        "industry": industry,
    }

# ==========================================
# 3. 呼叫 OpenAI 生成 LinkedIn 貼文草稿
# ==========================================
def generate_linkedin_post(company_data):
    """利用 GPT-4o 將公司資料與競品分析架構轉換為 LinkedIn 貼文"""
    print("正在透過 OpenAI 生成 LinkedIn 貼文草稿...")
    
    prompt = f"""
你是一位專業的科技與金融產業分析師，擅長在 LinkedIn 發布深入淺出的商業洞察。

請針對以下這間台灣上市櫃公司，撰寫一篇吸引人的 LinkedIn 繁體中文貼文草稿：

【公司基本資料】
- 公司名稱：{company_data['company_name']} ({company_data['stock_id']})
- 所屬產業：{company_data['industry']}

【撰寫要求與架構】
1. **Hook (前兩行)**：用一個強烈、有洞察力的商業提問或現狀切入，吸引讀者點開「看更多」。
2. **核心業務**：簡明扼要說明該公司在產業鏈中的關鍵角色與獲利模式。
3. **競品對比與護城河 (請根據你的知識庫補充)**：
   - 點出主要競爭對手（國內或國際競品）。
   - 分析這家公司相較於競品的關鍵優勢或技術護城河。
4. **個人觀點**：列出 2-3 個未來的商業看點或面臨的挑戰（使用 Bullet points）。
5. **結尾互動**：拋出一個問題引導讀者在留言區討論。
6. **Hashtags**：附上 3~5 個適當的標籤（例如：#台股分析 #商業洞察）。

語氣要求：專業、理性、具啟發性，適度運用 Emoji 增加排版可讀性。
"""

    response = client.chat.completions.create(
        model="gpt-4o",  # 可依需求替換為 gpt-4o-mini
        messages=[
            {"role": "system", "content": "你是一位資深的產業分析師與社群內容創作者。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content

# ==========================================
# 4. 發送貼文草稿至 Telegram Bot
# ==========================================
def send_to_telegram(message):
    """將生成的草稿傳送到 Telegram 進行人工審核"""
    print("正在發送至 Telegram Bot...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # 加上標頭提醒這是每日自動生成草稿
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🚀 **每日 LinkedIn 貼文草稿生成成功！**\n\n{message}",
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("✅ 已成功發送到 Telegram！")
    else:
        print(f"❌ Telegram 發送失敗: {response.text}")

# ==========================================
# 5. 主程式進入點
# ==========================================
if __name__ == "__main__":
    # 1. 抓取資料
    data = fetch_company_data(STOCK_ID)
    
    if data:
        # 2. 生成文案
        post_draft = generate_linkedin_post(data)
        
        # 3. 發送至 Telegram
        send_to_telegram(post_draft)
    else:
        print("無法取得公司資料，請確認股票代號是否正確。")
```

## 💡 專家與進階延伸建議

1. **避免純自動發佈（Human-in-the-loop）**：
   上市櫃公司的數據（特別是財務數據與競品名稱）極度要求準確度。建議讓程式每天寫好草稿推送到你的通訊軟體（如 Telegram Bot），花 30 秒花眼神過一遍確認沒錯再發布，內容品質會高很多。
2. **輪播機制 (Company Rotation)**：
   台股有上千家公司，您可以建立一個包含「市值前 100 大」或「熱門半導體/AI概念股」的 JSON/CSV 檔，每天腳本執行時自動讀取「下一家」公司的代號，輪完一圈後再重新循環。
3. **免費自動化排程 (GitHub Actions)**：
   您可以將此 Python 腳本放上 GitHub 個人儲存庫，並設定 `.github/workflows/daily_post.yml` 檔，利用 GitHub Actions 的 **Cron 觸發器** 免費在每天固定時間執行（例如每天早上 8:00）。
4. **擴充資料豐富度**：
   在 `fetch_company_data` 函數中，可加入 `Tavily API` 或 `SerpAPI` 抓取當週最新的該公司財報新聞，並一併餵給 GPT-4o，能讓生成的文章具備當下最新時事熱點。
5. **LinkedIn 演算法友情提示**：
   LinkedIn 演算法非常不喜歡純外連連結。如果文章中要附上公司官網或新聞來源，請放在**留言區（Comments）**，不要放在正文裡面，觸及率會高很多。
