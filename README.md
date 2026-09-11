# 每日商業故事 - 貼文自動產出腳本系統 (InsightOrbit)

這是一個自動化內容行銷系統，主要用於自動產出並發佈商業分析文章與重大新聞快訊。系統包含資料抓取、LLM 分析生成、資料儲存與 API 伺服器等功能。

## 系統架構與核心功能

本系統分為三大核心模組：

### 1. 每日商業故事自動產出 (Business Story)
* **核心檔案**: `main.py`, `modules/gov_api.py`, `modules/news_api.py`, `modules/formatter.py`
* **運作流程**: 
  1. 透過政府公開資料 API 隨機挑選一家台灣上市櫃公司。
  2. 使用 Tavily API 搜尋該公司的 8 大維度指標 (如財報、最新動態、競品分析)。
  3. 呼叫 LLM (如 Gemini/OpenAI) 將資料彙整，並自動加上每日單字 (Vocabulary)、名言佳句 (Proverb) 與德文單字 (German word) 作為商業故事。
  4. 產生 HTML 格式報表並透過 Telegram Bot 發送。

### 2. 重大新聞快訊 Top 3 (InsightOrbit News Automation)
* **核心檔案**: `main.py`, `run_news.py`, `modules/news_aggregator.py`, `modules/llm_api.py`
* **運作流程**:
  1. 透過 RSS 爬蟲抓取各大商業/科技媒體 (如鉅亨網、科技新報、數位時代、TechCrunch 等) 的最新新聞。
  2. **時間過濾**：篩選出過去 24 小時內發布的新聞。
  3. 呼叫 LLM 從候選新聞中精選出 Top 3，並自動生成摘要、關鍵影響與分類標籤 (Tags)。
  4. 針對標籤呼叫 LLM 生成深度科普知識 (Glossary/Takeaway)，將結構化資料儲存至 SQLite 資料庫。
  5. 將最終結果發送到 Telegram。

### 3. InsightOrbit 視覺化 API 伺服器 (API Server)
* **核心檔案**: `api_server.py`, `templates/`
* **運作流程**:
  1. 基於 FastAPI 建立的後端伺服器。
  2. 提供 API 介面供前端 (Demo Panel) 讀取資料庫中的新聞與標籤知識圖譜 (Orbit Data & Tag Deep Dive)。
  3. 提供標籤動態生成 (On-the-fly) 與背景預先抓取 (Prefetch) 的功能。

## 執行與部署
* **完整執行 (商業故事 + 新聞)**: 執行 `python main.py`
* **僅執行新聞模組**: 執行 `python run_news.py`
* **啟動 API 伺服器**: 執行 `python api_server.py`

## 環境變數 (.env)
系統依賴多個外部服務，需要設定以下環境變數：
- `OPENAI_API_KEY` 或 `GEMINI_API_KEY`: 用於內容分析與生成。
- `TAVILY_API_KEY`: 用於公司背景資料與競品搜尋。
- `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: 用於自動發送產出結果。
- `DATABASE_URL`: (可選) 資料庫路徑。

## 更新日誌 (Changelog)
* **API 穩定度升級**: 將原本僅用於「商業故事」模組的 Gemini API 自動重試機制 (`_call_gemini_with_retry`) 重構為通用架構，並擴大套用於「新聞 Top 3 篩選」與「標籤科普生成」等核心 LLM 呼叫。現在系統在面對尖峰時刻的 503 錯誤與網路延遲時，會自動採取指數退避 (Exponential Backoff) 策略進行至多 6 次重試，大幅提升了每日發文自動化的穩定度與抗壓性。
