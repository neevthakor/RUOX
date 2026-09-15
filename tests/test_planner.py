import unittest
import json
from unittest.mock import MagicMock

from app.core.planner import Planner
from app.core.executor import Executor
from app.core.state import Plan, PlanStep, Task
from app.llm.base import LLMProvider
from app.tools.registry import tool_registry
from app.tools.base import Tool, ToolResult

class MockTool(Tool):
    name = "mock_tool"
    description = "A mock tool"
    requires_confirmation = False

    def _run(self, input_data: dict):
        return "success"

class MockConfirmTool(Tool):
    name = "mock_confirm_tool"
    description = "A mock tool needing confirmation"
    requires_confirmation = True

    def _run(self, input_data: dict):
        return "success_confirmed"

class MockLLM(LLMProvider):
    def __init__(self, response_content=""):
        self.response_content = response_content

    def generate(self, messages, tools=None):
        return {"message": {"content": self.response_content}}

    def stream(self, messages, tools=None):
        pass

    def supports_vision(self): return False
    def supports_tools(self): return True
    def is_available(self): return True

class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLM()
        self.planner = Planner(self.llm)
        tool_registry.register(MockTool())
        tool_registry.register(MockConfirmTool())

    def test_classify_intent(self):
        self.assertEqual(self.planner.classify_intent("hello"), "DIRECT_SIMPLE")
        self.assertEqual(self.planner.classify_intent("who are you"), "DIRECT_SIMPLE")
        self.assertEqual(self.planner.classify_intent("find all python files and count them"), "PLAN")
        self.assertEqual(self.planner.classify_intent("what time is it"), "TOOL_SIMPLE")
        self.assertEqual(self.planner.classify_intent("open calculator"), "TOOL_COMPLEX")

    def test_generate_plan(self):
        self.llm.response_content = json.dumps([
            {"description": "Test step", "tool_name": "mock_tool", "arguments": {"x": 1}}
        ])
        plan = self.planner.generate_plan("Do something", [])
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].tool_name, "mock_tool")

    def test_validate_plan(self):
        plan = Plan(steps=[
            PlanStep(step_id=1, description="Step 1", tool_name="mock_tool", arguments={}),
        ])
        self.assertTrue(self.planner.validate_plan(plan))

        invalid_plan = Plan(steps=[
            PlanStep(step_id=1, description="Step 1", tool_name="unknown_tool", arguments={}),
        ])
        self.assertFalse(self.planner.validate_plan(invalid_plan))
        
        # Test unrelated tool rejection
        # get_current_time is a real tool, but not relevant to "create a file"
        from app.tools.system import SystemTimeTool
        tool_registry.register(SystemTimeTool())
        unrelated_plan = Plan(steps=[
            PlanStep(step_id=1, description="Step 1", tool_name="get_current_time", arguments={}),
        ])
        # It should fail because get_current_time is not in the schema for "create a file"
        self.assertFalse(self.planner.validate_plan(unrelated_plan, goal="create a file"))

class TestExecutor(unittest.TestCase):
    def setUp(self):
        tool_registry.register(MockTool())
        tool_registry.register(MockConfirmTool())
        
    def test_execute_plan_success(self):
        executor = Executor(callbacks={"on_print": lambda x, y: None})
        plan = Plan(steps=[
            PlanStep(step_id=1, description="Step 1", tool_name="mock_tool", arguments={}),
        ])
        
        executed = executor.execute_plan(plan, "test_task")
        self.assertEqual(executed.status, "COMPLETED")
        self.assertEqual(executed.steps[0].status, "COMPLETED")
        self.assertEqual(executed.steps[0].result, "success")

    def test_execute_plan_confirmation(self):
        # We need to simulate user input returning 'y'
        executor = Executor(callbacks={
            "on_print": lambda x, y: None,
            "on_input": lambda x: "y"
        })
        plan = Plan(steps=[
            PlanStep(step_id=1, description="Step 1", tool_name="mock_confirm_tool", arguments={}),
        ])
        
        executed = executor.execute_plan(plan, "test_task")
        self.assertEqual(executed.status, "COMPLETED")
        self.assertEqual(executed.steps[0].status, "COMPLETED")
        self.assertEqual(executed.steps[0].result, "success_confirmed")

    def test_execute_plan_denial(self):
        # Simulate user input returning 'n'
        executor = Executor(callbacks={
            "on_print": lambda x, y: None,
            "on_input": lambda x: "n"
        })
        plan = Plan(steps=[
            PlanStep(step_id=1, description="Step 1", tool_name="mock_confirm_tool", arguments={}),
        ])
        
        executed = executor.execute_plan(plan, "test_task")
        self.assertEqual(executed.status, "FAILED")
        self.assertEqual(executed.steps[0].status, "CANCELLED")

if __name__ == '__main__':
    unittest.main()
