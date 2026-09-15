from app.memory.store import MemoryStore
from app.memory.models import Memory, MemoryType
from app.security.redaction import redact_text
from typing import List, Optional
import math
import os
from datetime import datetime

class MemoryManager:
    def __init__(self):
        self.store = MemoryStore()
        
    def add_explicit_memory(self, content: str, project: str = None) -> str:
        # Check security
        redacted = redact_text(content)
        if redacted != content:
            raise ValueError("Candidate memory contains sensitive information/secrets and was rejected.")
            
        # Importance scoring heuristic (simple version)
        words = [w.strip(".,!?") for w in content.lower().split()]
        trivial_words = {"hi", "hello", "thanks", "ok", "yes", "no", "ruox"}
        if len(words) <= 3 and all(w in trivial_words for w in words):
            return None # Discard trivial memory
            
        importance = 0.5
        if any(w in words for w in ["always", "never", "prefer", "hate", "love", "must"]):
            importance = 0.9
            
        min_importance = float(os.getenv("MEMORY_MIN_IMPORTANCE", "0.6"))
        
        # Deduplication / Strengthen
        existing = self.store.search_memories(content, limit=10)
        for mem in existing:
            # Semantic overlap check (simplified)
            if mem.content.strip().lower() == content.strip().lower():
                mem.access_count += 1
                mem.importance = min(1.0, mem.importance + 0.1)
                if project and not mem.project:
                    mem.project = project
                self.store.update_memory(mem)
                return mem.id
                
        # If importance is too low, we might not store it explicitly unless requested, 
        # but for add_explicit_memory we store it anyway if it was a direct tool call.
        mem_type = MemoryType.PROJECT if project else MemoryType.SEMANTIC
        
        mem = Memory(
            memory_type=mem_type,
            content=content,
            source="explicit",
            importance=importance,
            project=project
        )
        return self.store.add_memory(mem)

    def search_relevant_memories(self, context: str, project: str = None, limit: int = None) -> List[Memory]:
        """Simple keyword-based relevance matching without embeddings."""
        if limit is None:
            limit = int(os.getenv("MEMORY_MAX_CONTEXT", "5"))
            
        candidates = self.store.list_memories(limit=500)
        
        stop_words = {"is", "the", "of", "a", "an", "and", "or", "in", "to", "for", "with", "on", "at", "by", "what", "how", "why"}
        words = set([w.strip(".,!?") for w in context.lower().split()]) - stop_words
        
        scored = []
        now = datetime.utcnow()
        
        for mem in candidates:
            # Filter by project if strictly needed, or just boost project memories
            project_boost = 0.0
            if project and mem.project == project:
                project_boost = 1.0
            elif mem.project and mem.project != project:
                # If memory belongs to another project, drastically reduce its score
                project_boost = -2.0
                
            # Token overlap score
            mem_words = set([w.strip(".,!?") for w in mem.content.lower().split()]) - stop_words
            overlap = len(words.intersection(mem_words))
            relevance = overlap / max(1, len(mem_words))
            
            # Recency decay (halving every 7 days)
            days_old = (now - mem.updated_at).total_seconds() / (3600 * 24)
            recency = math.exp(-days_old / 7.0)
            
            # Final score
            score = (relevance * 2.0) + mem.importance + (recency * 0.5) + project_boost
            
            if score > 0.5 and relevance > 0: # Threshold requires at least some textual relevance
                scored.append((score, mem))
                
        scored.sort(key=lambda x: x[0], reverse=True)
        top_mems = [mem for score, mem in scored[:limit]]
        
        # Touch retrieved memories
        for m in top_mems:
            self.store.touch_memory(m.id)
            
        return top_mems

memory_manager = MemoryManager()
