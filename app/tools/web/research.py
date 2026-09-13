import os
from typing import Dict, Any
from app.tools.base import Tool, ToolResult
from app.security.permissions import PermissionLevel
from app.tools.web.search import get_search_provider
from app.tools.web.fetch import web_fetcher
from app.tools.web.safety import validate_search_query, validate_url_safety, SecurityError

class WebResearchTool(Tool):
    name = "web_research"
    description = "Conducts deep web research by performing a search and immediately fetching and extracting content from the top results. Returns a compiled research context with citations."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The research question or search query."}
        },
        "required": ["query"]
    }
    permission_level = PermissionLevel.LOW_RISK

    def _run(self, input_data: dict):
        try:
            query = validate_search_query(input_data["query"])
        except SecurityError as e:
            return str(e)
            
        max_sources = int(os.getenv("WEB_MAX_SOURCES_PER_RESEARCH", "3"))
        
        provider = get_search_provider()
        search_results = provider.search(query, max_sources)
        
        if not search_results or "error" in search_results[0]:
            err = search_results[0]['error'] if search_results else "No results."
            return f"Research failed during search phase: {err}"
            
        compiled_context = [f"Research Context for: '{query}'\n"]
        
        # Deduplicate URLs
        seen_urls = set()
        
        for i, res in enumerate(search_results):
            url = res.get("url")
            if not url or url in seen_urls:
                continue
                
            seen_urls.add(url)
            
            try:
                # Pre-validate before fetching
                validate_url_safety(url)
            except SecurityError:
                continue # Skip unsafe URLs
                
            fetch_res = web_fetcher.fetch(url)
            
            if "error" in fetch_res:
                content = f"(Failed to fetch: {fetch_res['error']})"
            else:
                content = fetch_res["text"]
                # Truncate content per source to avoid massive context
                # max_text_chars limits it globally, but for research we might want smaller
                if len(content) > 10000:
                    content = content[:10000] + "\n...[TRUNCATED]"
                    
            source_id = f"S{i+1}"
            compiled_context.append(f"[{source_id}] Title: {res.get('title')}")
            compiled_context.append(f"URL: {url}")
            compiled_context.append(f"Content:\n{content}\n")
            
        return "\n".join(compiled_context)
