from app.tools.base import Tool
from app.security.permissions import PermissionLevel
from app.vision.analyzer import screen_analyzer, format_screen_context

class ScreenContextTool(Tool):
    name = "screen_context"
    description = "Provides a structured textual representation of the current screen, active window, and visible text."
    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    permission_level = PermissionLevel.LOW_RISK

    def _run(self, input_data: dict):
        try:
            ctx = screen_analyzer.get_context()
            return format_screen_context(ctx)
        except Exception as e:
            return f"Failed to get screen context: {str(e)}"

class AnalyzeScreenTool(Tool):
    name = "analyze_screen"
    description = "Analyzes the user's current screen to answer a specific question about what is visible or what errors are present."
    input_schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The specific question about the screen to answer."}
        },
        "required": ["question"]
    }
    permission_level = PermissionLevel.LOW_RISK

    def _run(self, input_data: dict):
        # We fetch the context, then return it so the main agent can answer the question.
        # This keeps the logic localized to the existing LLM.
        try:
            ctx = screen_analyzer.get_context()
            formatted = format_screen_context(ctx)
            return (
                f"Question to answer: {input_data.get('question')}\n\n"
                f"Current Screen Information:\n{formatted}\n\n"
                f"(Answer the user's question based ONLY on the observed screen info above.)"
            )
        except Exception as e:
            return f"Failed to analyze screen: {str(e)}"

class CaptureScreenTool(Tool):
    name = "capture_screen"
    description = "Captures the screen and returns metadata. Does NOT return text. Useful only for raw dimensions."
    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    permission_level = PermissionLevel.LOW_RISK

    def _run(self, input_data: dict):
        try:
            from app.vision.capture import screen_capturer
            from app.vision.safety import cleanup_screenshots
            
            meta = screen_capturer.capture()
            cleanup_screenshots()
            
            return (
                f"Screen Capture Metadata:\n"
                f"Dimensions: {meta['width']}x{meta['height']}\n"
                f"Active Window: {meta['active_window']}\n"
                f"Timestamp: {meta['timestamp']}"
            )
        except Exception as e:
            return f"Failed to capture screen: {str(e)}"
