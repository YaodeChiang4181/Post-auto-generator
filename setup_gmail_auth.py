"""
Gmail OAuth 首次授權腳本
==============================
執行此腳本以完成 Gmail 授權，產生 token.json。
之後 main.py 會自動使用此 token，不需要再次授權。

步驟：
1. 從 Google Cloud Console 下載 credentials.json 並放於本專案根目錄
2. 執行此腳本: python setup_gmail_auth.py
3. 瀏覽器會自動開啟 Google 授權頁面，點擊允許
4. 授權完成後，token.json 會自動建立
"""

import sys
import os

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
    from google.oauth2.credentials import Credentials
except ImportError:
    print("❌ 缺少必要套件，請先執行：")
    print("   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')

print("🚀 開始 Gmail OAuth 授權流程...")
print("   瀏覽器即將開啟，請登入你的 Google 帳號並點擊「允許」")
print()

flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
creds = flow.run_local_server(port=0)

with open(TOKEN_FILE, 'w') as token:
    token.write(creds.to_json())

print()
print(f"✅ 授權成功！token.json 已儲存至：{TOKEN_FILE}")
print("   之後執行 main.py 時會自動使用此授權，無需重複操作。")
