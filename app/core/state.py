import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PlanStep(BaseModel):
    step_id: int
    description: str
    status: str = "PENDING" # PENDING, RUNNING, WAITING_APPROVAL, COMPLETED, FAILED, SKIPPED, CANCELLED
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    error: Optional[str] = None
    requires_confirmation: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class Plan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    steps: List[PlanStep] = []
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class TaskStep(BaseModel):
    id: int
    action: str
    status: str = "pending" # pending, running, done, failed
    observation: Optional[str] = None

class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    status: str = "PLANNING" # PLANNING, RUNNING, WAITING_APPROVAL, FAILED, DONE
    plan: Optional[Plan] = None
    steps: List[TaskStep] = []
    messages: List[Dict[str, str]] = []  # Added for conversation context
    risk_level: str = "LOW"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
