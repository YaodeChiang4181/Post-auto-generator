"""
Gmail OAuth 授權腳本 (支援 Brave 瀏覽器與手動貼上繞過)
======================================================
執行此腳本以完成 Gmail 授權，產生 token.json。
之後 main.py 與 GitHub Actions 會自動使用此 token，不需要再次授權。

特色：
- 針對 Brave 瀏覽器設計：支援「網址列貼回」機制，即使 Brave 盾牌阻擋
  localhost 轉址或顯示「無法連線」，也能 100% 成功完成授權。
- 自動輸出 GitHub Secrets (GMAIL_TOKEN) 格式，方便複製設定。
"""

import sys
import os
import urllib.parse

# 確保 Windows 終端機能正確輸出 UTF-8 字元
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 允許 OAuthlib 處理 localhost 的 HTTP 回呼
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# 確認 credentials.json 存在
credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
if not os.path.exists(credentials_path):
    print("❌ 找不到 credentials.json！")
    print(f"   請前往 Google Cloud Console 下載 OAuth 2.0 用戶端憑證，")
    print(f"   並將檔案放置於：{credentials_path}")
    print()
    print("步驟：")
    print("  1. 前往 https://console.cloud.google.com/apis/credentials")
    print("  2. 找到你建立的 OAuth 2.0 用戶端 ID")
    print("  3. 點擊下載圖示，下載 JSON 檔")
    print("  4. 將檔案重新命名為 credentials.json 並放入本專案根目錄")
    sys.exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("❌ 缺少必要套件，請先執行：")
    print("   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')

print("=" * 65)
print("  Gmail OAuth 授權助手 (Brave 瀏覽器友善版)")
print("=" * 65)
print()
print("請選擇授權驗證模式：")
print("  [1] Brave / 手動複製貼上模式 (推薦！不受 Brave 盾牌或 localhost 阻擋影響)")
print("  [2] 自動本機伺服器模式 (適用於一般 Chrome/Edge 自動跳轉)")
print()

choice = input("請選擇模式 [預設 1]: ").strip()
if choice not in ['1', '2']:
    choice = '1'

if choice == '1':
    # 模式 1：手動網址貼回 (完全繞過 Brave 任何本地重定向與網路阻擋)
    REDIRECT_URI = 'http://localhost:8080/'
    flow = InstalledAppFlow.from_client_secrets_file(
        credentials_path,
        SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

    print()
    print("=" * 65)
    print("步驟 1：請複製下方網址，貼到瀏覽器 (Brave 或 Edge) 中開啟：")
    print("-" * 65)
    print(auth_url)
    print("-" * 65)
    print()
    print("💡【Brave 瀏覽器小提示】")
    print("  1. 若登入時 Google 顯示「此瀏覽器或應用程式可能不安全」：")
    print("     - 請點擊網址列右側的「獅子盾牌 (Brave Shields)」圖示，將防護切換為「關閉 (DOWN)」，然後重新整理。")
    print("     - 或者直接將上方網址貼至 Windows 內建的 Microsoft Edge 瀏覽器登入。")
    print("  2. 在 Google 頁面點擊「繼續」與「允許」完成授權。")
    print("  3. 授權後瀏覽器會嘗試跳轉至 http://localhost:8080/?state=...&code=...")
    print("     ⚠️ 此時 Brave 顯示「無法連線至此網站」或 ERR_SSL_PROTOCOL_ERROR 是完全正常的！")
    print("     請直接查看瀏覽器的【網址列】，將整串網址複製下來。")
    print()
    print("步驟 2：請將跳轉後的完整網址（或 code 授權碼）貼在下方：")
    
    user_input = input("👉 貼上網址或授權碼: ").strip()
    if not user_input:
        print("❌ 未輸入任何內容，授權中止。")
        sys.exit(1)

    # 解析 code
    if "code=" in user_input:
        parsed = urllib.parse.urlparse(user_input)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get('code', [None])[0]
        if not code:
            code = user_input
    else:
        code = user_input

    print()
    print("⏳ 正在向 Google 交換 Token，請稍候...")
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
    except Exception as e:
        print(f"❌ Token 交換失敗：{e}")
        print("請確認貼上的網址是否完整，或重新執行此腳本嘗試。")
        sys.exit(1)

else:
    # 模式 2：自動監聽伺服器
    print()
    print("🚀 啟動本機伺服器中...")
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=False)

# 儲存 token.json
with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
    token.write(creds.to_json())

print()
print("=" * 65)
print(f"🎉 授權成功！token.json 已儲存至：{TOKEN_FILE}")
print("=" * 65)
print()
print("📋【下一步：更新 GitHub Secrets】")
print("如果你需要在 GitHub Actions 自動化中建立 Gmail 草稿，請執行：")
print("  1. 前往 GitHub Repository -> Settings -> Secrets and variables -> Actions")
print("  2. 找到或新增 Secret: GMAIL_TOKEN")
print("  3. 將下方框框內的完整 JSON 內容複製貼上儲存：")
print("-" * 65)
with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
    print(f.read().strip())
print("-" * 65)
print("完成！之後 GitHub Actions 與本地端 main.py 都能自動發送草稿。")
