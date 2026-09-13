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

tool_registry = ToolRegistry()
