import unittest
from unittest.mock import MagicMock
from app.tools.registry import ToolRegistry, tool_registry
from app.core.agent import RUOXAgent
from app.core.state import Task

from app.tools.system import SystemTimeTool, SystemInfoTool
from app.tools.memory import RememberInformationTool, SearchMemoryTool
from app.tools.computer import OpenApplicationTool, RunCommandTool
from app.vision import ScreenContextTool
from app.tools.web import WebSearchTool

class TestP61Regression(unittest.TestCase):
    def setUp(self):
        # We can use the global tool registry to test context routing
        self.registry = tool_registry
        self.registry.register(SystemTimeTool())
        self.registry.register(SystemInfoTool())
        self.registry.register(RememberInformationTool())
        self.registry.register(SearchMemoryTool())
        self.registry.register(OpenApplicationTool())
        self.registry.register(RunCommandTool())
        self.registry.register(ScreenContextTool())
        self.registry.register(WebSearchTool())
        
    def test_01_simple_chat_no_tools(self):
        schemas = self.registry.get_schemas_for_context("Hello RUOX")
        self.assertEqual(len(schemas), 0, "Simple chat should expose 0 tools")
        
    def test_02_system_tool_routing(self):
        schemas = self.registry.get_schemas_for_context("What time is it?")
        names = [s["function"]["name"] for s in schemas]
        self.assertIn("get_current_time", names)
        self.assertIn("get_system_info", names)
        
    def test_03_memory_tool_routing(self):
        schemas = self.registry.get_schemas_for_context("Remember that my favorite language is Python.")
        names = [s["function"]["name"] for s in schemas]
        self.assertIn("remember_information", names)
        self.assertIn("search_memory", names)

    def test_04_computer_tool_routing(self):
        schemas = self.registry.get_schemas_for_context("Open Calculator app.")
        names = [s["function"]["name"] for s in schemas]
        self.assertIn("open_application", names)
        
    def test_05_vision_tool_routing(self):
        schemas = self.registry.get_schemas_for_context("What is on my screen?")
        names = [s["function"]["name"] for s in schemas]
        self.assertIn("screen_context", names)
        
    def test_06_web_tool_routing(self):
        schemas = self.registry.get_schemas_for_context("Search the web for news.")
        names = [s["function"]["name"] for s in schemas]
        self.assertIn("web_search", names)
        
    def test_07_bounded_conversation_context(self):
        mock_provider = MagicMock()
        mock_provider.stream.return_value = [{"message": {"content": "Response"}}]
        mock_router = MagicMock()
        mock_router.get_provider.return_value = mock_provider
        
        agent = RUOXAgent(mock_router)
        task = Task(goal="Test context bound")
        
        task.messages.append({"role": "system", "content": "Sys"})
        for i in range(19):
            task.messages.append({"role": "user" if i%2==0 else "assistant", "content": f"msg{i}"})
            
        agent.run_task(task)
        
        call_args = mock_provider.stream.call_args
        passed_messages = call_args[0][0]
        
        # 1 system + 10 recent history = 11 messages maximum passed
        self.assertTrue(len(passed_messages) <= 11)
        self.assertEqual(passed_messages[0]["role"], "system")
        
    def test_10_streaming(self):
        on_token_called = False
        def token_cb(text):
            nonlocal on_token_called
            on_token_called = True
            
        agent = RUOXAgent(MagicMock(), callbacks={"on_token": token_cb})
        
        mock_provider = MagicMock()
        mock_provider.stream.return_value = [{"message": {"content": "Chunk1"}}]
        agent.router.get_provider.return_value = mock_provider
        
        task = Task(goal="Stream")
        agent.run_task(task)
        self.assertTrue(on_token_called)
        
    def test_11_cancellation(self):
        cancel_checked = False
        def cancel_cb():
            nonlocal cancel_checked
            cancel_checked = True
            return True # Cancel immediately
            
        agent = RUOXAgent(MagicMock(), callbacks={"on_cancel_check": cancel_cb})
        
        mock_provider = MagicMock()
        mock_provider.stream.return_value = [{"message": {"content": "Chunk"}} for _ in range(5)]
        agent.router.get_provider.return_value = mock_provider
        
        task = Task(goal="Cancel")
        agent.run_task(task)
        
        self.assertTrue(cancel_checked)
        self.assertEqual(task.status, "WAITING_USER")

    def test_13_ui_queue(self):
        import queue
        ui_queue = queue.Queue()
        agent = RUOXAgent(MagicMock(), callbacks={
            "on_print": lambda text, end: ui_queue.put({"type": "print"})
        })
        
        mock_provider = MagicMock()
        mock_provider.stream.return_value = [{"message": {"content": "Hello"}}]
        agent.router.get_provider.return_value = mock_provider
        
        task = Task(goal="Queue")
        agent.run_task(task)
        
        self.assertTrue(not ui_queue.empty())
        item = ui_queue.get()
        self.assertEqual(item["type"], "print")
        
    def test_15_approval_flow(self):
        deny_called = False
        def input_cb(prompt):
            nonlocal deny_called
            deny_called = True
            return "n"
            
        agent = RUOXAgent(MagicMock(), callbacks={"on_input": input_cb})
        mock_provider = MagicMock()
        
        mock_provider.stream.side_effect = [
            [{
                "message": {
                    "tool_calls": [{
                        "function": {"name": "run_command", "arguments": '{"command": "echo bad"}'}
                    }]
                }
            }],
            [{"message": {"content": "I am done."}}]
        ]
        agent.router.get_provider.return_value = mock_provider
        
        task = Task(goal="Run bad cmd")
        
        # Mock the tool inside the registry to always demand confirmation
        real_tool = self.registry.get_tool("run_command")
        original_execute = real_tool.execute
        def mock_execute(args, user_confirmed=False):
            if not user_confirmed:
                from app.tools.base import ToolResult
                return ToolResult(success=False, error="AWAITING_CONFIRMATION")
            return original_execute(args, user_confirmed)
            
        real_tool.execute = mock_execute
        
        agent.run_task(task)
        
        real_tool.execute = original_execute
        self.assertTrue(deny_called)
        
if __name__ == '__main__':
    unittest.main()
