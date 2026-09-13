import unittest
from app.security.permissions import global_security_state, PermissionLevel
from app.tools.computer.shell import RunCommandTool
from app.tools.registry import ToolRegistry

class TestPermissions(unittest.TestCase):
    def test_permission_enforcement(self):
        # By default, LOCAL_ONLY is True
        self.assertTrue(global_security_state.local_only_mode)
        
        # Test a tool that requires confirmation
        tool = RunCommandTool()
        self.assertTrue(tool.requires_confirmation)
        
        input_data = {"command": "pip install x"}
        
        # Should fail if not confirmed
        result = tool.execute(input_data, user_confirmed=False)
        self.assertFalse(result.success)
        self.assertEqual(result.error, "AWAITING_CONFIRMATION")
        
        # Should succeed if confirmed
        result = tool.execute(input_data, user_confirmed=True)
        self.assertTrue(result.success)
        
        # Scenario 2: Emergency kill switch enabled (computer control disabled)
        global_security_state.disable_computer_control()
        result_override = tool.execute(input_data, user_confirmed=True) # Even if confirmed!
        self.assertFalse(result_override.success)
        self.assertEqual(result_override.error, "COMPUTER_CONTROL_DISABLED")

if __name__ == '__main__':
    unittest.main()
