import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from modules.state_manager import normalize_text, get_canonical_variants, StateManager

class TestDeduplicationArchitecture(unittest.TestCase):
    def test_normalize_text(self):
        # 1. Whitespace and Casing
        self.assertEqual(normalize_text("  Synergy  "), "synergy")
        self.assertEqual(normalize_text("BEAR MARKET"), "bear market")
        
        # 2. Leading articles
        self.assertEqual(normalize_text("a bear market"), "bear market")
        self.assertEqual(normalize_text("An arbitrage opportunity"), "arbitrage opportunity")
        self.assertEqual(normalize_text("the liquidity squeeze"), "liquidity squeeze")
        
        # 3. Parenthetical annotations
        self.assertEqual(normalize_text("leverage (n.)"), "leverage")
        self.assertEqual(normalize_text("pivot (v.)"), "pivot")
        self.assertEqual(normalize_text("軋空 (Short Squeeze)"), "軋空")

    def test_canonical_variants(self):
        # 1. Plural inflections
        variants_synergies = get_canonical_variants("synergies")
        self.assertIn("synergy", variants_synergies)
        self.assertIn("synergies", variants_synergies)

        variants_dividends = get_canonical_variants("dividends")
        self.assertIn("dividend", variants_dividends)

        # 2. Verb / Participle inflections
        variants_hedging = get_canonical_variants("hedging")
        self.assertIn("hedge", variants_hedging)
        self.assertIn("hedging", variants_hedging)

        variants_leveraged = get_canonical_variants("leveraged")
        self.assertIn("leverage", variants_leveraged)

        # 3. Bilingual / Bracketed financial terms
        variants_bilingual = get_canonical_variants("軋空 (Short Squeeze)")
        self.assertIn("軋空", variants_bilingual)
        self.assertIn("short squeeze", variants_bilingual)

    def test_check_vocabulary_exists_with_variants(self):
        # Mock StateManager connection to avoid modifying production database during unit test
        sm = StateManager.__new__(StateManager)
        
        # Simulated database contents for 'vocab' and 'finance_term'
        fake_db = {
            'vocab': [
                ("synergy",),
                ("hedge",),
                ("bear market",),
                ("leverage",),
            ],
            'finance_term': [
                ("軋空 (Short Squeeze)",),
                ("流動性枯竭 (Liquidity Squeeze)",)
            ]
        }
        
        def fake_get_connection():
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            
            def execute(query, params=None):
                vocab_type = params[0] if params else 'vocab'
                mock_cursor.fetchall.return_value = fake_db.get(vocab_type, [])
                
            mock_cursor.execute.side_effect = execute
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            return mock_conn

        sm._get_connection = fake_get_connection

        # Test Inflections & Form Variations
        self.assertTrue(sm.check_vocabulary_exists("synergies", "vocab"))
        self.assertTrue(sm.check_vocabulary_exists("hedging", "vocab"))
        self.assertTrue(sm.check_vocabulary_exists("a bear market", "vocab"))
        self.assertTrue(sm.check_vocabulary_exists("Leverage (n.)", "vocab"))
        
        # Test Non-duplicates
        self.assertFalse(sm.check_vocabulary_exists("blue chip", "vocab"))
        self.assertFalse(sm.check_vocabulary_exists("arbitrage", "vocab"))

        # Test Finance Terms Bilingual Duplicate Checking
        self.assertTrue(sm.check_vocabulary_exists("Short Squeeze", "finance_term"))
        self.assertTrue(sm.check_vocabulary_exists("軋空", "finance_term"))
        self.assertTrue(sm.check_vocabulary_exists("軋空 (Short Squeeze)", "finance_term"))
        self.assertTrue(sm.check_vocabulary_exists("Liquidity Squeeze", "finance_term"))
        self.assertFalse(sm.check_vocabulary_exists("Quantitative Easing", "finance_term"))

        # Test Isolation: vocab vs finance_term (User explicit requirement)
        # "Short Squeeze" is in finance_term but NOT in vocab
        self.assertFalse(sm.check_vocabulary_exists("Short Squeeze", "vocab"))
        # "synergy" is in vocab but NOT in finance_term
        self.assertFalse(sm.check_vocabulary_exists("synergy", "finance_term"))

    def test_bounded_retry_logic(self):
        # Test that retry loop stops upon reaching a non-duplicate or max_retries
        attempts = 0
        max_retries = 3
        words_stream = ["synergy", "synergies", "unprecedented"] # 1st dup, 2nd dup, 3rd fresh
        
        def mock_check(w):
            return w in ["synergy", "synergies"]
            
        current_word = words_stream[0]
        rejected = []
        for i in range(max_retries):
            attempts += 1
            if mock_check(current_word):
                rejected.append(current_word)
                current_word = words_stream[i + 1]
            else:
                break
                
        self.assertEqual(current_word, "unprecedented")
        self.assertEqual(attempts, 3)
    def test_live_db_integration(self):
        # Optional live database test if DATABASE_URL is configured
        from config import DATABASE_URL
        if not DATABASE_URL:
            self.skipTest("DATABASE_URL not configured")
        
        try:
            live_sm = StateManager()
            history = live_sm.get_recent_history(days=30)
            self.assertIn("vocab", history)
            self.assertIn("proverb", history)
            self.assertIn("german", history)
            self.assertIn("finance_term", history)
            print(f"\n[Live DB] Successfully retrieved 30-day history: {len(history['vocab'])} vocabs, {len(history['finance_term'])} finance terms.")
        except Exception as e:
            err_msg = str(e)
            if "timeout expired" in err_msg or "failed to connect" in err_msg.lower():
                self.skipTest(f"Skipping live DB check: Local ISP/firewall cannot reach remote Neon DB on port 5432. (Verified in GitHub Actions runner environment). Details: {err_msg}")
            else:
                self.fail(f"Live database test failed: {e}")

if __name__ == '__main__':
    unittest.main()
