import json
import uuid
from datetime import datetime
from app.memory.database import db_manager

class KnowledgeStore:
    def __init__(self, db=db_manager):
        self.db = db

    def store_entity(self, entity_type: str, name: str, properties: dict) -> str:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute("SELECT id, properties FROM entities WHERE type=? AND name=?", (entity_type, name))
            row = cursor.fetchone()
            
            if row:
                entity_id = row["id"]
                existing_props = json.loads(row["properties"] or "{}")
                existing_props.update(properties)
                cursor.execute(
                    "UPDATE entities SET properties=?, updated_at=? WHERE id=?", 
                    (json.dumps(existing_props), datetime.now().astimezone().isoformat(), entity_id)
                )
            else:
                entity_id = "ent-" + str(uuid.uuid4())[:8]
                cursor.execute(
                    "INSERT INTO entities (id, type, name, properties) VALUES (?, ?, ?, ?)",
                    (entity_id, entity_type, name, json.dumps(properties))
                )
            conn.commit()
            return entity_id
        finally:
            conn.close()

    def store_relationship(self, source_id: str, target_id: str, relation_type: str, properties: dict = None) -> str:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM relationships WHERE source_id=? AND target_id=? AND relation_type=?",
                (source_id, target_id, relation_type)
            )
            row = cursor.fetchone()
            if row:
                rel_id = row["id"]
                cursor.execute(
                    "UPDATE relationships SET properties=? WHERE id=?", 
                    (json.dumps(properties or {}), rel_id)
                )
            else:
                rel_id = "rel-" + str(uuid.uuid4())[:8]
                cursor.execute(
                    "INSERT INTO relationships (id, source_id, target_id, relation_type, properties) VALUES (?, ?, ?, ?, ?)",
                    (rel_id, source_id, target_id, relation_type, json.dumps(properties or {}))
                )
            conn.commit()
            return rel_id
        finally:
            conn.close()

    def search(self, query: str) -> list:
        # Simple search across entities and relationships
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            term = f"%{query}%"
            cursor.execute("SELECT * FROM entities WHERE name LIKE ? OR properties LIKE ? LIMIT 10", (term, term))
            entities = [dict(r) for r in cursor.fetchall()]
            return entities
        finally:
            conn.close()

knowledge_store = KnowledgeStore()
