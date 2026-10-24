import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import re
from logger import get_logger

logger = get_logger(__name__)

# OAuth2 scopes: 支援自動直接發信 (gmail.send) 與建立草稿 (gmail.compose)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

# Paths for OAuth credential files
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'email_newsletter.html')


def _get_gmail_service():
    """
    取得已授權的 Gmail API 服務物件。
    若未授權或過期會自動嘗試使用 token.json 或重新刷新。
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        logger.error("缺少 Gmail API 套件，請執行: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        return None

    creds = None

    # 嘗試載入已快取的 token
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            logger.warning(f"載入 token.json 失敗，將重新授權: {e}")
            creds = None

    # 若 token 不存在或已失效，進行授權流程
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Gmail token 已自動刷新")
            except Exception as e:
                logger.warning(f"Token 刷新失敗，需重新授權: {e}")
                creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                logger.error(f"找不到 credentials.json，請從 Google Cloud Console 下載並放置於: {CREDENTIALS_FILE}")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info("Gmail OAuth 授權成功")
            except Exception as e:
                logger.error(f"執行本地 OAuth 伺服器授權失敗: {e}")
                return None

        # 儲存 token 供下次使用
        try:
            with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())
        except Exception as e:
            logger.warning(f"寫入 token.json 失敗: {e}")

    service = build('gmail', 'v1', credentials=creds)
    return service


def build_email_html(story_data: dict, news_data: dict, issue_number: int = None, subject: str = None) -> str:
    """
    組合【每日時務商報】現代化響應式 HTML 電子報內容。
    優先使用 templates/email_newsletter.html 模板。
    """
    today_str = datetime.now().strftime("%Y/%m/%d")
    company_name = story_data.get("company_name", "")
    issue_title = f"第 {issue_number} 期" if issue_number else "今日商報"
    actual_subject = subject or (f"【每日時務商報#{issue_number}】｜{today_str}" if issue_number else f"【每日時務商報】｜{today_str}")

    # --- 新聞區段 HTML ---
    news_items_html = ""
    for idx, item in enumerate(news_data.get("top_news", []), 1):
        rank = item.get("rank", idx)
        title = item.get("title", "")
        url = item.get("source_url", "#")
        impact = item.get("impact_reason", "")
        summary = item.get("summary", "")
        tags = item.get("tags", [])
        
        tags_html = "".join([f'<span class="tag-pill">#{t.get("name", t)}</span>' for t in tags])

        news_items_html += f"""
        <div class="news-card">
          <div class="news-title">
            <span style="color:#e67e22;font-weight:bold;margin-right:4px;">{rank}.</span>
            <a href="{url}" target="_blank">{title}</a>
          </div>
          <div class="news-impact">
            <strong>影響：</strong>{impact}
          </div>
          <div class="news-summary">
            <strong>摘要：</strong>{summary}
          </div>
          <div class="tags-container">
            {tags_html}
          </div>
        </div>
        """

    # --- 商業故事主文處理 ---
    story_raw = story_data.get("story", "")
    story_lines = story_raw.split("\n")
    story_html_lines = []
    for line in story_lines:
        stripped = line.strip()
        if not stripped:
            story_html_lines.append("<br>")
            continue

        is_hashtag = stripped.startswith("#")
        # 處理粗體與斜體
        stripped = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', stripped)
        stripped = re.sub(r'\*(.*?)\*', r'<span style="color:#2563eb"><i>\1</i></span>', stripped)
        stripped = re.sub(r'\b_(.*?)_\b', r'<span style="color:#2563eb"><i>\1</i></span>', stripped)

        if is_hashtag:
            story_html_lines.append(
                f'<div style="text-align:center;margin-top:12px;"><b><font color="#10b981">{stripped}</font></b></div>'
            )
        else:
            story_html_lines.append(
                f'<div style="margin:4px 0;">{stripped}</div>'
            )
    story_html = "\n".join(story_html_lines)

    # --- 單字、德語、諺語資料 ---
    vocab = story_data.get("vocab", {})
    german = story_data.get("german", {})
    proverb = story_data.get("proverb", {})

    vocab_word = vocab.get("word", "")
    vocab_pos = vocab.get("pos", "")
    vocab_pron = vocab.get("pronunciation", "")
    vocab_def = vocab.get("definition", "").replace("\n", "<br>")
    vocab_ex = vocab.get("example", "").replace("\n", "<br>")

    german_word = german.get("word", "")
    german_pos = german.get("pos", "")
    german_pron = german.get("pronunciation", "")
    german_def = german.get("definition", "")
    german_ex = german.get("example", "").replace("\n", "<br>")

    proverb_text = proverb.get("text", "")
    proverb_exp = proverb.get("explanation", "").replace("\n", "<br>")
    proverb_usage = proverb.get("usage", "").replace("\n", "<br>")

    # 讀取獨立模板
    if os.path.exists(TEMPLATE_FILE):
        try:
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                template_str = f.read()

            replacements = {
                "{{ subject }}": actual_subject,
                "{{ issue_title }}": issue_title,
                "{{ date }}": today_str,
                "{{ news_items_html }}": news_items_html,
                "{{ company_name }}": company_name,
                "{{ story_html }}": story_html,
                "{{ vocab_word }}": vocab_word,
                "{{ vocab_pos }}": vocab_pos,
                "{{ vocab_pron }}": vocab_pron,
                "{{ vocab_def }}": vocab_def,
                "{{ vocab_ex }}": vocab_ex,
                "{{ proverb_text }}": proverb_text,
                "{{ proverb_exp }}": proverb_exp,
                "{{ proverb_usage }}": proverb_usage,
                "{{ german_word }}": german_word,
                "{{ german_pos }}": german_pos,
                "{{ german_pron }}": german_pron,
                "{{ german_def }}": german_def,
                "{{ german_ex }}": german_ex,
            }
            for key, val in replacements.items():
                template_str = template_str.replace(key, str(val))
            return template_str
        except Exception as e:
            logger.warning(f"讀取 HTML 模板失敗，切換內建版面: {e}")

    # 內建備用版面
    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;line-height:1.6;color:#333;">
      <h1 style="color:#d97706;text-align:center;">{actual_subject}</h1>
      <p style="text-align:center;color:#666;">{today_str}</p>
      <hr style="border:none;border-top:2px solid #f59e0b;margin:20px 0;">
      <h2>每日重大新聞快訊 Top 3</h2>
      {news_items_html}
      <hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">
      <h2>商業故事：{company_name}</h2>
      {story_html}
      <hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">
      <h3>💡 今日商務單字: {vocab_word} ({vocab_pos})</h3>
      <p>{vocab_def}</p>
      <p><em>{vocab_ex}</em></p>
      <h3>📜 今日商業諺語</h3>
      <p><strong>{proverb_text}</strong></p>
      <p>{proverb_exp}</p>
      <h3>🇩🇪 德語小教室: {german_word} ({german_pos})</h3>
      <p>{german_def}</p>
      <p><em>{german_ex}</em></p>
    </div>
    """


def build_email_plaintext(story_data: dict, news_data: dict, issue_number: int = None, subject: str = None) -> str:
    """產生標準純文字版本 (Plain Text Fallback)"""
    today_str = datetime.now().strftime("%Y/%m/%d")
    company_name = story_data.get("company_name", "")
    actual_subject = subject or (f"【每日時務商報#{issue_number}】｜{today_str}" if issue_number else f"【每日時務商報】｜{today_str}")

    lines = [
        f"========================================",
        f" {actual_subject}",
        f" 日期：{today_str}",
        f"========================================\n",
        f"【每日重大新聞快訊 Top 3】\n"
    ]

    for idx, item in enumerate(news_data.get("top_news", []), 1):
        lines.append(f"{idx}. {item.get('title', '')}")
        lines.append(f"   連結: {item.get('source_url', '')}")
        lines.append(f"   影響: {item.get('impact_reason', '')}")
        lines.append(f"   摘要: {item.get('summary', '')}\n")

    lines.append(f"\n【今日深度商業故事：{company_name}】\n")
    lines.append(story_data.get("story", "").strip())

    vocab = story_data.get("vocab", {})
    lines.append(f"\n\n【今日商務單字】")
    lines.append(f"{vocab.get('word', '')} ({vocab.get('pos', '')}) /{vocab.get('pronunciation', '')}/")
    lines.append(f"釋義：{vocab.get('definition', '')}")
    lines.append(f"例句：{vocab.get('example', '')}")

    proverb = story_data.get("proverb", {})
    lines.append(f"\n【今日商業/處世諺語】")
    lines.append(f"{proverb.get('text', '')}")
    lines.append(f"解析：{proverb.get('explanation', '')}")
    lines.append(f"應用：{proverb.get('usage', '')}")

    german = story_data.get("german", {})
    lines.append(f"\n【德語小教室】")
    lines.append(f"{german.get('word', '')} ({german.get('pos', '')}) /{german.get('pronunciation', '')}/")
    lines.append(f"釋義：{german.get('definition', '')}")
    lines.append(f"例句：{german.get('example', '')}")

    lines.append(f"\n----------------------------------------")
    lines.append("【每日時務商報】· InsightOrbit 自動化生成系統")

    return "\n".join(lines)


def send_email_message(subject: str, html_body: str, to_email: str = None, bcc_emails: list = None, plain_body: str = None) -> bool:
    """
    透過 Gmail API 直接發送一封電子郵件 (支援 HTML 與 Plain Text 雙相容)。
    """
    service = _get_gmail_service()
    if not service:
        logger.error("無法取得 Gmail Service，寄信終止")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = 'me'

        if to_email:
            msg['To'] = to_email
        if bcc_emails:
            msg['Bcc'] = ", ".join(bcc_emails)

        # 附加純文字降級版本
        if plain_body:
            msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))

        # 附加 HTML 富文字內容
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        send_body = {'raw': raw}

        service.users().messages().send(userId='me', body=send_body).execute()
        return True
    except Exception as e:
        logger.error(f"發送郵件失敗 (To: {to_email}, Bcc: {bcc_emails}): {e}")
        return False


def create_gmail_draft(subject: str, html_body: str, plain_body: str = None) -> bool:
    """
    在 Gmail 中建立一封 HTML 格式草稿 (安全備援)。
    """
    service = _get_gmail_service()
    if not service:
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = 'me'

        if plain_body:
            msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        draft_body = {'message': {'raw': raw}}

        draft = service.users().drafts().create(userId='me', body=draft_body).execute()
        draft_id = draft.get('id', 'unknown')
        logger.info(f"Gmail 草稿建立成功！草稿 ID: {draft_id}")
        return True
    except Exception as e:
        logger.error(f"建立 Gmail 草稿失敗: {e}")
        return False


def send_newsletter(story_data: dict, news_data: dict, issue_number: int = None) -> dict:
    """
    【每日時務商報】整合發信入口：
    依據環境變數 (EMAIL_AUTO_SEND) 與收件人清單自動判定直接發送或建立草稿。
    若發送失敗自動安全降級為建立草稿。

    Returns:
        dict: {
            "mode": "sent" 或 "draft",
            "success": bool,
            "sent_count": int,
            "total_recipients": int,
            "subject": str
        }
    """
    today_str = datetime.now().strftime("%Y/%m/%d")

    # 確保信件標題格式標準化為【每日時務商報】
    if issue_number:
        subject = f"【每日時務商報#{issue_number}】｜{today_str}"
    else:
        subject = f"【每日時務商報】｜{today_str}"

    html_body = build_email_html(story_data, news_data, issue_number, subject)
    plain_body = build_email_plaintext(story_data, news_data, issue_number, subject)

    auto_send = os.getenv("EMAIL_AUTO_SEND", "false").lower() in ("true", "1", "yes")
    recipients_str = os.getenv("NEWSLETTER_RECIPIENTS", "")
    send_mode = os.getenv("EMAIL_SEND_MODE", "individual").lower()  # "individual" 或 "bcc"

    # 支援半形逗號 (,)、中文全形逗號 (，)、分號 (;) 或換行，防止輸入格式問題
    recipients = [r.strip() for r in re.split(r'[,，;\n\r]+', recipients_str) if r.strip()]

    # 若開啟自動發信且有設定收件人
    if auto_send and recipients:
        logger.info(f"🚀 開始自動寄送電子報: {subject}，目標收件人數: {len(recipients)}")
        sent_count = 0

        if send_mode == "bcc":
            # 模式 1: 單封信件透過 Bcc 群發
            ok = send_email_message(subject, html_body, to_email="me", bcc_emails=recipients, plain_body=plain_body)
            if ok:
                sent_count = len(recipients)
        else:
            # 模式 2: 逐封獨立寄送 (避免 Bcc 判定為垃圾信，每位讀者收到的 To 都是自己)
            for to in recipients:
                if send_email_message(subject, html_body, to_email=to, plain_body=plain_body):
                    sent_count += 1

        if sent_count > 0:
            logger.info(f"✅ 電子報自動發送成功！成功寄出: {sent_count}/{len(recipients)}")
            return {
                "mode": "sent",
                "success": True,
                "sent_count": sent_count,
                "total_recipients": len(recipients),
                "subject": subject
            }
        else:
            logger.warning("⚠️ 自動發信失敗，立即安全降級為建立 Gmail 草稿...")
            draft_ok = create_gmail_draft(subject, html_body, plain_body)
            return {
                "mode": "draft_fallback",
                "success": draft_ok,
                "sent_count": 0,
                "total_recipients": len(recipients),
                "subject": subject
            }

    # 未開啟自動發信或無收件人名單 -> 建立草稿 (既有安全模式)
    logger.info(f"📝 未開啟 EMAIL_AUTO_SEND 或無收件人名單，建立 Gmail 草稿: {subject}")
    draft_ok = create_gmail_draft(subject, html_body, plain_body)
    return {
        "mode": "draft",
        "success": draft_ok,
        "sent_count": 0,
        "total_recipients": len(recipients),
        "subject": subject
    }


def send_newsletter_as_draft(story_data: dict, news_data: dict, issue_number: int = None) -> bool:
    """向後相容輔助函式"""
    res = send_newsletter(story_data, news_data, issue_number)
    return res.get("success", False)
