from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import json

class MemoryType:
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROJECT = "PROJECT"

class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: str
    content: str
    source: Optional[str] = "automatic" # 'explicit' or 'automatic'
    importance: float = 0.5
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    project: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def from_row(cls, row: dict) -> 'Memory':
        return cls(
            id=row["id"],
            memory_type=row["memory_type"],
            content=row["content"],
            source=row["source"],
            importance=row["importance"],
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if isinstance(row["updated_at"], str) else row["updated_at"],
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"]) if isinstance(row["last_accessed_at"], str) else row["last_accessed_at"],
            access_count=row["access_count"],
            project=row["project"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
