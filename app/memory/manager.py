from app.memory.store import MemoryStore
from app.memory.models import Memory, MemoryType
from app.security.redaction import redact_text
from typing import List, Optional
import math
from datetime import datetime

class MemoryManager:
    def __init__(self):
        self.store = MemoryStore()
        
    def add_explicit_memory(self, content: str, project: str = None) -> str:
        # Check security
        redacted = redact_text(content)
        if redacted != content:
            raise ValueError("Candidate memory contains sensitive information/secrets and was rejected.")
            
        # Deduplication
        existing = self.store.search_memories(content, limit=5)
        for mem in existing:
            if mem.content.strip().lower() == content.strip().lower():
                mem.access_count += 1
                mem.importance = min(1.0, mem.importance + 0.1)
                self.store.update_memory(mem)
                return mem.id
                
        mem = Memory(
            memory_type=MemoryType.SEMANTIC,
            content=content,
            source="explicit",
            importance=0.9,
            project=project
        )
        return self.store.add_memory(mem)

    def search_relevant_memories(self, context: str, limit: int = 5) -> List[Memory]:
        """Simple keyword-based relevance matching without embeddings."""
        # Get recent or important memories
        # To avoid over-engineering, we fetch all memories and score them if the db is small.
        # For P3 lightweight sqlite, fetching 100 recent/important memories and ranking is fine.
        candidates = self.store.list_memories(limit=200)
        
        words = set(context.lower().split())
        scored = []
        now = datetime.utcnow()
        
        for mem in candidates:
            # Token overlap score
            mem_words = set(mem.content.lower().split())
            overlap = len(words.intersection(mem_words))
            relevance = overlap / max(1, len(mem_words))
            
            # Recency decay (1.0 for now, halving every 7 days)
            days_old = (now - mem.updated_at).total_seconds() / (3600 * 24)
            recency = math.exp(-days_old / 7.0)
            
            # Final score
            score = (relevance * 2.0) + mem.importance + (recency * 0.5)
            
            if score > 0.5 and relevance > 0: # Threshold requires at least some textual relevance
                scored.append((score, mem))
                
        scored.sort(key=lambda x: x[0], reverse=True)
        top_mems = [mem for score, mem in scored[:limit]]
        
        # Touch retrieved memories
        for m in top_mems:
            self.store.touch_memory(m.id)
            
        return top_mems

memory_manager = MemoryManager()
