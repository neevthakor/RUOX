from typing import Dict, Type
from app.tools.base import Tool

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool_instance: Tool):
        self._tools[tool_instance.name] = tool_instance

    def get_tool(self, name: str) -> Tool:
        return self._tools.get(name)

    def get_all_schemas(self):
        schemas = []
        for name, tool in self._tools.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.input_schema
                }
            })
        return schemas

    def get_schemas_for_context(self, prompt: str):
        prompt = prompt.lower()
        active_groups = set()
        
        # SYSTEM
        if any(w in prompt for w in ["time", "date", "os ", "system", "operating system", "who are you", "version"]):
            active_groups.add("SYSTEM")
            
        # MEMORY/KNOWLEDGE (P16)
        if any(w in prompt for w in ["remember", "forget", "recall", "favorite", "my name", "told you", "earlier", "memory", "project", "knowledge"]):
            active_groups.add("MEMORY")
            
        # TASK/AUTONOMOUS (P14)
        if any(w in prompt for w in ["task", "resume", "continue", "recent", "what was i doing", "status", "background"]):
            active_groups.add("TASK")
            
        # PROACTIVE (P15)
        if any(w in prompt for w in ["remind", "schedule", "every"]):
            active_groups.add("PROACTIVE")
            
        # COMPUTER
        if any(w in prompt for w in ["open", "run", "list", "directory", "folder", "file", "create", "path", "command", "calculator", "app", "mouse", "click", "scroll", "keyboard", "type", "press", "window", "focus", "close"]):
            active_groups.add("COMPUTER")
            
        # VISION
        if any(w in prompt for w in ["screen", "see", "display", "monitor", "showing", "look"]):
            active_groups.add("VISION")
            
        # WEB/BROWSER (P13)
        if any(w in prompt for w in ["search", "web", "internet", "news", "google", "duckduckgo", "fetch", "research", "browser", "chrome", "website", "read"]):
            active_groups.add("WEB")
            
        group_mapping = {
            "get_current_time": "SYSTEM",
            "get_system_info": "SYSTEM",
            
            "remember_information": "MEMORY",
            "search_memory": "MEMORY",
            "list_memories": "MEMORY",
            "forget_memory": "MEMORY",
            "remember_knowledge": "MEMORY",
            "search_knowledge": "MEMORY",
            
            "get_recent_tasks": "TASK",
            "schedule_task": "PROACTIVE",
            "cancel_schedule": "PROACTIVE",
            
            "open_application": "COMPUTER",
            "list_directory": "COMPUTER",
            "get_file_info": "COMPUTER",
            "create_directory": "COMPUTER",
            "open_path": "COMPUTER",
            "run_command": "COMPUTER",
            "mouse_position": "COMPUTER",
            "mouse_move": "COMPUTER",
            "mouse_click": "COMPUTER",
            "mouse_scroll": "COMPUTER",
            "keyboard_type": "COMPUTER",
            "keyboard_hotkey": "COMPUTER",
            "window_list": "COMPUTER",
            "window_focus": "COMPUTER",
            "window_close": "COMPUTER",
            
            "screen_context": "VISION",
            "analyze_screen": "VISION",
            "capture_screen": "VISION",
            
            "web_search": "WEB",
            "web_fetch": "WEB",
            "web_research": "WEB",
            "browser_open": "WEB",
            "browser_observe": "WEB",
            "browser_click": "WEB",
            "browser_type": "WEB",
            "browser_extract": "WEB",
        }
        
        schemas = []
        for name, tool in self._tools.items():
            group = group_mapping.get(name)
            if group in active_groups:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool.description,
                        "parameters": tool.input_schema
                    }
                })
        return schemas

tool_registry = ToolRegistry()
