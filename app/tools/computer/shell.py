import subprocess
import shlex
import re
from app.tools.base import Tool
from app.security.permissions import PermissionLevel
from app.security.redaction import redact_text

# Regex patterns for fast blocking
BLOCKED_PATTERNS = [
    r'(?i)\b(shutdown|restart|format|diskpart|taskkill)\b',
    r'(?i)(del|rmdir|rm)\s+(/s|-r)',  # Recursive deletes
    r'(?i)reg\s+(add|delete)', # Registry mods
    r'(?i)netsh\s+advfirewall', # Firewall mods
]

SAFE_COMMANDS = [
    "python --version", "git status", "git log", "git diff", "dir", "echo",
    "where python", "pytest", "npm --version", "node --version"
]

def classify_command(cmd: str) -> tuple[str, str]:
    """Returns (Classification, Reason)
    Classification: 'SAFE', 'BLOCKED', 'CONFIRMATION_REQUIRED'
    """
    cmd_lower = cmd.lower().strip()
    
    # 1. Blocked checks
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_lower):
            return "BLOCKED", f"Matches blocked pattern: {pattern}"
            
    # 2. Safe checks
    if any(cmd_lower.startswith(safe_cmd) for safe_cmd in SAFE_COMMANDS):
        return "SAFE", "Matches safe command list."
        
    # Special cases for purely read-only commands not strictly matching above
    if cmd_lower.startswith("python -m unittest"):
        return "SAFE", "Running tests."
        
    return "CONFIRMATION_REQUIRED", "Command may modify state."


class RunCommandTool(Tool):
    name = "run_command"
    description = "Executes a shell command. Use for tests, git, or scripts."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The command to run."},
            "working_directory": {"type": "string", "description": "Optional working directory."}
        },
        "required": ["command"]
    }
    
    # We will dynamically adjust these in validate/execute, but base defaults:
    permission_level = PermissionLevel.HIGH_RISK
    requires_confirmation = True

    def execute(self, input_data: dict, user_confirmed: bool = False):
        # Override execute to perform classification FIRST
        cmd = input_data.get("command", "")
        classification, reason = classify_command(cmd)
        
        if classification == "BLOCKED":
            return type(self).result_class(success=False, error=f"Command BLOCKED by security policy: {reason}")
            
        if classification == "CONFIRMATION_REQUIRED" and not user_confirmed:
            # We want to tell the agent it needs confirmation
            return type(self).result_class(success=False, error="AWAITING_CONFIRMATION")
            
        # If SAFE, or CONFIRMATION_REQUIRED + user_confirmed, proceed
        return super().execute(input_data, user_confirmed=True)

    def _run(self, input_data: dict):
        command = input_data["command"]
        cwd = input_data.get("working_directory")
        
        if cwd:
            from app.tools.computer.filesystem import _resolve_path
            cwd = str(_resolve_path(cwd))
        else:
            from app.core.config import get_project_root
            cwd = str(get_project_root())
            
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )
            
            # Truncate and redact outputs
            def process_output(text: str):
                if not text: return ""
                if len(text) > 4000:
                    text = text[:4000] + "\n...[TRUNCATED]"
                return redact_text(text)

            return {
                "exit_code": result.returncode,
                "stdout": process_output(result.stdout),
                "stderr": process_output(result.stderr),
                "timed_out": False
            }
            
        except subprocess.TimeoutExpired as e:
            return {
                "exit_code": -1,
                "stdout": redact_text(e.stdout.decode()[:4000] if e.stdout else ""),
                "stderr": redact_text(e.stderr.decode()[:4000] if e.stderr else ""),
                "timed_out": True
            }
        except Exception as e:
            return {"error": str(e)}

# Inject result_class hack to use ToolResult easily
from app.tools.base import ToolResult
RunCommandTool.result_class = ToolResult
