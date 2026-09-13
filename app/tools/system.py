from app.tools.base import Tool
from app.security.permissions import PermissionLevel

# Old ShellCommandTool removed, replaced by app.tools.computer.shell.RunCommandTool
class SystemTimeTool(Tool):
    name = "get_current_time"
    description = "Returns the current local date, time, and timezone of the system."
    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    permission_level = PermissionLevel.READ
    requires_confirmation = False

    def _run(self, input_data: dict):
        import datetime
        now = datetime.datetime.now().astimezone()
        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": str(now.tzinfo),
            "iso8601": now.isoformat()
        }

class SystemInfoTool(Tool):
    name = "get_system_info"
    description = "Returns information about the current operating system, Python version, and basic hardware info."
    input_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    permission_level = PermissionLevel.READ
    requires_confirmation = False

    def _run(self, input_data: dict):
        import platform
        import sys
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python_version": sys.version,
            "architecture": platform.architecture()[0]
        }
