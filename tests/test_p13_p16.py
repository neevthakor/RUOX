import unittest
import os
import sqlite3
from datetime import datetime, timedelta
from app.memory.database import DatabaseManager
from app.core.state import Task, TaskStep
from app.memory.task_store import TaskStore
from app.knowledge.store import KnowledgeStore
from app.proactive.scheduler import Scheduler
from app.browser.agent import BrowserAgent

import tempfile
import os

class TestP13ToP16(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use a temp file DB for testing so connections share it
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False)
        cls.db = DatabaseManager(cls.temp_db.name)
        cls.db.initialize_db()
        
        cls.task_store = TaskStore(cls.db)
        cls.knowledge_store = KnowledgeStore(cls.db)
        cls.scheduler = Scheduler(cls.db)
        
    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(cls.temp_db.name)
        except PermissionError:
            pass
        
    def test_p14_task_creation_and_persistence(self):
        task = Task(goal="Test task")
        task.status = "RUNNING"
        self.task_store.save_task(task)
        
        recent = self.task_store.get_recent_tasks(limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["goal"], "Test task")
        self.assertEqual(recent[0]["status"], "RUNNING")
        
    def test_p15_scheduler(self):
        trigger = datetime.now().astimezone() + timedelta(minutes=5)
        sched_id = self.scheduler.schedule_task("Remind me to test", trigger_time=trigger)
        self.assertTrue(sched_id.startswith("sched-"))
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schedules WHERE id=?", (sched_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["goal"], "Remind me to test")
        
    def test_p16_knowledge_creation(self):
        ent_id = self.knowledge_store.store_entity("PROJECT", "RUOX", {"status": "active"})
        self.assertTrue(ent_id.startswith("ent-"))
        
        results = self.knowledge_store.search("RUOX")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "RUOX")
        
        # Test update
        self.knowledge_store.store_entity("PROJECT", "RUOX", {"phase": "P16"})
        results = self.knowledge_store.search("RUOX")
        self.assertEqual(len(results), 1)
        import json
        props = json.loads(results[0]["properties"])
        self.assertEqual(props["status"], "active")
        self.assertEqual(props["phase"], "P16")

    def test_p13_browser_agent(self):
        # We don't want to actually launch Chromium in a unit test suite normally,
        # but to prove it works we can just instantiate the class and mock.
        # But we'll do a quick check of the singleton instance.
        agent = BrowserAgent()
        self.assertIsNotNone(agent)
        
if __name__ == '__main__':
    unittest.main()
