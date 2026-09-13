import unittest
import os
import tempfile
from pathlib import Path
from app.tools.computer.apps import OpenApplicationTool
from app.tools.computer.filesystem import ListDirectoryTool, GetFileInfoTool, CreateDirectoryTool, OpenPathTool
from app.tools.computer.shell import RunCommandTool, classify_command

class TestComputerTools(unittest.TestCase):
    def test_classify_command(self):
        # Safe commands
        self.assertEqual(classify_command("python --version")[0], "SAFE")
        self.assertEqual(classify_command("git status")[0], "SAFE")
        self.assertEqual(classify_command("dir")[0], "SAFE")
        
        # Blocked commands
        self.assertEqual(classify_command("shutdown /s")[0], "BLOCKED")
        self.assertEqual(classify_command("rmdir /s C:\\")[0], "BLOCKED")
        self.assertEqual(classify_command("del -r something")[0], "BLOCKED")
        self.assertEqual(classify_command("taskkill /im notepad.exe")[0], "BLOCKED")
        
        # Confirmation required
        self.assertEqual(classify_command("pip install x")[0], "CONFIRMATION_REQUIRED")
        self.assertEqual(classify_command("git commit -m 'test'")[0], "CONFIRMATION_REQUIRED")
        self.assertEqual(classify_command("python script.py")[0], "CONFIRMATION_REQUIRED")

    def test_run_command_tool(self):
        tool = RunCommandTool()
        
        # Test safe command
        res = tool.execute({"command": "echo hello"})
        self.assertTrue(res.success)
        self.assertIn("hello", res.output["stdout"].lower())
        
        # Test blocked command
        res = tool.execute({"command": "shutdown /s /t 0"})
        self.assertFalse(res.success)
        self.assertIn("BLOCKED", res.error)
        
        # Test confirmation required without confirmation
        res = tool.execute({"command": "pip install requests"}, user_confirmed=False)
        self.assertFalse(res.success)
        self.assertEqual(res.error, "AWAITING_CONFIRMATION")
        
        # Test confirmation required with confirmation
        res = tool.execute({"command": "echo confirming"}, user_confirmed=True)
        self.assertTrue(res.success)

    def test_filesystem_tools(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "test.txt"
            test_file.write_text("hello")
            
            # List dir
            list_tool = ListDirectoryTool()
            res = list_tool.execute({"path": tmpdir})
            self.assertTrue(res.success)
            self.assertTrue(any(i["name"] == "test.txt" for i in res.output["items"]))
            
            # Get info
            info_tool = GetFileInfoTool()
            res = info_tool.execute({"path": str(test_file)})
            self.assertTrue(res.success)
            self.assertEqual(res.output["size_bytes"], 5)
            
            # Create dir
            mkdir_tool = CreateDirectoryTool()
            new_dir = str(tmp_path / "new_folder")
            res = mkdir_tool.execute({"path": new_dir}, user_confirmed=True)
            self.assertTrue(res.success)
            self.assertTrue(Path(new_dir).exists())
            
if __name__ == "__main__":
    unittest.main()
