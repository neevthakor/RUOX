from html.parser import HTMLParser
import re

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
        self.current_tag = ""
        self.skip_tags = {'script', 'style', 'noscript', 'meta', 'link', 'head', 'nav', 'footer', 'header'}

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag

    def handle_endtag(self, tag):
        self.current_tag = ""

    def handle_data(self, d):
        if self.current_tag not in self.skip_tags:
            d = d.strip()
            if d:
                self.text.append(d)

    def get_data(self):
        # Join with space, then clean up excessive whitespace
        raw_text = ' '.join(self.text)
        cleaned = re.sub(r'\s+', ' ', raw_text)
        return cleaned.strip()

def extract_text_from_html(html_content: str, max_chars: int = 30000) -> str:
    extractor = TextExtractor()
    try:
        extractor.feed(html_content)
    except Exception:
        pass # Ignore parse errors, return what we have
    
    text = extractor.get_data()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[TRUNCATED]"
    return text

def format_untrusted_content(text: str) -> str:
    return f"\n--- UNTRUSTED WEB CONTENT ---\n{text}\n--- END UNTRUSTED WEB CONTENT ---\n"
