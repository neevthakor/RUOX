import unittest
import os
import tempfile
from pathlib import Path
from app.memory.database import DatabaseManager
from app.memory.store import MemoryStore
from app.memory.task_store import TaskStore
from app.memory.models import Memory, MemoryType
from app.memory.manager import MemoryManager
from app.core.state import Task, TaskStep

class TestMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_memory.db")
        self.db_manager = DatabaseManager(self.db_path)
        self.db_manager.initialize_db()
        self.store = MemoryStore(self.db_manager)
        self.manager = MemoryManager()
        self.manager.store = self.store
        self.task_store = TaskStore(self.db_manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_idempotency(self):
        # Initializing again should not throw errors
        self.db_manager.initialize_db()
        self.assertTrue(Path(self.db_path).exists())

    def test_memory_crud(self):
        mem = Memory(memory_type=MemoryType.EPISODIC, content="I love testing")
        mem_id = self.store.add_memory(mem)
        
        fetched = self.store.get_memory(mem_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.content, "I love testing")
        
        fetched.content = "I love testing more"
        self.store.update_memory(fetched)
        
        fetched_again = self.store.get_memory(mem_id)
        self.assertEqual(fetched_again.content, "I love testing more")
        
        self.store.delete_memory(mem_id)
        self.assertIsNone(self.store.get_memory(mem_id))

    def test_memory_manager_add_and_dedup(self):
        id1 = self.manager.add_explicit_memory("My name is Alice")
        fetched1 = self.store.get_memory(id1)
        self.assertEqual(fetched1.importance, 0.5)
        self.assertEqual(fetched1.access_count, 0)
        
        # Adding identical should deduplicate and bump importance/access
        id2 = self.manager.add_explicit_memory("my name is alice")
        self.assertEqual(id1, id2)
        
        fetched2 = self.store.get_memory(id1)
        self.assertEqual(fetched2.access_count, 1)
        self.assertEqual(fetched2.importance, 0.6)
        
    def test_relevance_search(self):
        self.manager.add_explicit_memory("My favorite color is blue.")
        self.manager.add_explicit_memory("Python is great.")
        self.manager.add_explicit_memory("The sky is blue today.")
        
        # Searching for 'blue'
        results = self.manager.search_relevant_memories("What is my favorite color and is it blue?")
        self.assertTrue(len(results) > 0)
        self.assertTrue(any("favorite color" in m.content for m in results))

    def test_secret_redaction(self):
        with self.assertRaises(ValueError):
            self.manager.add_explicit_memory("Here is my secret: OPENAI_API_KEY=sk-1234567890abcdef")

    def test_task_persistence(self):
        t = Task(goal="Run some tests", status="PENDING")
        self.task_store.save_task(t)
        
        t.status = "DONE"
        self.task_store.save_task(t)
        
        recent = self.task_store.get_recent_tasks()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]['status'], "DONE")
        self.assertEqual(recent[0]['goal'], "Run some tests")

if __name__ == "__main__":
    unittest.main()
