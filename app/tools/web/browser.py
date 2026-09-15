import json
from app.tools.base import Tool, ToolResult
from app.browser.agent import browser_agent
from pydantic import Field
from typing import Dict, Any

class BrowserOpenTool(Tool):
    name = "browser_open"
    description = "Opens the browser and navigates to a URL."
    requires_confirmation = False

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        url = kwargs.get("url")
        if not url:
            return ToolResult(success=False, error="URL required")
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
            
        success = browser_agent.navigate(url)
        if success:
            obs = browser_agent.get_observation()
            return ToolResult(success=True, output=f"Navigated to {url}. Title: {obs.get('title')}")
        return ToolResult(success=False, error=f"Failed to navigate to {url}")

class BrowserObserveTool(Tool):
    name = "browser_observe"
    description = "Observes the current page title, URL, and text content."
    requires_confirmation = False

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        obs = browser_agent.get_observation()
        if "error" in obs:
            return ToolResult(success=False, error=obs["error"])
        
        content = f"Title: {obs['title']}\nURL: {obs['url']}\nContent: {obs['content']}"
        return ToolResult(success=True, output=content)

class BrowserClickTool(Tool):
    name = "browser_click"
    description = "Clicks an element on the page using a CSS selector. If submitting a consequential form, requires confirmation."
    requires_confirmation = True

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        if not user_confirmed and self.requires_confirmation:
            return ToolResult(success=False, error="AWAITING_CONFIRMATION")
            
        selector = kwargs.get("selector")
        if not selector:
            return ToolResult(success=False, error="Selector required")
            
        success = browser_agent.click(selector)
        if success:
            return ToolResult(success=True, output=f"Clicked {selector}")
        return ToolResult(success=False, error=f"Failed to click {selector}")

class BrowserTypeTool(Tool):
    name = "browser_type"
    description = "Types text into an input field on the page using a CSS selector."
    requires_confirmation = False

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        selector = kwargs.get("selector")
        text = kwargs.get("text")
        if not selector or not text:
            return ToolResult(success=False, error="Selector and text required")
            
        success = browser_agent.type_text(selector, text)
        if success:
            return ToolResult(success=True, output=f"Typed text into {selector}")
        return ToolResult(success=False, error=f"Failed to type into {selector}")

class BrowserExtractTool(Tool):
    name = "browser_extract"
    description = "Extracts specific elements from the page using a CSS selector."
    requires_confirmation = False

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        selector = kwargs.get("selector")
        if not selector:
            return ToolResult(success=False, error="Selector required")
            
        result = browser_agent.extract(selector)
        return ToolResult(success=True, output=f"Extracted: {result}")
