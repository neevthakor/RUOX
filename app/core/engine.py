import threading
import time
from app.memory.task_store import task_store
from app.core.agent import RUOXAgent
from app.core.state import Task

class TaskEngine:
    def __init__(self, agent: RUOXAgent):
        self.agent = agent
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def resume_incomplete_tasks(self):
        # On startup, find running tasks and mark them as PAUSED or ask to resume
        conn = task_store.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, goal FROM tasks WHERE status IN ('RUNNING', 'READY', 'RECOVERING')")
            tasks = cursor.fetchall()
            for t in tasks:
                cursor.execute("UPDATE tasks SET status = 'PAUSED' WHERE id = ?", (t["id"],))
                print(f"\n[Task Engine] Found incomplete task: {t['goal']} (Paused. Say 'resume task' to continue.)")
            conn.commit()
        finally:
            conn.close()

    def _loop(self):
        while self.running:
            try:
                self._process_background_tasks()
            except Exception as e:
                pass
            time.sleep(10)

    def _process_background_tasks(self):
        # Background processing is complex because of stdout/stdin contention.
        # For P14, we primarily ensure task state is persisted and can be resumed.
        # A fully parallel agent requires a message queue.
        # We will focus on the persistence, checkpointing, and recovery.
        pass

task_engine = None

def init_engine(agent):
    global task_engine
    task_engine = TaskEngine(agent)
    task_engine.resume_incomplete_tasks()
    task_engine.start()
    return task_engine
