import unittest
from unittest.mock import patch, MagicMock
from app.llm.ollama import OllamaProvider

class TestOllamaProvider(unittest.TestCase):
    def setUp(self):
        self.provider = OllamaProvider(base_url="http://fake", model="qwen2.5:7b")

    @patch("app.llm.ollama.requests.post")
    def test_generate_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "Hello"}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        res = self.provider.generate([{"role": "user", "content": "Hi"}])
        self.assertIn("message", res)
        self.assertEqual(res["message"]["content"], "Hello")

    @patch("app.llm.ollama.requests.post")
    def test_generate_error(self, mock_post):
        mock_post.side_effect = Exception("Connection error")
        res = self.provider.generate([{"role": "user", "content": "Hi"}])
        self.assertIn("error", res)
        self.assertEqual(res["error"], "Connection error")

if __name__ == "__main__":
    unittest.main()
