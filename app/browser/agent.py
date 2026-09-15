import threading
from playwright.sync_api import sync_playwright, Page, BrowserContext
from typing import Optional, Dict, Any

class BrowserAgent:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(BrowserAgent, cls).__new__(cls)
                cls._instance.initialize()
            return cls._instance

    def initialize(self):
        self.playwright = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._pw_thread = None

    def start(self):
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.context = self.browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 720}
            )
            self.page = self.context.new_page()

    def stop(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def ensure_started(self):
        if not self.page:
            self.start()

    def navigate(self, url: str) -> bool:
        self.ensure_started()
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return True
        except Exception as e:
            print(f"Browser navigate error: {e}")
            return False

    def get_observation(self) -> Dict[str, Any]:
        self.ensure_started()
        try:
            title = self.page.title()
            url = self.page.url
            
            # Simple heuristic for stripping prompt injection in observation
            # Ideally done in LLM pipeline but we can scrub some text
            text_content = self.page.evaluate("document.body.innerText")
            if text_content and len(text_content) > 10000:
                text_content = text_content[:10000] + "... (truncated)"
                
            return {
                "title": title,
                "url": url,
                "content": text_content
            }
        except Exception as e:
            return {"error": str(e)}
            
    def click(self, selector: str) -> bool:
        self.ensure_started()
        try:
            # We wait a bit to see if it's there
            element = self.page.locator(selector).first
            if not element.is_visible(timeout=5000):
                return False
            element.click()
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            return True
        except Exception as e:
            print(f"Browser click error: {e}")
            return False

    def type_text(self, selector: str, text: str) -> bool:
        self.ensure_started()
        try:
            element = self.page.locator(selector).first
            if not element.is_visible(timeout=5000):
                return False
            element.fill(text)
            return True
        except Exception as e:
            print(f"Browser type error: {e}")
            return False

    def extract(self, selector: str) -> str:
        self.ensure_started()
        try:
            element = self.page.locator(selector)
            if element.count() == 0:
                return ""
            return element.all_inner_texts()
        except Exception as e:
            return f"Error: {e}"

browser_agent = BrowserAgent()
