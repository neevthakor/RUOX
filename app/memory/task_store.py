import json
from typing import List, Optional
from datetime import datetime
from app.memory.database import db_manager
from app.core.state import Task, TaskStep

class TaskStore:
    def __init__(self, db_manager=db_manager):
        self.db_manager = db_manager

    def save_task(self, task: Task):
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute('SELECT id FROM tasks WHERE id = ?', (task.task_id,))
            exists = cursor.fetchone()
            
            steps_json = json.dumps([s.model_dump() for s in task.steps], default=str)
            
            # Since the db schema has current_step and result, we infer them
            current_step = next((s.action for s in task.steps if s.status in ("pending", "running")), "")
            result = ""
            if task.status == "DONE":
                result = "Task completed successfully."
                
            # If plan exists, merge it into metadata
            metadata = {}
            if task.plan:
                # We redact args if we want to be safe, but redaction happens at generation time.
                metadata["plan"] = task.plan.model_dump()
                
            metadata_json = json.dumps(metadata, default=str)
            
            if exists:
                cursor.execute('''
                    UPDATE tasks SET
                        status = ?, updated_at = ?, current_step = ?, steps = ?, result = ?, metadata = ?
                    WHERE id = ?
                ''', (
                    task.status, datetime.now().astimezone().isoformat(), current_step, steps_json, result, metadata_json, task.task_id
                ))
            else:
                cursor.execute('''
                    INSERT INTO tasks (
                        id, goal, status, created_at, updated_at, steps, current_step, result, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.task_id, task.goal, task.status, 
                    task.created_at.isoformat(), datetime.now().astimezone().isoformat(),
                    steps_json, current_step, result, metadata_json
                ))
            conn.commit()
        finally:
            conn.close()

    def get_recent_tasks(self, limit: int = 5) -> List[dict]:
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

task_store = TaskStore()
