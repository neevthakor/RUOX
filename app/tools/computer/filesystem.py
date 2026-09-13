import os
import subprocess
from datetime import datetime
from pathlib import Path
from app.tools.base import Tool
from app.security.permissions import PermissionLevel
from app.security.redaction import redact_text

from app.core.config import get_project_root

def _resolve_path(path_str: str) -> Path:
    ruox_root = get_project_root()
        
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = ruox_root / p
    
    # Resolve to absolute and remove symlinks for safety
    try:
        p = p.resolve()
    except Exception:
        pass
    
    return p

class ListDirectoryTool(Tool):
    name = "list_directory"
    description = "Lists files and folders in a given directory."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to list."}
        },
        "required": ["path"]
    }
    permission_level = PermissionLevel.READ
    requires_confirmation = False

    def _run(self, input_data: dict):
        path = _resolve_path(input_data["path"])
        if not path.exists() or not path.is_dir():
            return {"error": f"Path '{path}' is not a valid directory."}
            
        items = []
        try:
            for item in path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
            # Sort dirs first, then files
            items.sort(key=lambda x: (x["type"] == "file", x["name"].lower()))
            return {"directory": str(path), "items": items}
        except Exception as e:
            return {"error": str(e)}

class GetFileInfoTool(Tool):
    name = "get_file_info"
    description = "Gets metadata for a specific file."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file."}
        },
        "required": ["path"]
    }
    permission_level = PermissionLevel.READ
    requires_confirmation = False

    def _run(self, input_data: dict):
        path = _resolve_path(input_data["path"])
        if not path.exists():
            return {"error": f"File '{path}' does not exist."}
            
        try:
            stat = path.stat()
            return {
                "path": str(path),
                "is_file": path.is_file(),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

class CreateDirectoryTool(Tool):
    name = "create_directory"
    description = "Creates a new directory."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the new directory."}
        },
        "required": ["path"]
    }
    permission_level = PermissionLevel.MEDIUM_RISK
    requires_confirmation = True

    def _run(self, input_data: dict):
        path = _resolve_path(input_data["path"])
        try:
            path.mkdir(parents=True, exist_ok=True)
            return {"status": f"Directory '{path}' created successfully."}
        except Exception as e:
            return {"error": f"Failed to create directory: {str(e)}"}

class OpenPathTool(Tool):
    name = "open_path"
    description = "Opens a file or folder in the default Windows application."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to open."}
        },
        "required": ["path"]
    }
    permission_level = PermissionLevel.LOW_RISK
    requires_confirmation = False

    def _run(self, input_data: dict):
        path = _resolve_path(input_data["path"])
        if not path.exists():
            return {"error": f"Path '{path}' does not exist."}
            
        try:
            os.startfile(str(path))
            return {"status": f"Successfully opened {path}"}
        except Exception as e:
            return {"error": f"Failed to open path: {str(e)}"}
