import sqlite3
import os
from pathlib import Path
from app.core.config import get_project_root

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use data/memory.db from project root
            root = get_project_root()
            data_dir = root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "memory.db")
        else:
            self.db_path = db_path
            
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_db(self):
        """Idempotent initialization of tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Memory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                project TEXT,
                metadata TEXT
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                current_step TEXT,
                steps TEXT,
                result TEXT,
                error TEXT,
                metadata TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
        
        conn.commit()
        conn.close()

# Singleton instance
db_manager = DatabaseManager()
