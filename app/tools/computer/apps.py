import os
import subprocess
from app.tools.base import Tool
from app.security.permissions import PermissionLevel

# Map of common applications to their standard Windows execution commands
# We rely on Windows PATH or 'start' shell builtin where appropriate.
COMMON_APPS = {
    "chrome": "start chrome",
    "edge": "start msedge",
    "firefox": "start firefox",
    "vscode": "code",
    "code": "code",
    "notepad": "notepad",
    "calculator": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "terminal": "wt",
    "powershell": "powershell",
    "settings": "start ms-settings:"
}

class OpenApplicationTool(Tool):
    name = "open_application"
    description = "Opens a common desktop application (e.g., chrome, vscode, notepad)."
    input_schema = {
        "type": "object",
        "properties": {
            "application": {
                "type": "string", 
                "description": "The name of the application to open."
            }
        },
        "required": ["application"]
    }
    permission_level = PermissionLevel.LOW_RISK # SAFE conceptually, but let's map to LOW_RISK
    requires_confirmation = False

    def _run(self, input_data: dict):
        app_name = input_data.get("application", "").lower()
        
        # Check against common apps
        cmd = COMMON_APPS.get(app_name)
        
        if not cmd:
            # Fallback for executables if it looks like a simple name (no path traversal)
            if " " not in app_name and "/" not in app_name and "\\" not in app_name:
                cmd = f"start {app_name}"
            else:
                return {"error": f"Application '{app_name}' not recognized or unsafe."}

        try:
            # Use shell=True since we are using 'start'
            subprocess.Popen(cmd, shell=True)
            return {"status": f"Successfully requested launch of {app_name}."}
        except Exception as e:
            return {"error": f"Failed to launch {app_name}: {str(e)}"}
