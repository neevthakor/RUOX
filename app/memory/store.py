import json
from typing import List, Optional
from datetime import datetime
from app.memory.database import db_manager
from app.memory.models import Memory

class MemoryStore:
    def __init__(self, db_manager=db_manager):
        self.db_manager = db_manager

    def add_memory(self, memory: Memory) -> str:
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memories (
                    id, memory_type, content, source, importance,
                    created_at, updated_at, last_accessed_at, access_count,
                    project, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory.id, memory.memory_type, memory.content, memory.source,
                memory.importance, memory.created_at.isoformat(), memory.updated_at.isoformat(),
                memory.last_accessed_at.isoformat(), memory.access_count,
                memory.project, json.dumps(memory.metadata)
            ))
            conn.commit()
            return memory.id
        finally:
            conn.close()

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM memories WHERE id = ?', (memory_id,))
            row = cursor.fetchone()
            if row:
                return Memory.from_row(dict(row))
            return None
        finally:
            conn.close()

    def update_memory(self, memory: Memory):
        conn = self.db_manager.get_connection()
        try:
            memory.updated_at = datetime.utcnow()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE memories SET
                    memory_type = ?, content = ?, source = ?, importance = ?,
                    updated_at = ?, last_accessed_at = ?, access_count = ?,
                    project = ?, metadata = ?
                WHERE id = ?
            ''', (
                memory.memory_type, memory.content, memory.source, memory.importance,
                memory.updated_at.isoformat(), memory.last_accessed_at.isoformat(), memory.access_count,
                memory.project, json.dumps(memory.metadata), memory.id
            ))
            conn.commit()
        finally:
            conn.close()

    def touch_memory(self, memory_id: str):
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE memories 
                SET access_count = access_count + 1, last_accessed_at = ?
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), memory_id))
            conn.commit()
        finally:
            conn.close()

    def delete_memory(self, memory_id: str):
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
            conn.commit()
        finally:
            conn.close()

    def clear_all(self):
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM memories')
            conn.commit()
        finally:
            conn.close()

    def list_memories(self, limit: int = 100, project: str = None) -> List[Memory]:
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            if project:
                cursor.execute('SELECT * FROM memories WHERE project = ? ORDER BY updated_at DESC LIMIT ?', (project, limit))
            else:
                cursor.execute('SELECT * FROM memories ORDER BY updated_at DESC LIMIT ?', (limit,))
            return [Memory.from_row(dict(row)) for row in cursor.fetchall()]
        finally:
            conn.close()
            
    def search_memories(self, query: str, limit: int = 10) -> List[Memory]:
        # Simple SQL LIKE search
        conn = self.db_manager.get_connection()
        try:
            cursor = conn.cursor()
            like_query = f"%{query}%"
            cursor.execute('SELECT * FROM memories WHERE content LIKE ? ORDER BY importance DESC, updated_at DESC LIMIT ?', (like_query, limit))
            return [Memory.from_row(dict(row)) for row in cursor.fetchall()]
        finally:
            conn.close()
