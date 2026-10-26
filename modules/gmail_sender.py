import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
import re
from logger import get_logger

logger = get_logger(__name__)

def get_taiwan_date_str(fmt: str = "%Y/%m/%d") -> str:
    """
    取得台灣時區 (Asia/Taipei, UTC+8) 的當前日期字串。
    確保在 GitHub Actions (預設 UTC) 或各類雲端環境中執行時，
    信件內文之日期均精確對標台灣在地日期。
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Taipei")).strftime(fmt)
    except Exception:
        # 備援：台灣無夏令時間，全年恆為 UTC+8
        tz_tw = timezone(timedelta(hours=8))
        return datetime.now(tz_tw).strftime(fmt)

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


def build_email_html(story_data: dict, news_data: dict, issue_number: int = None, story_number: int = None, subject: str = None) -> str:
    """
    組合【每日時務商報】極簡人文風 HTML 電子報內容 (無 Emoji、無 AI 產出感)。
    優先使用 templates/email_newsletter.html 模板。
    """
    today_str = get_taiwan_date_str("%Y/%m/%d")
    company_name = story_data.get("company_name", "")
    issue_num = issue_number or 47
    story_num = story_number or 63
    actual_subject = subject or f"【每日時務商報#{issue_num}】－每日快訊與成長"

    # --- 新聞區段 HTML ---
    news_items_html = ""
    for idx, item in enumerate(news_data.get("top_news", []), 1):
        rank = item.get("rank", idx)
        title = item.get("title", "")
        url = item.get("source_url", "#")
        impact = item.get("impact_reason", "")
        summary = item.get("summary", "")
        tags = item.get("tags", [])
        
        tags_str = "　".join([f"#{t.get('name', t)}" for t in tags])

        news_items_html += f"""
        <div class="news-item">
          <div class="news-title">
            {rank}. <a href="{url}" target="_blank">{title}</a>
          </div>
          <div class="news-detail-group">
            <div class="news-detail-row">
              <span class="impact-label">影響：</span><span class="impact-text">{impact}</span>
            </div>
            <div class="news-detail-row">
              <span class="summary-label">摘要：</span><span class="summary-text">{summary}</span>
            </div>
            <div class="news-tags">{tags_str}</div>
          </div>
        </div>
        """

    # --- 商業故事主文處理 ---
    story_raw = story_data.get("story", "")
    story_lines = story_raw.split("\n")
    story_html_lines = []
    
    first_non_empty = True
    for line in story_lines:
        stripped = line.strip()
        if not stripped:
            story_html_lines.append("<br>")
            continue

        # 若第一行已包含「商業故事」標題，略過以避免與模板重複
        if first_non_empty and ("商業故事" in stripped):
            first_non_empty = False
            continue
        first_non_empty = False

        is_hashtag = stripped.startswith("#")
        # 處理粗體與斜體 (復刻經典排版：重點藍色斜體)
        stripped = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', stripped)
        stripped = re.sub(r'\*(.*?)\*', r'<span style="color:rgb(37, 110, 225)"><i>\1</i></span>', stripped)
        stripped = re.sub(r'\b_(.*?)_\b', r'<span style="color:rgb(37, 110, 225)"><i>\1</i></span>', stripped)

        if is_hashtag:
            story_html_lines.append(
                f'<div style="text-align:center;margin-top:14px;"><b><font color="#93c47d">{stripped}</font></b></div>'
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
                "{{ issue_number }}": str(issue_num),
                "{{ story_number }}": str(story_num),
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

    # 內建備用版面 (無 Emoji、極簡排版)
    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px;line-height:1.7;color:#333;">
      <div style="text-align:center;border-bottom:2px solid #222;padding-bottom:12px;margin-bottom:20px;">
        <h1 style="font-size:22px;color:#222;margin:0;">【每日時務商報】</h1>
        <div style="font-size:12px;color:#666;">第 {issue_num} 期 · {today_str} · 每日快訊與成長</div>
      </div>
      <h2 style="color:#a36200;font-size:18px;">每日重大新聞快訊 Top 3</h2>
      {news_items_html}
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <div style="text-align:center;margin-bottom:16px;">
        <span style="font-size:17px;font-weight:bold;color:#ff9900;">商業故事#{story_num}：{company_name}</span>
      </div>
      {story_html}
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <div style="text-align:center;">
        <div style="font-weight:bold;color:#ff9900;margin-bottom:8px;">【今日商務單字】</div>
        <p><b><i>{vocab_word}</i></b> ({vocab_pos}) // {vocab_pron} //</p>
        <p style="color:rgb(37,110,225);">{vocab_def}</p>
        <p><b>【例句】</b><br><i>{vocab_ex}</i></p>
      </div>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <div style="text-align:center;">
        <div style="font-weight:bold;margin-bottom:8px;">【今日商業／處世諺語】</div>
        <p><b><i>{proverb_text}</i></b></p>
        <p><span style="color:rgb(37,110,225);font-weight:bold;">解析：</span>{proverb_exp}</p>
        <p><span style="color:rgb(37,110,225);font-weight:bold;">應用：</span>{proverb_usage}</p>
      </div>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <div style="text-align:center;">
        <div style="font-weight:bold;margin-bottom:8px;">【德語小教室】</div>
        <p><b><i>{german_word}</i></b> ({german_pos}) / {german_pron} /</p>
        <p style="color:rgb(37,110,225);">{german_def}</p>
        <p><b>【例句】</b><br><i>{german_ex}</i></p>
      </div>
      <div style="text-align:center;color:#999;font-size:12px;margin-top:28px;">
        每日時務商報 · 第 {issue_num} 期 · {today_str}
      </div>
    </div>
    """


def build_email_plaintext(story_data: dict, news_data: dict, issue_number: int = None, story_number: int = None, subject: str = None) -> str:
    """產生標準純文字版本 (Plain Text Fallback，簡約、無 Emoji)"""
    today_str = get_taiwan_date_str("%Y/%m/%d")
    company_name = story_data.get("company_name", "")
    issue_num = issue_number or 47
    story_num = story_number or 63
    actual_subject = subject or f"【每日時務商報#{issue_num}】－每日快訊與成長"

    lines = [
        f"========================================",
        f" {actual_subject}",
        f" 第 {issue_num} 期 · 日期：{today_str}",
        f"========================================\n",
        f"每日重大新聞快訊 Top 3\n"
    ]

    for idx, item in enumerate(news_data.get("top_news", []), 1):
        lines.append(f"{idx}. {item.get('title', '')}")
        lines.append(f"   連結: {item.get('source_url', '')}")
        lines.append(f"   影響: {item.get('impact_reason', '')}")
        lines.append(f"   摘要: {item.get('summary', '')}\n")

    lines.append(f"\n商業故事#{story_num}：{company_name}\n")
    lines.append(story_data.get("story", "").strip())

    vocab = story_data.get("vocab", {})
    lines.append(f"\n\n【今日商務單字】")
    lines.append(f"{vocab.get('word', '')} ({vocab.get('pos', '')}) /{vocab.get('pronunciation', '')}/")
    lines.append(f"釋義：{vocab.get('definition', '')}")
    lines.append(f"例句：{vocab.get('example', '')}")

    proverb = story_data.get("proverb", {})
    lines.append(f"\n【今日商業／處世諺語】")
    lines.append(f"{proverb.get('text', '')}")
    lines.append(f"解析：{proverb.get('explanation', '')}")
    lines.append(f"應用：{proverb.get('usage', '')}")

    german = story_data.get("german", {})
    lines.append(f"\n【德語小教室】")
    lines.append(f"{german.get('word', '')} ({german.get('pos', '')}) /{german.get('pronunciation', '')}/")
    lines.append(f"釋義：{german.get('definition', '')}")
    lines.append(f"例句：{german.get('example', '')}")

    lines.append(f"\n----------------------------------------")
    lines.append(f"每日時務商報 · 第 {issue_num} 期 · {today_str}")

    return "\n".join(lines)


_cached_sender_email = None

def _get_sender_email(service) -> str:
    """取得當前已授權使用者的 Gmail 地址，供 From 標頭使用以防被郵件伺服器誤判為垃圾信"""
    global _cached_sender_email
    if _cached_sender_email:
        return _cached_sender_email
    try:
        profile = service.users().getProfile(userId='me').execute()
        _cached_sender_email = profile.get('emailAddress', 'me')
        return _cached_sender_email
    except Exception:
        return 'me'


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

        # 使用標準 RFC 5322 格式寄件者標頭 (符合 SPF/DKIM/DMARC 規範，大幅降低被分類為垃圾信之機率)
        sender_email = _get_sender_email(service)
        if sender_email and sender_email != 'me':
            msg['From'] = f"每日時務商報 <{sender_email}>"
        else:
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


def send_newsletter(story_data: dict, news_data: dict, issue_number: int = None, story_number: int = None) -> dict:
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
    # 若外部未傳入期數或故事篇數，自動透過 StateManager 取得下一期
    if issue_number is None or story_number is None:
        try:
            from modules.state_manager import StateManager
            sm = StateManager()
            next_nl, next_st = sm.get_next_counters()
            issue_number = issue_number or next_nl
            story_number = story_number or next_st
        except Exception:
            issue_number = issue_number or 47
            story_number = story_number or 63

    subject = f"【每日時務商報#{issue_number}】－每日快訊與成長"

    html_body = build_email_html(story_data, news_data, issue_number, story_number, subject)
    plain_body = build_email_plaintext(story_data, news_data, issue_number, story_number, subject)

    auto_send = os.getenv("EMAIL_AUTO_SEND", "false").strip().strip("'\"").lower() in ("true", "1", "yes")
    recipients_str = os.getenv("NEWSLETTER_RECIPIENTS", "").strip().strip("'\"")
    send_mode = os.getenv("EMAIL_SEND_MODE", "individual").strip().strip("'\"").lower()  # "individual" 或 "bcc"

    # 支援半形逗號 (,)、中文全形逗號 (，)、分號 (;) 或換行，防止輸入格式問題，並去除引號與前後空白
    recipients = [r.strip().strip("'\"") for r in re.split(r'[,，;\n\r]+', recipients_str) if r.strip().strip("'\"")]

    logger.info(f"[Newsletter Sender] auto_send={auto_send}, recipients_count={len(recipients)}, send_mode={send_mode}")
    if recipients:
        masked_recipients = [r[:3] + "***" + r[r.find("@"):] if "@" in r else r for r in recipients]
        logger.info(f"[Newsletter Sender] 目標名單: {', '.join(masked_recipients)}")

    # 若開啟自動發信且有設定收件人
    if auto_send and recipients:
        logger.info(f"開始自動寄送電子報: {subject}，目標收件人數: {len(recipients)}")
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
            logger.info(f"電子報自動發送成功！成功寄出: {sent_count}/{len(recipients)}")
            return {
                "mode": "sent",
                "success": True,
                "sent_count": sent_count,
                "total_recipients": len(recipients),
                "subject": subject
            }
        else:
            logger.warning("自動發信失敗，立即安全降級為建立 Gmail 草稿...")
            draft_ok = create_gmail_draft(subject, html_body, plain_body)
            return {
                "mode": "draft_fallback",
                "success": draft_ok,
                "sent_count": 0,
                "total_recipients": len(recipients),
                "subject": subject
            }

    # 未開啟自動發信或無收件人名單 -> 建立草稿 (既有安全模式)
    logger.info(f"未開啟 EMAIL_AUTO_SEND 或無收件人名單，建立 Gmail 草稿: {subject}")
    draft_ok = create_gmail_draft(subject, html_body, plain_body)
    return {
        "mode": "draft",
        "success": draft_ok,
        "sent_count": 0,
        "total_recipients": len(recipients),
        "subject": subject
    }


def send_newsletter_as_draft(story_data: dict, news_data: dict, issue_number: int = None, story_number: int = None) -> bool:
    """向後相容輔助函式"""
    res = send_newsletter(story_data, news_data, issue_number, story_number)
    return res.get("success", False)
