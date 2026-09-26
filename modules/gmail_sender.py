import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from logger import get_logger

logger = get_logger(__name__)

# OAuth2 scopes needed for Gmail draft creation
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

# Paths for OAuth credential files (must be placed in project root)
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'token.json')


def _get_gmail_service():
    """
    取得已授權的 Gmail API 服務物件。
    第一次執行時會開啟瀏覽器要求授權；之後會自動使用快取的 token.json。
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
                logger.warning(f"Token 刷新失敗，將重新授權: {e}")
                creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                logger.error(f"找不到 credentials.json，請從 Google Cloud Console 下載並放置於: {CREDENTIALS_FILE}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("Gmail OAuth 授權成功")

        # 儲存 token 供下次使用
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service


def build_email_html(story_data: dict, news_data: dict) -> str:
    """
    根據「每日時務商報」範本，組合商業故事 + 新聞快訊的完整 HTML 信件內容。

    story_data keys:
        story (str): 商業故事主文（含標題、條列等）
        vocab (dict): word, pos, pronunciation, definition, example
        proverb (dict): text, explanation, usage
        german (dict): word, pos, pronunciation, definition, example
        company_name (str)

    news_data keys:
        top_news (list of dict): rank, title, source_url, impact_reason, summary, tags
    """
    today = datetime.now().strftime("%Y/%m/%d")
    company_name = story_data.get("company_name", "")

    # --- 新聞區段 HTML ---
    news_items_html = ""
    for item in news_data.get("top_news", []):
        rank = item.get("rank", "")
        title = item.get("title", "")
        url = item.get("source_url", "#")
        impact = item.get("impact_reason", "")
        summary = item.get("summary", "")
        tags = item.get("tags", [])
        tags_str = "　".join([f"#{t['name']}" for t in tags])

        news_items_html += f"""
<li style="margin:12px 0px 0px 32px">
  <p style="line-height:1.6em;margin:0px;box-sizing:border-box;padding-left:4px">
    <span style="background-color:transparent">
      <b><a href="{url}" target="_blank" style="color:#ff9900;text-decoration:none">{title}</a></b>
    </span>
  </p>
  <ul style="color:rgb(54,55,55);margin-top:0px;padding:0px">
    <li style="margin:6px 0px 0px 32px">
      <p style="line-height:1.6em;margin:0px;box-sizing:border-box;padding-left:4px">
        <em><strong>影響：</strong></em>
      </p>
      <p style="line-height:1.6em;margin:0px;box-sizing:border-box;padding-left:4px">
        <span style="color:rgb(37,110,225)"><i>{impact}</i></span>
      </p>
    </li>
    <li style="margin:6px 0px 0px 32px">
      <p style="line-height:1.6em;margin:0px;box-sizing:border-box;padding-left:4px">
        <em><strong>摘要：</strong></em>
      </p>
      <p style="line-height:1.6em;margin:0px;box-sizing:border-box;padding-left:4px">
        <i>{summary}</i>
      </p>
    </li>
    <li style="margin:4px 0px 0px 32px;color:#888888">
      <p style="line-height:1.6em;margin:0px;box-sizing:border-box;padding-left:4px;font-size:0.9em">
        {tags_str}
      </p>
    </li>
  </ul>
</li>
"""

    # --- 商業故事主文處理（換行轉 HTML）---
    story_raw = story_data.get("story", "")
    story_lines = story_raw.split("\n")
    story_html_lines = []
    for line in story_lines:
        stripped = line.strip()
        if not stripped:
            story_html_lines.append("<br>")
        elif stripped.startswith("#"):
            # hashtag 行
            story_html_lines.append(
                f'<div style="text-align:center"><b><font color="#93c47d">{stripped}</font></b></div>'
            )
        else:
            story_html_lines.append(
                f'<div style="text-align:center">{stripped}</div>'
            )
    story_html = "\n".join(story_html_lines)

    # --- 單字、德語、諺語區段 ---
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
    proverb_exp = proverb.get("explanation", "")
    proverb_usage = proverb.get("usage", "")

    html = f"""<div dir="ltr">

<!-- ===== 每日重大新聞快訊 Top 3 ===== -->
<h2 style="color:rgb(54,55,55);font-family:'SF Pro Display',-apple-system,system-ui,sans-serif;word-break:keep-all;margin:0px auto 0.625em;line-height:1.16em;font-size:28px;max-width:600px">
  <span style="color:rgb(163,98,0)">每日重大新聞快訊</span>
  <span style="color:rgb(163,98,0)">Top 3</span>
</h2>

<div>
  <ol style="margin-top:0px;padding:0px;max-width:600px;margin-left:auto;margin-right:auto;font-family:-apple-system-ui-serif,ui-serif,Georgia,serif">
    {news_items_html}
  </ol>
</div>

<hr style="border:none;border-top:2px solid #f0c060;margin:28px auto;max-width:600px">

<!-- ===== 商業故事 ===== -->
<div style="text-align:center;max-width:600px;margin:0 auto">
  <div>
    <b><font color="#ff9900" style="font-size:large">商業故事：{company_name}</font></b>
  </div>
  <div><br></div>

  {story_html}

  <div><br></div>
</div>

<hr style="border:none;border-top:1px solid #eeeeee;margin:24px auto;max-width:600px">

<!-- ===== 今日商務單字 ===== -->
<div style="text-align:center;max-width:600px;margin:0 auto">
  <div>
    <b><font size="4" color="#ff9900">【今日商務單字】</font></b>
  </div>
  <div><br></div>
  <div>
    <b><i>{vocab_word} </i>({vocab_pos}) // {vocab_pron} //</b>
  </div>
  <div><br></div>
  <div><font color="#6fa8dc">{vocab_def}</font></div>
  <div><br></div>
  <div><b>【例句】</b></div>
  <div><br></div>
  <div><b><i>{vocab_ex}</i></b></div>
  <div><br></div>
</div>

<hr style="border:none;border-top:1px solid #eeeeee;margin:24px auto;max-width:600px">

<!-- ===== 今日商業諺語 ===== -->
<div style="text-align:center;max-width:600px;margin:0 auto">
  <div>
    <b><font size="4">【今日商業/處世諺語】</font></b>
  </div>
  <div><br></div>
  <div><b><i>{proverb_text}</i></b></div>
  <div><br></div>
  <div>
    <ul style="text-align:left;display:inline-block;margin:0 auto">
      <li><b><i><font color="#6fa8dc">解析：</font></i></b></li>
    </ul>
  </div>
  <div style="max-width:500px;margin:0 auto;text-align:center">{proverb_exp}</div>
  <div><br></div>
  <div>
    <ul style="text-align:left;display:inline-block;margin:0 auto">
      <li><b><i><font color="#6fa8dc">應用：</font></i></b></li>
    </ul>
  </div>
  <div style="max-width:500px;margin:0 auto;text-align:center">{proverb_usage}</div>
  <div><br></div>
</div>

<hr style="border:none;border-top:1px solid #eeeeee;margin:24px auto;max-width:600px">

<!-- ===== 德語小教室 ===== -->
<div style="text-align:center;max-width:600px;margin:0 auto">
  <div>
    <b><font size="4">【德語小教室】</font></b>
  </div>
  <div><br></div>
  <div>
    <b><i>{german_word} </i>({german_pos}) / {german_pron} /</b>
  </div>
  <div><br></div>
  <div><font color="#6fa8dc">{german_def}</font></div>
  <div><br></div>
  <div><b>【例句】</b></div>
  <div><br></div>
  <div><b><i>{german_ex}</i></b></div>
  <div><br></div>
</div>

<div style="text-align:center;color:#aaaaaa;font-size:12px;margin-top:32px;max-width:600px;margin-left:auto;margin-right:auto">
  每日時務商報 · 自動產出 · {today}
</div>

</div>"""

    return html


def create_gmail_draft(subject: str, html_body: str) -> bool:
    """
    在 Gmail 中建立一封 HTML 格式的草稿。

    Args:
        subject: 信件主旨
        html_body: 信件 HTML 內容

    Returns:
        True 表示成功，False 表示失敗
    """
    service = _get_gmail_service()
    if not service:
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = 'me'
        # 收件人由使用者在草稿中自行填寫，此處不設定 To

        # 加入 HTML 內容
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        draft_body = {'message': {'raw': raw}}

        draft = service.users().drafts().create(userId='me', body=draft_body).execute()
        draft_id = draft.get('id', 'unknown')
        logger.info(f"Gmail 草稿建立成功！草稿 ID: {draft_id}")
        return True

    except Exception as e:
        logger.error(f"建立 Gmail 草稿失敗: {e}")
        return False


def send_newsletter_as_draft(story_data: dict, news_data: dict, issue_number: int = None) -> bool:
    """
    將商業故事與新聞快訊組合成「每日時務商報」格式並建立 Gmail 草稿。

    Args:
        story_data: 商業故事相關資料 (參考 build_email_html)
        news_data: 新聞資料 (參考 build_email_html)
        issue_number: 期號 (選填，若不提供則自動使用日期)

    Returns:
        True 表示成功，False 表示失敗
    """
    today_str = datetime.now().strftime("%Y/%m/%d")

    if issue_number:
        subject = f"每日時務商報 #{issue_number}｜{today_str}"
    else:
        subject = f"每日時務商報｜{today_str}"

    logger.info(f"正在組合 Gmail 草稿: {subject}")
    html_body = build_email_html(story_data, news_data)
    return create_gmail_draft(subject, html_body)
