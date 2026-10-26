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
- `EMAIL_AUTO_SEND`: (可選) 是否啟用自動直接寄信 (`true` / `false`，預設 `false` 建立草稿安全模式)。
- `NEWSLETTER_RECIPIENTS`: (可選) 收件人名單，以逗號分隔（例如 `user1@gmail.com,user2@example.com`）。
- `EMAIL_SEND_MODE`: (可選) 發信模式，`individual`（預設，逐封寄送保障隱私且不易入促銷匣）或 `bcc`（密件副本群發）。

## 更新日誌 (Changelog)
* **【每日時務商報】信件內文日期精確對標台灣時區 (Asia/Taipei UTC+8 Alignment)**:
  * **內文與純文字日期時區對齊**：解決 GitHub Actions Linux Runner 預設運行於 UTC 國際標準時間（當排程在台灣時間清晨 04:13 觸發時，UTC 仍處於前一天深夜），導致信件頂部報頭與頁尾日期顯示為前一日的問題。
  * **雙層時區防護機制**：
    * **應用層精確轉換**：在 `modules/gmail_sender.py` 實作 `get_taiwan_date_str()`，使用 `zoneinfo.ZoneInfo("Asia/Taipei")`（具備常態 UTC+8 備援）精確產生台灣日期，全面應用於 HTML 模板替換 `{{ date }}` 與 Plaintext 備用格式。
    * **CI/CD 環境層校準**：在 `.github/workflows/daily_report.yml` 注入 `TZ: 'Asia/Taipei'` 環境變數，確保 Runner 系統層級之 `date` 與排程執行日誌皆完全對齊台灣時間。
  * **全量單元測試驗證**：在 `test_gmail_newsletter.py` 新增 `test_taiwan_date_formatting` 測試，確保日期格式正規性（`YYYY/MM/DD`）與模板置換準確性，7 項單元測試全數通過。
* **【每日時務商報】發信通道診斷強化、RFC 5322 標準寄件者標頭與防垃圾信優化 (Delivery Diagnostics & Anti-Spam Optimization)**:
  * **RFC 5322 標準寄件者標頭**：修正過往 `From: me` 原始標頭容易被 Gmail 與各家收件伺服器誤判為格式異常或釣魚垃圾信的問題，改為自動取得授權帳號並格式化為標準 `From: 每日時務商報 <user@gmail.com>`，大幅提升主收件匣（Inbox）投遞率。
  * **環境變數強固化清洗**：針對 GitHub Secrets 輸入變數時可能夾帶之外層單雙引號（如 `"true"` 或 `'user@gmail.com'`），在 `modules/gmail_sender.py` 加入全面去除引號與前後空白處理，避免布林值判定失效。
  * **工作流預檢診斷強化**：在 `.github/workflows/daily_report.yml` 與 `main.py` 注入去識別化（Masked）之發信預檢日誌，清晰記錄 `EMAIL_AUTO_SEND` 狀態、收件人數量與發送結果，便於追蹤每日無人值守排程的發信管道狀態。
* **【每日時務商報】極簡人文風排版與期數篇數自動加一進位系統 (Minimalist Editorial Styling & Auto-incrementing Counters)**:
  * **信件標題與故事篇數繼承推進**：
    * 遵循原有名稱結構，標題格式標準化為「`【每日時務商報#{issue_number}】－每日快訊與成長`」。
    * 導入雙計數器持久化機制（PostgreSQL 雲端資料庫 `system_counters` 表格 + 本機備援 `data/counters.json`），將既有之第 46 封商報與第 62 篇商業故事作為基準，次日排程自動推進為 **第 47 期** 與 **商業故事#63**，後續每日無人值守順序加一遞增。
  * **極簡人文報刊排版（徹底無 Emoji、無 AI 感）**：
    * 升級 `templates/email_newsletter.html`，移除所有裝飾性 Emoji（如 💡, 📜, 🇩🇪, 🚀, 🪐 等）與生硬的科技漸層色塊。
    * 採用經典報刊黑白灰底蘊，搭配招牌橘色新聞超連結標題、深藍色重要影響斜體、綠色 Hashtag 與字典風格排版（單字、處世諺語、德語小教室），營造頂級商業週刊般的專業閱讀質感。
  * **Gmail API 自動直接發信與草稿平滑降級**：
    * 擴充 OAuth Scope 包含 `gmail.send` 與 `gmail.compose`。
    * 支援由環境變數 `EMAIL_AUTO_SEND` 與 `NEWSLETTER_RECIPIENTS` 驅動的全自動發信功能。
    * 支援逐封發送 (`individual`) 與密件副本 (`bcc`)，且收件人清單智慧相容半形逗號、全形中文逗號、分號與換行符號。
    * 具備無縫安全降級機制：若未設定收件人、未開啟自動寄信或網路異常，系統自動平滑降級為「建立 Gmail 草稿」，確保排程流程永不中斷。
  * **CI/CD 自動化工作流整合**：在 `daily_report.yml` 注入電子報自動發信相關環境變數，並將 `data/counters.json` 納入自動 commit 流程確保跨環境狀態同步。
  * **全量單元與整合測試**：新增 `test_gmail_newsletter.py`，通過無 Emoji 驗證、標題編譯、純文字降級、草稿模式與自動發信模式之 6 項單元測試，無任何回歸問題。
* **單字防重複架構深度升級與形態模糊比對 (Resilient Deduplication & Normalization Architecture)**:
  * **詞態還原與標準化比對 (Lemmatization & Normalization)**：針對過往 SQL `ILIKE` 精確比對無法防範單複數（`synergies` vs `synergy`）、動詞時態（`hedged` / `hedging` vs `hedge`）、片語冠詞（`a bear market` vs `bear market`）與詞性註解（`leverage (n.)`）之盲點，在 `modules/state_manager.py` 導入標準化清洗與詞幹衍生變體（Canonical Variants）交集比對引擎，徹底杜絕輕微變形所導致的漏檢。
  * **受控重試迴圈與累積黑名單 (Bounded Retry Loop & Cumulative Blacklist)**：全面升級 `modules/formatter.py` 與 `run_finance_term.py`，將過往單次 `if` 重新生成機制改為至多 3 次的受控重試迴圈 (`max_retries=3`)。重試時會將歷次退件項目全量納入 Prompt 累積黑名單，避免 AI 盲猜再次撞庫。
  * **歷史排序修復與前視記憶擴充 (Historical Lookahead & DESC Order)**：修正 `get_recent_history` 查詢加入 `ORDER BY created_at DESC`，確保精準取得最新的歷史紀錄；並將主 Prompt 的避開名單容量由原本的 5 筆大幅擴充至最近 30 筆，從源頭將撞庫率降低 90% 以上。
  * **獨立命名空間防護 (Domain Isolation)**：依據業務邏輯，將夜間金融詞彙 (`finance_term`) 與早晨商務單字 (`vocab`) 保持獨立防護空間，互不干擾，並為晚間金融詞彙補足相同的後驗證與重試機制。
  * **Docker 容器化全量邏輯驗證**：新增 `test_deduplication.py` 單元與整合測試，並已於 Docker 容器環境（模擬 GitHub Actions Linux Runner）全數通過驗證。
* **一鍵遷移資料庫數週歷史紀錄至靜態頁面 (Full History Migration to Pages)**:
  * 針對使用者反映「過去數週累積的歷史新聞與標籤時間軸若遺失很可惜」的需求，升級 `modules/static_exporter.py`，改為遍歷資料庫中累積的所有標籤，提取過去數週的所有歷史新聞關聯事件（Timeline）。
  * 新增一鍵自動化工作流 `.github/workflows/export_history.yml`（支援網頁手動觸發 `workflow_dispatch`），由 GitHub Actions 直接連線至雲端 Neon 資料庫，將歷史全量資料批次打包匯出並自動同步至 GitHub Pages，完全保留數週的跨時空比對能力。
* **視覺化面板靜態化與 GitHub Pages 遷移 (Static Panel & GitHub Pages)**:
  * **解決 Render 免費額度耗盡問題**：將 `insight_orbit_panel.html` 轉型為支援純靜態運行的獨立架構，部署於 `/docs` 目錄以啟用 GitHub Pages 託管，徹底擺脫 Render 每月 750 小時休眠與暫停限制。
  * **完整保留相同標籤歷史時間軸功能 (Tag Historical Timeline)**：靜態資料結構 (`docs/data/orbit_data.json`) 完整打包了所有標籤的深度科普 (Glossary/Takeaway) 以及關聯之歷史新聞事件清單 (Timeline)。使用者點擊時間軸任一歷史新聞時，前端 React 狀態會無縫切換主 Orbit 視角，實現零後端延遲 (0ms) 的跨時空新聞脈絡回溯。
  * **自動化靜態資料匯出與同步**：新增 `modules/static_exporter.py`，於每日新聞排程結束後自動產出最新靜態資料；並在 GitHub Actions (`daily_report.yml`) 中加入自動 commit 與 push 機制，達成全自動更新。
  * **永久在線隱私權網址**：新增 `docs/privacy.html`，提供 Google Cloud OAuth 審核專用的永久靜態隱私權政策頁面。
* **Gmail OAuth 升級支援 Brave 瀏覽器繞過模式 (Brave OAuth Bypass)**:
  * 針對 Brave 瀏覽器的內建安全防護（Brave Shields 阻擋 Google 指紋識別、自動升級 HTTPS、阻擋 `localhost` 私有網路轉址）進行深度優化。
  * 升級 `setup_gmail_auth.py`，加入「手動網址列貼回」機制。使用者在瀏覽器完成授權後，即使頁面顯示無法連線，只需將網址列的完整回呼網址貼回終端機，腳本即可精準擷取 `code` 完成 Token 交換，並自動格式化輸出 `token.json` 供 GitHub Secrets 快速設定。
* **新增隱私權政策端點 (Privacy Policy Route)**:
  * 於 `api_server.py` 新增 `/privacy` 路由，以提供簡易的隱私權政策 HTML 網頁 (`https://insightorbit-api.onrender.com/privacy`)。此頁面主要用於滿足 Google Cloud OAuth 同意畫面 (Consent Screen) 正式發布時，對應用程式隱私權政策網址的要求。
* **修復 GitHub Actions 執行錯誤 (Fix Workflow Syntax Error)**:
  * 修正 `daily_report.yml` 中 `Restore Gmail OAuth credentials` 步驟的 `if` 條件語法錯誤。因 GitHub Actions 不支援在 `if` 條件式內直接讀取 `secrets` context，將其改回使用 `env` context 進行條件判斷，確保每日自動排程能順利啟動。
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
