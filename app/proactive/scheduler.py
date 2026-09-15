import threading
import time
import uuid
from datetime import datetime
from croniter import croniter
from app.memory.database import db_manager
from app.core.state import Task

class Scheduler:
    def __init__(self, db_manager=db_manager):
        self.db = db_manager
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

    def schedule_task(self, goal: str, trigger_time: datetime = None, cron_expr: str = None) -> str:
        conn = self.db.get_connection()
        try:
            sched_id = "sched-" + str(uuid.uuid4())[:8]
            status = "ACTIVE"
            trigger_str = trigger_time.isoformat() if trigger_time else None
            
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedules (id, goal, trigger_time, cron_expr, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sched_id, goal, trigger_str, cron_expr, status, datetime.now().astimezone().isoformat()))
            conn.commit()
            return sched_id
        finally:
            conn.close()

    def cancel_schedule(self, goal_query: str) -> bool:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            term = f"%{goal_query}%"
            cursor.execute("UPDATE schedules SET status = 'CANCELLED' WHERE goal LIKE ? AND status = 'ACTIVE'", (term,))
            success = cursor.rowcount > 0
            conn.commit()
            return success
        finally:
            conn.close()

    def _loop(self):
        from app.memory.task_store import task_store
        while self.running:
            try:
                self._check_schedules(task_store)
            except Exception as e:
                print(f"[Scheduler] Error: {e}")
            time.sleep(60) # check every minute

    def _check_schedules(self, task_store):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedules WHERE status = 'ACTIVE'")
            schedules = cursor.fetchall()
            
            now = datetime.now().astimezone()
            
            for sched in schedules:
                should_run = False
                trigger_time_str = sched["trigger_time"]
                cron_expr = sched["cron_expr"]
                
                if trigger_time_str:
                    trigger_time = datetime.fromisoformat(trigger_time_str)
                    if now >= trigger_time:
                        should_run = True
                elif cron_expr:
                    # check cron
                    last_run = sched["last_run_at"]
                    base_time = datetime.fromisoformat(last_run) if last_run else datetime.fromisoformat(sched["created_at"])
                    if base_time.tzinfo is None:
                        base_time = base_time.astimezone()
                    iter = croniter(cron_expr, base_time)
                    next_run = iter.get_next(datetime)
                    if next_run.tzinfo is None:
                        next_run = next_run.astimezone()
                    if now >= next_run:
                        should_run = True
                        
                if should_run:
                    # Create a new task
                    new_task = Task(goal=sched["goal"])
                    task_store.save_task(new_task)
                    print(f"\n[Scheduler] Triggered proactive task: {new_task.goal}")
                    
                    if cron_expr:
                        cursor.execute("UPDATE schedules SET last_run_at = ? WHERE id = ?", (now.isoformat(), sched["id"]))
                    else:
                        cursor.execute("UPDATE schedules SET status = 'COMPLETED', last_run_at = ? WHERE id = ?", (now.isoformat(), sched["id"]))
                    conn.commit()
        finally:
            conn.close()

scheduler = Scheduler()
