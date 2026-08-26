import requests
import json

def test_key(key_name, api_key):
    print(f"測試 {key_name}...")
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent'
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }
    payload = {
        "contents": [{"parts": [{"text": "hi"}]}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"HTTP 狀態碼: {response.status_code}")
    if response.status_code == 200:
        print("Success! The key is valid.")
    else:
        print("Failed! Error message:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print("-" * 50)

if __name__ == "__main__":
    # 來自【英語練習機器人】的 Key
    english_bot_key = "YOUR_API_KEY_HERE"
    # 你剛剛第三次截圖建立的新 Key (Project: 272649053632)
    new_business_key = "YOUR_API_KEY_HERE"
    
    test_key("【英語練習機器人】的 AQ 金鑰", english_bot_key)
    test_key("【第三次截圖全新專案】的 AQ 金鑰", new_business_key)
