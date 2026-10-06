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
* **目前監測新聞來源**:
  * 鉅亨網
  * 科技新報
  * 數位時代
  * BBC Business
  * TechCrunch
  * Google News (財經)
  * 經濟日報
  * Yahoo財經
  * The Wall Street Journal
  * CNN Markets
* **運作流程**:
  1. 透過 RSS 爬蟲抓取各大商業/科技媒體的最新新聞。
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
* **晚間金融名詞解析**: 執行 `python run_finance_term.py` (已設定 GitHub Actions 每日 18:07 執行)
* **啟動 API 伺服器**: 執行 `python api_server.py`

## 環境變數 (.env)
系統依賴多個外部服務，需要設定以下環境變數：
- `OPENAI_API_KEY` 或 `GEMINI_API_KEY`: 用於內容分析與生成。
- `TAVILY_API_KEY`: 用於公司背景資料與競品搜尋。
- `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: 用於自動發送產出結果。
- `DATABASE_URL`: (可選) 資料庫路徑。

## 更新日誌 (Changelog)
* **Gmail 草稿 GitHub Actions 整合 (CI Gmail Draft)**:
  * **Workflow 自動注入 OAuth 憑證**: 修改 `daily_report.yml`，新增步驟將 `GMAIL_CREDENTIALS` 與 `GMAIL_TOKEN` 兩個 GitHub Secrets 還原為 `credentials.json` / `token.json` 檔案，使 Gmail 草稿功能在 GitHub Actions 環境中也能正常運作。
  * **Docker 專用授權腳本**: 新增 `setup_gmail_docker.py`，支援在 Docker 容器中透過 port mapping (`-p 8080:8080`) 完成 OAuth 授權。授權成功後，腳本會自動輸出 `token.json` 與 `credentials.json` 的內容，方便使用者直接複製貼上設定 GitHub Secrets。
* **視覺化面板 UI 更新**: 於 InsightOrbit 前端介面的新聞圓圈 (Orbit) 展開狀態下，新增「跳轉看新聞」按鈕，允許使用者直接導向原始新聞網頁。
* **晚間專業金融詞彙解析 (自動排程)**: 新增 `run_finance_term.py` 模組，透過 GitHub Actions 設定於台灣時間 18:07 自動觸發。系統會自動讀取當日新聞脈絡作為 LLM Prompt，並具備「防重複記憶機制」（記錄於資料庫 `vocabulary_history`），確保每日推送全新未解析過的金融術語。
* **新聞來源擴充**: 將原本的 RSS 監測名單擴充，加入「經濟日報」、「Yahoo財經」、「The Wall Street Journal」與「CNN Markets」。
* **API 穩定度升級**: 將原本僅用於「商業故事」模組的 Gemini API 自動重試機制 (`_call_gemini_with_retry`) 重構為通用架構，並擴大套用於「新聞 Top 3 篩選」與「標籤科普生成」等核心 LLM 呼叫。現在系統在面對尖峰時刻的 503 錯誤與網路延遲時，會自動採取指數退避 (Exponential Backoff) 策略進行至多 6 次重試，大幅提升了每日發文自動化的穩定度與抗壓性。
* **API 模型降級防護與效能雙重優化**:
  * **雙層防護重試機制 (Two-Tier Resilience)**: 針對 Gemini API 經常發生的 `429 流量限制` 與 `404 模型下架` 錯誤，導入了「內層模型無縫切換（退而求其次）」與「外層 Tenacity 指數退避等待」的雙層防護機制。同時更新了最新可用的 Gemini 模型輪詢清單 (包含 `3.7-flash`, `3.8-flash`, `flash-latest` 等)，確保在單一模型額度耗盡時，腳本能自動跳轉至備用模型繼續執行，達到真正的無人值守穩定性。
  * **科普標籤批次生成 (Batch Generation)**: 將每日新聞與商業故事中的標籤 (Tags) 與延伸關鍵字的科普知識抓取方式，從以往的「逐一單獨呼叫 API」重構為「批次打包請求」。此舉大幅減少了高達 80% 的 API 呼叫次數，完美解決了舊版腳本因單日生成過多標籤，極易觸發 Google API 專案級別每日免費額度上限 (1500 RPD) 的問題。
* **Gmail 每日時務商報草稿自動生成 (Gmail Draft Integration)**:
  * **自動化電子報整併**: 將原本分開的「商業故事」與「每日 Top 3 新聞」整合，並完全復刻使用者原始的 `.eml` 信件範本排版風格（包含字體顏色、橘色超連結新聞標題等）。系統完成 Telegram 推播後，會利用 Gmail API 在使用者的信箱中自動建立草稿。
  * **OAuth 2.0 一次性授權**: 新增 `setup_gmail_auth.py` 授權腳本，支援本機或 Docker 環境。完成首次 Google 授權後，系統將自動保存 `token.json`，後續執行 `main.py` 即可達到無人值守、全自動草稿建立的目標。
* **內容品質與 Token 最佳化 (Deduplication & Context Optimization)**:
  * **歷史新聞查重與後續報導識別**: 在挑選 Top 3 新聞前，系統會自動預載過去 48 小時的歷史新聞標題。LLM 具備自動判斷能力，能將「純粹因新聞台較晚發布的重複內容」權重降為零直接淘汰，而若是「同一事件但具備新人物發言或後續新進展」的報導則保留權重。
  * **單字防呆與後驗證機制 (Post-validation)**: 為了解決商業單字重複問題，並避免原本塞入全量歷史單字導致的 Prompt 過長問題，導入了精準後驗證機制。現在主 Prompt 僅提供最近 5 筆單字減輕 AI 負擔，待產出結果後由後端程式即時比對資料庫 (`ILIKE` 精確比對)。若不幸發生單字、諺語或德文重複，系統會觸發一次輕量級的重試 API 單獨替換該欄位，確保內容百分之百全新。
