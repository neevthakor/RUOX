import unittest
from app.security.redaction import redact_text, redact_dict

class TestRedaction(unittest.TestCase):
    def test_text_redaction(self):
        text = "Here is my key sk-1234567890abcdefghij123 and token ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        redacted = redact_text(text)
        self.assertNotIn("sk-", redacted)
        self.assertIn("<REDACTED_SECRET_KEY>", redacted)
        self.assertNotIn("ghp_", redacted)
        self.assertIn("<REDACTED_GITHUB_TOKEN>", redacted)

    def test_dict_redaction(self):
        data = {
            "api_key": "sk-1234567890abcdefghij123",
            "safe_value": "hello",
            "nested": {
                "password": "my_super_secret"
            }
        }
        redacted = redact_dict(data)
        self.assertEqual(redacted["api_key"], "<REDACTED>")
        self.assertEqual(redacted["safe_value"], "hello")
        self.assertEqual(redacted["nested"]["password"], "<REDACTED>")

if __name__ == '__main__':
    unittest.main()
