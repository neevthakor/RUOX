import unittest
import os
from unittest.mock import patch, MagicMock
from app.tools.web.safety import validate_url_safety, validate_search_query, SecurityError
from app.tools.web.parser import extract_text_from_html, format_untrusted_content
from app.tools.web.fetch import WebFetcher
from app.tools.web.search import get_search_provider
from app.tools.web import WebSearchTool, WebFetchTool, WebResearchTool

class TestWebSafety(unittest.TestCase):
    @patch.dict(os.environ, {"LOCAL_ONLY": "true"})
    def test_local_only_blocks(self):
        with self.assertRaisesRegex(SecurityError, "disabled because LOCAL_ONLY"):
            validate_url_safety("http://example.com")
        with self.assertRaisesRegex(SecurityError, "disabled because LOCAL_ONLY"):
            validate_search_query("test query")

    @patch.dict(os.environ, {"LOCAL_ONLY": "false"})
    def test_ssrf_protection_localhost(self):
        with self.assertRaisesRegex(SecurityError, "SSRF"):
            validate_url_safety("http://127.0.0.1")
        with self.assertRaisesRegex(SecurityError, "SSRF"):
            validate_url_safety("http://localhost")
            
    @patch.dict(os.environ, {"LOCAL_ONLY": "false"})
    def test_ssrf_protection_private_ip(self):
        with self.assertRaisesRegex(SecurityError, "SSRF"):
            validate_url_safety("http://192.168.1.5")
            
    @patch.dict(os.environ, {"LOCAL_ONLY": "false"})
    def test_ssrf_protection_metadata(self):
        with self.assertRaisesRegex(SecurityError, "SSRF"):
            validate_url_safety("http://169.254.169.254")

    @patch.dict(os.environ, {"LOCAL_ONLY": "false"})
    def test_protocol_restriction(self):
        with self.assertRaisesRegex(SecurityError, "Protocol 'file' not allowed"):
            validate_url_safety("file:///etc/passwd")

    @patch.dict(os.environ, {"LOCAL_ONLY": "false"})
    def test_secret_redaction(self):
        with self.assertRaisesRegex(SecurityError, "contains sensitive information"):
            validate_search_query("search for my OPENAI_API_KEY=sk-1234567890abcdef")

class TestWebParser(unittest.TestCase):
    def test_extract_text(self):
        html = "<html><head><script>alert('x')</script></head><body><h1>Title</h1><p>Content text.</p></body></html>"
        text = extract_text_from_html(html)
        self.assertNotIn("alert", text)
        self.assertIn("Title Content text.", text)
        
    def test_format_untrusted(self):
        content = "Some text"
        formatted = format_untrusted_content(content)
        self.assertTrue(formatted.startswith("\n--- UNTRUSTED WEB CONTENT ---"))
        self.assertTrue(formatted.endswith("--- END UNTRUSTED WEB CONTENT ---\n"))

class TestWebTools(unittest.TestCase):
    @patch.dict(os.environ, {"LOCAL_ONLY": "false"})
    @patch("app.tools.web.search.DuckDuckGoHtmlProvider.search")
    def test_web_search_tool(self, mock_search):
        mock_search.return_value = [{"title": "Test", "url": "https://test.com", "snippet": "A test snippet"}]
        tool = WebSearchTool()
        res = tool._run({"query": "test query"})
        self.assertIn("Test", res)
        self.assertIn("https://test.com", res)

    @patch.dict(os.environ, {"LOCAL_ONLY": "false"})
    @patch("app.tools.web.fetch.WebFetcher.fetch")
    def test_web_fetch_tool(self, mock_fetch):
        mock_fetch.return_value = {"success": True, "url": "https://example.com", "text": "--- UNTRUSTED WEB CONTENT ---\nMock text"}
        tool = WebFetchTool()
        res = tool._run({"url": "https://example.com"})
        self.assertIn("Mock text", res)

    @patch.dict(os.environ, {"LOCAL_ONLY": "false"})
    @patch("app.tools.web.search.DuckDuckGoHtmlProvider.search")
    @patch("app.tools.web.fetch.WebFetcher.fetch")
    def test_web_research_tool(self, mock_fetch, mock_search):
        mock_search.return_value = [{"title": "Source 1", "url": "https://source1.com"}]
        mock_fetch.return_value = {"success": True, "url": "https://source1.com", "text": "Fetched content"}
        
        tool = WebResearchTool()
        res = tool._run({"query": "research topic"})
        self.assertIn("[S1] Title: Source 1", res)
        self.assertIn("URL: https://source1.com", res)
        self.assertIn("Fetched content", res)

if __name__ == "__main__":
    unittest.main()
