import unittest
from app.tools.system import SystemTimeTool

class TestSystemTimeTool(unittest.TestCase):
    def test_get_current_time(self):
        tool = SystemTimeTool()
        self.assertFalse(tool.requires_confirmation)
        
        result = tool.execute({})
        self.assertTrue(result.success)
        self.assertIn("current_time", result.output)
        self.assertIn("timezone", result.output)
        self.assertIn("iso8601", result.output)

    def test_get_system_info(self):
        from app.tools.system import SystemInfoTool
        tool = SystemInfoTool()
        self.assertFalse(tool.requires_confirmation)
        
        result = tool.execute({})
        self.assertTrue(result.success)
        self.assertIn("os", result.output)
        self.assertIn("python_version", result.output)

if __name__ == "__main__":
    unittest.main()
