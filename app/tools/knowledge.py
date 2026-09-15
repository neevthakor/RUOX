import json
from app.tools.base import Tool, ToolResult
from app.knowledge.store import knowledge_store
from typing import Dict, Any

class RememberKnowledgeTool(Tool):
    name = "remember_knowledge"
    description = "Store a structured fact, entity, or preference in the Personal Knowledge System."
    requires_confirmation = False

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        entity_type = kwargs.get("type", "FACT")
        name = kwargs.get("name")
        properties = kwargs.get("properties", {})
        
        if not name:
            return ToolResult(success=False, error="Entity name required")
            
        ent_id = knowledge_store.store_entity(entity_type, name, properties)
        return ToolResult(success=True, output=f"Stored knowledge entity {name} (ID: {ent_id})")

class SearchKnowledgeTool(Tool):
    name = "search_knowledge"
    description = "Search the Personal Knowledge System for entities, projects, or facts."
    requires_confirmation = False

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        query = kwargs.get("query")
        if not query:
            return ToolResult(success=False, error="Query required")
            
        results = knowledge_store.search(query)
        if not results:
            return ToolResult(success=True, output="No knowledge found.")
            
        out = "Found knowledge:\n"
        for r in results:
            out += f"- [{r['type']}] {r['name']}: {r['properties']}\n"
        return ToolResult(success=True, output=out)
