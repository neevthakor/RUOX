import unittest
from unittest.mock import MagicMock
from app.core.agent import RUOXAgent
from app.core.state import Task
from app.tools.registry import tool_registry

class MockLLMRouter:
    def __init__(self):
        self._provider = MagicMock()
        self._provider.last_tools = None
        
        def mock_stream(messages, tools=None):
            self._provider.last_tools = tools
            yield {"message": {"content": "Response"}}
            
        self._provider.stream = mock_stream
        self._provider.generate = MagicMock(return_value={"message": {"content": "[]"}})

    def get_provider(self, *args, **kwargs):
        return self._provider

class TestAgentLifecycle(unittest.TestCase):
    def setUp(self):
        self.router = MockLLMRouter()
        self.agent = RUOXAgent(self.router)
        self.provider = self.router.get_provider()
        
    def test_direct_intent_no_tools(self):
        # 1. First request
        task = Task(goal="Hello RUOX")
        self.agent.run_task(task)
        
        self.assertEqual(task.status, "WAITING_USER")
        self.assertIsNone(self.provider.last_tools)
        
        # 2. Second request (TOOL intent)
        task2 = Task(goal="What time is it in Tokyo?")
        self.agent.run_task(task2)
        self.assertEqual(task2.status, "WAITING_USER")
        # For a math query (TOOL intent), tools should be provided
        self.assertIsNotNone(self.provider.last_tools)
        
    def test_bounded_iterations(self):
        provider = self.router.get_provider()
        
        def infinite_tool_stream(messages, tools=None):
            # Always return a tool call
            yield {"message": {"tool_calls": [{"function": {"name": "get_current_time", "arguments": {}}}]}}
            
        provider.stream = infinite_tool_stream
        
        # We must use a goal that does NOT hit the deterministic bypass,
        # otherwise we can't test the agent generation loop protection!
        task = Task(goal="What time is it in Tokyo?")
        # Register tool so it executes
        from app.tools.system import SystemTimeTool
        tool_registry.register(SystemTimeTool())
        
        self.agent.run_task(task)
        
        # Loop protection should catch the duplicate identical args tool call and abort safely
        self.assertEqual(task.status, "FAILED")
        self.assertTrue(any("stuck in a loop" in m.get("content", "") for m in task.messages))
        
    def test_deterministic_bypass(self):
        # A simple bypass like time
        task = Task(goal="What time is it?")
        from app.tools.system import SystemTimeTool
        tool_registry.register(SystemTimeTool())
        
        self.agent.run_task(task)
        # Should bypass LLM completely and return WAITING_USER instantly
        self.assertEqual(task.status, "WAITING_USER")
        # Ensure it generated a message containing the time
        self.assertTrue(any(m["role"] == "assistant" for m in task.messages))
        # Ensure the LLM was never called
        self.assertIsNone(self.provider.last_tools)
        
    def test_arithmetic_bypass(self):
        # A basic arithmetic bypass
        task = Task(goal="What is 2+2?")
        self.agent.run_task(task)
        # Should bypass LLM completely and output "4"
        self.assertEqual(task.status, "WAITING_USER")
        messages = [m["content"] for m in task.messages if m["role"] == "assistant"]
        self.assertTrue(len(messages) > 0)
        self.assertEqual(messages[-1], "4")
        
    def test_plan_terminates(self):
        provider = self.router.get_provider()
        
        # Register the tool so validation passes
        from app.tools.computer import ListDirectoryTool
        tool_registry.register(ListDirectoryTool())
        
        # Mock planner to generate a valid plan with a relevant tool
        provider.generate.return_value = {"message": {"content": '[{"description": "d", "tool_name": "list_directory", "arguments": {"path": "."}}]'}}
        
        def normal_stream(messages, tools=None):
            yield {"message": {"content": "Done plan"}}
            
        provider.stream = normal_stream
        
        task = Task(goal="Find all files and count them")
        self.agent.run_task(task)
        
        self.assertEqual(task.status, "WAITING_USER")

if __name__ == "__main__":
    unittest.main()
