import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class TaskStep(BaseModel):
    id: int
    action: str
    status: str = "pending" # pending, running, done, failed
    observation: Optional[str] = None

class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    status: str = "PLANNING" # PLANNING, RUNNING, WAITING_APPROVAL, FAILED, DONE
    steps: List[TaskStep] = []
    messages: List[Dict[str, str]] = []  # Added for conversation context
    risk_level: str = "LOW"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
