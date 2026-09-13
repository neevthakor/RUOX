import unittest
import os
from pathlib import Path
from app.core.config import get_project_root, get_system_context
from app.tools.computer.filesystem import _resolve_path

class TestConfig(unittest.TestCase):
    def test_project_root_default(self):
        # Without env var, it should resolve relative to __file__
        original_env = os.environ.get("RUOX_PROJECT_ROOT")
        if "RUOX_PROJECT_ROOT" in os.environ:
            del os.environ["RUOX_PROJECT_ROOT"]
            
        root = get_project_root()
        self.assertTrue(root.is_absolute())
        self.assertEqual(root.name, "RUOX")  # Assuming tests run in RUOX dir
        
        if original_env is not None:
            os.environ["RUOX_PROJECT_ROOT"] = original_env

    def test_project_root_env_var(self):
        os.environ["RUOX_PROJECT_ROOT"] = "/fake/root"
        root = get_project_root()
        self.assertEqual(str(root), str(Path("/fake/root").resolve()))
        del os.environ["RUOX_PROJECT_ROOT"]

    def test_system_context(self):
        ctx = get_system_context()
        self.assertIn("RUOX Project Root:", ctx)
        self.assertIn("Operating System:", ctx)

    def test_path_resolution(self):
        os.environ["RUOX_PROJECT_ROOT"] = "/fake/root"
        # Relative path resolves to root
        p = _resolve_path("subfolder")
        self.assertEqual(str(p), str(Path("/fake/root/subfolder").resolve()))
        
        # Absolute path remains absolute
        p = _resolve_path("/absolute/path")
        self.assertEqual(str(p), str(Path("/absolute/path").resolve()))
        
        del os.environ["RUOX_PROJECT_ROOT"]

if __name__ == "__main__":
    unittest.main()
