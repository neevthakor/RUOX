import unittest
import os
from unittest.mock import patch, MagicMock
from app.vision.models import BoundingBox, TextElement, ScreenContext
from app.vision.safety import validate_coordinates, get_temp_screenshot_dir
from app.vision.analyzer import format_screen_context
from app.vision import ScreenContextTool, AnalyzeScreenTool, CaptureScreenTool

class TestVisionSafety(unittest.TestCase):
    def test_validate_coordinates(self):
        # within bounds
        self.assertTrue(validate_coordinates(BoundingBox(x=10, y=10, w=100, h=100), 1920, 1080))
        # out of bounds x
        self.assertFalse(validate_coordinates(BoundingBox(x=-10, y=10, w=100, h=100), 1920, 1080))
        # out of bounds width
        self.assertFalse(validate_coordinates(BoundingBox(x=1900, y=10, w=100, h=100), 1920, 1080))

class TestVisionAnalyzer(unittest.TestCase):
    def test_format_screen_context(self):
        ctx = ScreenContext(
            width=1920,
            height=1080,
            active_window="Test Window",
            elements=[
                TextElement(text="Settings", bbox=BoundingBox(x=10, y=10, w=50, h=20), confidence=90.0)
            ],
            timestamp=123456.0,
            screenshot_id="test_id"
        )
        formatted = format_screen_context(ctx)
        self.assertIn("1920x1080", formatted)
        self.assertIn("Test Window", formatted)
        self.assertIn("Settings", formatted)

class TestVisionTools(unittest.TestCase):
    @patch("app.vision.capture.screen_capturer.capture")
    def test_capture_tool(self, mock_capture):
        mock_capture.return_value = {
            "width": 1024,
            "height": 768,
            "active_window": "VS Code",
            "timestamp": 1000.0,
            "screenshot_id": "test_id",
            "filepath": "fake.png"
        }
        tool = CaptureScreenTool()
        res = tool._run({})
        self.assertIn("1024x768", res)
        self.assertIn("VS Code", res)
        
    @patch("app.vision.analyzer.screen_analyzer.get_context")
    def test_analyze_tool(self, mock_get_context):
        ctx = ScreenContext(
            width=800, height=600, active_window=None, elements=[], timestamp=1.0, screenshot_id="1"
        )
        mock_get_context.return_value = ctx
        tool = AnalyzeScreenTool()
        res = tool._run({"question": "Where is the button?"})
        self.assertIn("Where is the button?", res)
        self.assertIn("800x600", res)

if __name__ == "__main__":
    unittest.main()
