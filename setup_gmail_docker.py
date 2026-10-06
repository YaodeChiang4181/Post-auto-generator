"""
Gmail OAuth 授權腳本 (Docker / 無瀏覽器環境專用)
====================================================
在 Docker 容器中完成 Gmail OAuth 授權並生成 token.json。
容器需要 expose port 8080，讓本機瀏覽器的 redirect 能打回容器。

使用方式 (Docker)：
    docker compose run --rm -p 8080:8080 app python setup_gmail_docker.py

使用方式 (本機)：
    python setup_gmail_docker.py

步驟：
    1. 確保 credentials.json 已放在專案根目錄
    2. 用上述指令啟動容器
    3. 複製終端機顯示的 URL，貼到瀏覽器中開啟
    4. 完成 Google 授權後會自動 redirect 回 localhost:8080
    5. token.json 會自動生成在專案根目錄（因為有 volume mapping）

產出 token.json 後，需將其內容設定為 GitHub Secret：
    - Secret 名稱：GMAIL_TOKEN
    - 同時也需要將 credentials.json 內容設為：GMAIL_CREDENTIALS
"""

import sys
import os
import json

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

print("=" * 60)
print("  Gmail OAuth 授權 (Docker / 無瀏覽器環境)")
print("=" * 60)
print()

# 判斷是否在 Docker 容器中
is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)

if is_docker:
    print("🐳 偵測到 Docker 環境")
    print("   請確認你已用以下指令啟動：")
    print("   docker compose run --rm -p 8080:8080 app python setup_gmail_docker.py")
    print()

print("🚀 開始授權流程...")
print("   請複製下方出現的網址，貼到你的瀏覽器中開啟。")
print("   完成 Google 授權後，會自動 redirect 回來。")
print()

flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)

# Docker 環境用 0.0.0.0 綁定，讓 host 的 port mapping 生效
# 本機環境用 localhost
bind_host = '0.0.0.0' if is_docker else 'localhost'

creds = flow.run_local_server(
    host=bind_host,
    port=8080,
    open_browser=False,
)

with open(TOKEN_FILE, 'w') as token:
    token.write(creds.to_json())

print()
print(f"✅ 授權成功！token.json 已儲存至：{TOKEN_FILE}")
print()
print("=" * 60)
print("  接下來，請將檔案內容設定為 GitHub Secret")
print("=" * 60)
print()

# 讀取檔案內容供複製
with open(TOKEN_FILE, 'r') as f:
    token_content = f.read()

with open(credentials_path, 'r') as f:
    creds_content = f.read()

print("📋 請到 GitHub Repo → Settings → Secrets and variables → Actions")
print("   新增以下兩個 Repository Secrets：")
print()
print("─" * 50)
print("📌 Secret 名稱: GMAIL_CREDENTIALS")
print("   Secret 值 (複製 credentials.json 的完整內容):")
print("─" * 50)
print(creds_content.strip())
print()
print("─" * 50)
print("📌 Secret 名稱: GMAIL_TOKEN")
print("   Secret 值 (複製 token.json 的完整內容):")
print("─" * 50)
print(token_content.strip())
print()
print("✅ 完成上述設定後，GitHub Actions 就能自動建立 Gmail 草稿了！")
