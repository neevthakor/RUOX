import abc
import os
import httpx
from typing import List, Dict, Any
from urllib.parse import quote_plus
from app.tools.web.parser import extract_text_from_html
from html.parser import HTMLParser

class WebSearchProvider(abc.ABC):
    @abc.abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        pass

class DuckDuckGoHtmlProvider(WebSearchProvider):
    """
    A lightweight, no-API-key fallback using DDG HTML search.
    This parses the HTML response of DuckDuckGo Lite.
    """
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        url = f"https://lite.duckduckgo.com/lite/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        data = {"q": query}
        
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, data=data)
                resp.raise_for_status()
                html = resp.text
                
                # Extremely primitive parsing for DDG Lite
                results = []
                import re
                
                # DDG Lite has a specific structure: 
                # <a class="result-url" href="URL">...</a>
                # <td class="result-snippet">SNIPPET</td>
                
                # We'll use regex to grab titles/urls and snippets roughly.
                # Since we don't want bs4 dependency, regex is ok for a fallback.
                
                blocks = re.split(r"<tr[^>]*>", html)
                current_result = {}
                
                for block in blocks:
                    # Look for URL and Title
                    url_match = re.search(r'<a class="result-url" href="([^"]+)">([^<]+)</a>', block)
                    if url_match:
                        if current_result and "url" in current_result:
                            results.append(current_result)
                            if len(results) >= num_results:
                                break
                        current_result = {
                            "url": url_match.group(1),
                            "title": extract_text_from_html(url_match.group(2)).strip()
                        }
                    
                    # Look for Snippet
                    snippet_match = re.search(r'<td class="result-snippet">(.+?)</td>', block, re.DOTALL)
                    if snippet_match and current_result:
                        current_result["snippet"] = extract_text_from_html(snippet_match.group(1)).strip()
                        
                if current_result and "url" in current_result and len(results) < num_results:
                    results.append(current_result)
                    
                return results
                
        except Exception as e:
            return [{"error": f"Search provider error: {str(e)}"}]

def get_search_provider() -> WebSearchProvider:
    # Later can check env var like SEARCH_PROVIDER=duckduckgo
    return DuckDuckGoHtmlProvider()
