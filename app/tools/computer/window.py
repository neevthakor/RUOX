import ctypes
from ctypes import wintypes
from typing import Dict, Any
from app.tools.base import Tool, ToolResult
from app.security.permissions import PermissionLevel
import json

# Windows API constants and types
user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

class WindowInfo:
    def __init__(self, hwnd, title):
        self.hwnd = hwnd
        self.title = title

def _get_window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value
    return ""

def _enum_windows():
    windows = []
    def callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            title = _get_window_title(hwnd)
            if title:
                windows.append(WindowInfo(hwnd, title))
        return True
    
    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return windows

class WindowListTool(Tool):
    name = "window_list"
    description = "List all visible windows and their titles."
    parameters_schema = {}
    permission_level = PermissionLevel.READ

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        try:
            windows = _enum_windows()
            output = [{"hwnd": w.hwnd, "title": w.title} for w in windows]
            return ToolResult(success=True, output=json.dumps(output))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class WindowFocusTool(Tool):
    name = "window_focus"
    description = "Focus/bring to front a window by its partial title or hwnd."
    parameters_schema = {
        "type": "object",
        "properties": {
            "title_contains": {"type": "string", "description": "Substring of window title to match."}
        },
        "required": ["title_contains"]
    }
    permission_level = PermissionLevel.LOW_RISK

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        try:
            title_contains = params["title_contains"].lower()
            windows = _enum_windows()
            
            for w in windows:
                if title_contains in w.title.lower():
                    # SW_RESTORE = 9
                    user32.ShowWindow(w.hwnd, 9)
                    user32.SetForegroundWindow(w.hwnd)
                    return ToolResult(success=True, output=f"Focused window: {w.title}")
                    
            return ToolResult(success=False, error="Window not found.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class WindowCloseTool(Tool):
    name = "window_close"
    description = "Close a window by its partial title."
    parameters_schema = {
        "type": "object",
        "properties": {
            "title_contains": {"type": "string"}
        },
        "required": ["title_contains"]
    }
    permission_level = PermissionLevel.MEDIUM_RISK

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        if not user_confirmed and self.permission_level >= PermissionLevel.MEDIUM_RISK:
            return ToolResult(success=False, error="AWAITING_CONFIRMATION")
            
        try:
            title_contains = params["title_contains"].lower()
            windows = _enum_windows()
            
            for w in windows:
                if title_contains in w.title.lower():
                    # WM_CLOSE = 0x0010
                    user32.PostMessageW(w.hwnd, 0x0010, 0, 0)
                    return ToolResult(success=True, output=f"Sent close signal to window: {w.title}")
                    
            return ToolResult(success=False, error="Window not found.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
