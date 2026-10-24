"""
【每日時務商報】郵件生成與發送邏輯單元與整合測試
===================================================
驗證項目：
1. 信件標題必須以【每日時務商報】為標準前綴。
2. build_email_html() 成功加載 templates/email_newsletter.html 模板並完成變數替換。
3. build_email_plaintext() 正確產出乾淨且無標籤的降級純文字。
4. send_newsletter() 在安全模式下 (EMAIL_AUTO_SEND=false) 會安全降級為建立草稿。
5. send_newsletter() 在無收件人或自動寄送時的容錯行為。
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from modules.gmail_sender import (
    build_email_html,
    build_email_plaintext,
    send_newsletter,
    SCOPES
)

class TestGmailNewsletter(unittest.TestCase):

    def setUp(self):
        self.sample_story_data = {
            "company_name": "台積電（2330）",
            "story": "台積電成立於1987年，是全球晶圓代工龍頭。\n**先進製程**引領全球半導體發展。\n*毛利率*維持高檔水準。\n#台積電 #半導體 #晶圓代工",
            "vocab": {
                "word": "paradigm",
                "pos": "n.",
                "pronunciation": "ˈpær.ə.daɪm",
                "definition": "範例、典範、樣式",
                "example": "TSMC represents a new paradigm in foundry model."
            },
            "proverb": {
                "text": "Innovation distinguishes between a leader and a follower.",
                "explanation": "創新是區分領導者與追隨者的關鍵。",
                "usage": "台積電持續在先進製程研發投入，展現龍頭格局。"
            },
            "german": {
                "word": "die Halbleiterindustrie",
                "pos": "f.",
                "pronunciation": "ˈhalpˌlaɪ̯tɐʔɪndʊsˌtʁiː",
                "definition": "半導體產業",
                "example": "Taiwan spielt eine zentrale Rolle in der globalen Halbleiterindustrie."
            }
        }

        self.sample_news_data = {
            "top_news": [
                {
                    "rank": 1,
                    "title": "輝達新一代 AI 晶片架構震撼發表",
                    "source_url": "https://example.com/nvidia-ai",
                    "impact_reason": "推升全球 AI 伺服器供應鏈強烈需求",
                    "summary": "輝達在發表會上公布最新 GPU 架構，算力相較前代提升超過三倍。",
                    "tags": [{"name": "人工智慧"}, {"name": "伺服器"}]
                },
                {
                    "rank": 2,
                    "title": "聯準會最新利率決策釋出偏鴿訊號",
                    "source_url": "https://example.com/fed-rate",
                    "impact_reason": "科技股估值壓力大幅減輕",
                    "summary": "聯準會宣布維持基準利率不變，市場預期下半年將啟動預防性降息。",
                    "tags": [{"name": "總體經濟"}, {"name": "降息"}]
                }
            ]
        }

    def test_scopes_include_send_and_compose(self):
        """驗證 SCOPES 同時包含寄信與草稿權限"""
        self.assertIn('https://www.googleapis.com/auth/gmail.send', SCOPES)
        self.assertIn('https://www.googleapis.com/auth/gmail.compose', SCOPES)

    def test_build_email_html_content_and_subject(self):
        """驗證 HTML 電子報生成與標題格式"""
        html = build_email_html(self.sample_story_data, self.sample_news_data, issue_number=19)
        self.assertIn("【每日時務商報】", html)
        self.assertIn("第 19 期", html)
        self.assertIn("台積電（2330）", html)
        self.assertIn("輝達新一代 AI 晶片架構震撼發表", html)
        self.assertIn("die Halbleiterindustrie", html)
        self.assertIn("paradigm", html)
        # 驗證標籤膠囊化
        self.assertIn('<span class="tag-pill">#人工智慧</span>', html)

    def test_build_email_plaintext(self):
        """驗證 Plain Text 降級內容"""
        text = build_email_plaintext(self.sample_story_data, self.sample_news_data, issue_number=19)
        self.assertIn("【每日時務商報#19】", text)
        self.assertIn("1. 輝達新一代 AI 晶片架構震撼發表", text)
        self.assertIn("【今日商務單字】", text)
        self.assertIn("die Halbleiterindustrie", text)

    @patch('modules.gmail_sender.create_gmail_draft')
    def test_send_newsletter_draft_mode(self, mock_create_draft):
        """驗證未啟用 EMAIL_AUTO_SEND 時，自動切換至建立草稿"""
        mock_create_draft.return_value = True
        with patch.dict(os.environ, {"EMAIL_AUTO_SEND": "false", "NEWSLETTER_RECIPIENTS": "test@example.com"}):
            res = send_newsletter(self.sample_story_data, self.sample_news_data)
            self.assertEqual(res["mode"], "draft")
            self.assertTrue(res["success"])
            self.assertTrue(res["subject"].startswith("【每日時務商報】"))
            mock_create_draft.assert_called_once()

    @patch('modules.gmail_sender.send_email_message')
    def test_send_newsletter_auto_send_individual(self, mock_send_email):
        """驗證啟用 EMAIL_AUTO_SEND 時，逐封發信至收件人清單"""
        mock_send_email.return_value = True
        recipients = "user1@example.com, user2@example.com"
        with patch.dict(os.environ, {
            "EMAIL_AUTO_SEND": "true",
            "NEWSLETTER_RECIPIENTS": recipients,
            "EMAIL_SEND_MODE": "individual"
        }):
            res = send_newsletter(self.sample_story_data, self.sample_news_data, issue_number=20)
            self.assertEqual(res["mode"], "sent")
            self.assertTrue(res["success"])
            self.assertEqual(res["sent_count"], 2)
            self.assertEqual(mock_send_email.call_count, 2)
            self.assertIn("【每日時務商報#20】", res["subject"])

    @patch('modules.gmail_sender.create_gmail_draft')
    @patch('modules.gmail_sender.send_email_message')
    def test_send_newsletter_failure_fallback_to_draft(self, mock_send_email, mock_create_draft):
        """驗證若自動發信失敗，應安全降級建立草稿"""
        mock_send_email.return_value = False
        mock_create_draft.return_value = True
        with patch.dict(os.environ, {
            "EMAIL_AUTO_SEND": "true",
            "NEWSLETTER_RECIPIENTS": "user@example.com",
            "EMAIL_SEND_MODE": "individual"
        }):
            res = send_newsletter(self.sample_story_data, self.sample_news_data)
            self.assertEqual(res["mode"], "draft_fallback")
            self.assertTrue(res["success"])
            mock_create_draft.assert_called_once()

if __name__ == "__main__":
    unittest.main()
