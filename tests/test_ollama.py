import unittest
from unittest.mock import patch, MagicMock
from app.llm.ollama import OllamaProvider

class TestOllamaProvider(unittest.TestCase):
    def setUp(self):
        self.provider = OllamaProvider(base_url="http://fake", model="qwen2.5:7b")

    @patch("app.llm.ollama.httpx.Client")
    def test_generate_success(self, mock_client_class):
        mock_res = MagicMock()
        mock_res.json.return_value = {"message": {"content": "Hello"}}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_res
        mock_client_class.return_value = mock_client
        
        provider = OllamaProvider()
        res = provider.generate([{"role": "user", "content": "hi"}])
        self.assertEqual(res["message"]["content"], "Hello")

    @patch("app.llm.ollama.httpx.Client")
    def test_generate_error(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client_class.return_value = mock_client
        
        provider = OllamaProvider()
        res = provider.generate([{"role": "user", "content": "hi"}])
        self.assertIn("error", res)
        self.assertEqual(res["error"], "Network error")

if __name__ == "__main__":
    unittest.main()
