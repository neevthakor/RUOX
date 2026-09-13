import unittest
from unittest.mock import MagicMock
from app.core.agent import RUOXAgent
from app.core.state import Task

class TestAgent(unittest.TestCase):
    def test_agent_run_task(self):
        # Mock Router and Provider
        mock_provider = MagicMock()
        # Mock stream to yield a chunk
        mock_provider.stream.return_value = [{"message": {"content": "Hello user"}}]
        
        mock_router = MagicMock()
        mock_router.get_provider.return_value = mock_provider
        
        agent = RUOXAgent(mock_router)
        task = Task(goal="Say hello")
        
        result_task = agent.run_task(task)
        
        self.assertEqual(result_task.status, "WAITING_USER")
        self.assertTrue(len(result_task.messages) >= 3) # System, User, Assistant
        self.assertEqual(result_task.messages[-1]["role"], "assistant")
        self.assertEqual(result_task.messages[-1]["content"], "Hello user")

if __name__ == "__main__":
    unittest.main()
