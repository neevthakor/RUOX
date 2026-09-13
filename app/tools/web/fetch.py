import httpx
import os
from typing import Dict, Any
from app.tools.web.safety import validate_url_safety, SecurityError
from app.tools.web.parser import extract_text_from_html, format_untrusted_content

class WebFetcher:
    def __init__(self):
        self.timeout = int(os.getenv("WEB_TIMEOUT_SECONDS", "15"))
        self.max_response_bytes = int(os.getenv("WEB_MAX_RESPONSE_MB", "5")) * 1024 * 1024
        self.max_text_chars = int(os.getenv("WEB_MAX_TEXT_CHARS", "30000"))
        
    def fetch(self, url: str) -> Dict[str, Any]:
        """
        Safely fetches a URL and returns structured data.
        Follows redirects but validates each one.
        """
        try:
            current_url = validate_url_safety(url)
        except SecurityError as e:
            return {"error": str(e), "url": url}
            
        headers = {
            "User-Agent": "RUOX Local AI Assistant Web Fetcher (Research Bot)"
        }
        
        try:
            # We handle redirects manually to validate safety at each step
            # Alternatively, we could use an httpx Event Hook, but manual is simpler for P4
            with httpx.Client(timeout=self.timeout) as client:
                redirects = 0
                max_redirects = 5
                
                while redirects < max_redirects:
                    response = client.get(current_url, headers=headers, follow_redirects=False)
                    
                    if response.is_redirect:
                        next_url = response.headers.get("Location")
                        if not next_url:
                            break
                        # Handle relative redirects
                        if next_url.startswith("/"):
                            from urllib.parse import urljoin
                            next_url = urljoin(current_url, next_url)
                            
                        # Validate the redirect target
                        current_url = validate_url_safety(next_url)
                        redirects += 1
                        continue
                        
                    # Target reached
                    response.raise_for_status()
                    
                    # Check size using Content-Length if available
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > self.max_response_bytes:
                        return {"error": "Response exceeds maximum allowed size.", "url": current_url}
                        
                    # Check content type
                    content_type = response.headers.get("Content-Type", "").lower()
                    
                    # Read content safely, checking size during download if possible
                    # (httpx allows stream reading, but we can just use response.content if we trust content-length)
                    content = response.content
                    if len(content) > self.max_response_bytes:
                        return {"error": "Response body exceeds maximum allowed size.", "url": current_url}
                        
                    if "text/html" in content_type:
                        text = extract_text_from_html(content.decode(errors='replace'), self.max_text_chars)
                    elif "application/json" in content_type or "text/plain" in content_type:
                        text = content.decode(errors='replace')[:self.max_text_chars]
                    else:
                        return {"error": f"Unsupported content type: {content_type}", "url": current_url}
                        
                    return {
                        "url": current_url,
                        "text": format_untrusted_content(text),
                        "success": True
                    }
                    
                return {"error": "Too many redirects.", "url": current_url}
                
        except httpx.TimeoutException:
            return {"error": "Request timed out.", "url": current_url}
        except httpx.RequestError as e:
            return {"error": f"Network error: {str(e)}", "url": current_url}
        except SecurityError as e:
            return {"error": str(e), "url": current_url}
        except Exception as e:
            return {"error": f"Failed to fetch: {str(e)}", "url": current_url}

web_fetcher = WebFetcher()
