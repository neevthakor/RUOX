from app.tools.base import Tool, ToolResult
from app.security.permissions import PermissionLevel
from app.memory.manager import memory_manager
from app.memory.task_store import task_store

class RememberInformationTool(Tool):
    name = "remember_information"
    description = "Saves important facts, preferences, or project details to long-term memory."
    input_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The explicit fact to remember."}
        },
        "required": ["content"]
    }
    permission_level = PermissionLevel.LOW_RISK
    
    def _run(self, input_data: dict):
        try:
            mem_id = memory_manager.add_explicit_memory(input_data["content"])
            return f"Information remembered successfully. (ID: {mem_id})"
        except Exception as e:
            return f"Failed to remember: {str(e)}"

class SearchMemoryTool(Tool):
    name = "search_memory"
    description = "Searches long-term memory for past facts or context."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keywords to search for."}
        },
        "required": ["query"]
    }
    permission_level = PermissionLevel.READ
    
    def _run(self, input_data: dict):
        mems = memory_manager.store.search_memories(input_data["query"])
        if not mems:
            return "No matching memories found."
        
        res = []
        for m in mems:
            res.append(f"- {m.content}")
        return "\n".join(res)

class ListMemoriesTool(Tool):
    name = "list_memories"
    description = "Lists all stored memories."
    input_schema = {
        "type": "object",
        "properties": {}
    }
    permission_level = PermissionLevel.READ
    
    def _run(self, input_data: dict):
        mems = memory_manager.store.list_memories(limit=50)
        if not mems:
            return "No memories stored."
        
        res = []
        for m in mems:
            res.append(f"[{m.id}] {m.content}")
        return "\n".join(res)

class ForgetMemoryTool(Tool):
    name = "forget_memory"
    description = "Deletes a specific memory by its ID, or clears all memories."
    input_schema = {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string", "description": "ID of memory to delete. Pass 'ALL' to delete everything."}
        },
        "required": ["memory_id"]
    }
    permission_level = PermissionLevel.HIGH_RISK
    requires_confirmation = True
    
    def _run(self, input_data: dict):
        mem_id = input_data.get("memory_id")
        if mem_id == "ALL":
            memory_manager.store.clear_all()
            return "All memories have been deleted."
        
        memory_manager.store.delete_memory(mem_id)
        return f"Memory {mem_id} deleted."

class GetRecentTasksTool(Tool):
    name = "get_recent_tasks"
    description = "Retrieves history of recent tasks executed by RUOX."
    input_schema = {
        "type": "object",
        "properties": {}
    }
    permission_level = PermissionLevel.READ
    
    def _run(self, input_data: dict):
        tasks = task_store.get_recent_tasks(limit=5)
        if not tasks:
            return "No recent tasks."
            
        res = []
        for t in tasks:
            res.append(f"Task: {t['goal']} | Status: {t['status']}")
        return "\n".join(res)
