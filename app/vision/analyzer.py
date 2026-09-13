import os
from typing import Dict, Any
from app.vision.models import ScreenContext
from app.vision.capture import screen_capturer
from app.vision.ocr import get_ocr_provider
from app.vision.safety import cleanup_screenshots

class ScreenAnalyzer:
    def __init__(self):
        self.ocr_provider = get_ocr_provider()
        
    def get_context(self) -> ScreenContext:
        """Captures screen, runs OCR, formats context, and cleans up."""
        capture_meta = screen_capturer.capture()
        
        try:
            elements = self.ocr_provider.extract_text(capture_meta["filepath"])
        except Exception as e:
            elements = []
            
        context = ScreenContext(
            width=capture_meta["width"],
            height=capture_meta["height"],
            active_window=capture_meta["active_window"],
            elements=elements,
            timestamp=capture_meta["timestamp"],
            screenshot_id=capture_meta["screenshot_id"]
        )
        
        # Cleanup
        cleanup_screenshots()
        return context

screen_analyzer = ScreenAnalyzer()

def format_screen_context(context: ScreenContext) -> str:
    """Formats the context into a string for the LLM."""
    lines = []
    lines.append(f"Screen Dimensions: {context.width}x{context.height}")
    
    if context.active_window:
        lines.append(f"Active Foreground Window: {context.active_window}")
        
    lines.append("\nVisible Text:")
    
    if not context.elements:
        lines.append("(No readable text found on screen or OCR unavailable)")
    else:
        # Just return the text strings for general context to save tokens
        # Sort roughly by Y then X
        sorted_elements = sorted(context.elements, key=lambda e: (e.bbox.y if e.bbox else 0, e.bbox.x if e.bbox else 0))
        text_lines = []
        for el in sorted_elements:
            text_lines.append(el.text)
        
        # Join into a paragraph-like structure to save vertical space
        text_block = " ".join(text_lines)
        max_chars = int(os.getenv("SCREEN_ANALYSIS_MAX_TEXT_CHARS", "12000"))
        if len(text_block) > max_chars:
            text_block = text_block[:max_chars] + "... [TRUNCATED]"
            
        lines.append(text_block)
        
    return "\n".join(lines)
