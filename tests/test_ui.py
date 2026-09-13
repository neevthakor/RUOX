import unittest
import os
from unittest.mock import patch, MagicMock

# Skip GUI tests in headless CI easily by catching import errors
try:
    import customtkinter
    from app.ui.hud import RUOXHUD
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

class TestUI(unittest.TestCase):
    @unittest.skipIf(not HAS_GUI, "GUI libraries not available")
    @patch("app.ui.hud.OllamaProvider")
    @patch("app.ui.hud.threading.Thread")
    def test_hud_initialization(self, mock_thread, mock_ollama):
        # Prevent actual thread start
        app = RUOXHUD()
        self.assertEqual(app.status_label.cget("text"), "IDLE")
        
        # Test state change
        app.set_state("THINKING")
        self.assertEqual(app.status_label.cget("text"), "THINKING")
        
        # Test chat append
        app.append_chat("Test msg")
        
        # Test approval resolve
        app.set_state("WAITING_APPROVAL", {"tool": "test", "args": {}, "desc": ""})
        self.assertEqual(app.status_label.cget("text"), "WAITING_APPROVAL")
        
        app._resolve_approval("y")
        self.assertEqual(app.approval_result, "y")
        self.assertEqual(app.status_label.cget("text"), "TOOL_EXECUTION")
        
        # Cleanup
        app.destroy()

if __name__ == "__main__":
    unittest.main()
