from app.tools.base import Tool, ToolResult
from app.security.permissions import PermissionLevel
from app.tools.web.safety import validate_search_query, validate_url_safety, SecurityError
from app.tools.web.search import get_search_provider
from app.tools.web.fetch import web_fetcher
from app.tools.web.research import WebResearchTool
import json

class WebSearchTool(Tool):
    name = "web_search"
    description = "Searches the internet for information. Returns titles, URLs, and snippets."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "num_results": {"type": "integer", "description": "Number of results to return (max 8).", "default": 5}
        },
        "required": ["query"]
    }
    permission_level = PermissionLevel.LOW_RISK

    def _run(self, input_data: dict):
        try:
            query = validate_search_query(input_data["query"])
        except SecurityError as e:
            return str(e)
            
        num_results = min(int(input_data.get("num_results", 5)), 8)
        
        provider = get_search_provider()
        results = provider.search(query, num_results)
        
        if not results:
            return "No results found."
            
        if "error" in results[0]:
            return results[0]["error"]
            
        output = [f"Search Results for '{query}':\n"]
        for i, res in enumerate(results):
            output.append(f"[S{i+1}] {res.get('title', 'Unknown Title')}")
            output.append(f"URL: {res.get('url', 'Unknown URL')}")
            output.append(f"Snippet: {res.get('snippet', '')}\n")
            
        return "\n".join(output)

class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetches the text content of a specific URL."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to fetch."}
        },
        "required": ["url"]
    }
    permission_level = PermissionLevel.LOW_RISK

    def _run(self, input_data: dict):
        try:
            # First pass validation
            url = validate_url_safety(input_data["url"])
        except SecurityError as e:
            return str(e)
            
        result = web_fetcher.fetch(url)
        if "error" in result:
            return f"Failed to fetch URL: {result['error']}"
            
        return result["text"]
