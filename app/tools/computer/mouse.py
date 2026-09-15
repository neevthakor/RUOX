import pyautogui
from typing import Dict, Any
from app.tools.base import Tool, ToolResult
from app.security.permissions import PermissionLevel
import json

class MousePositionTool(Tool):
    name = "mouse_position"
    description = "Get the current mouse pointer coordinates on the screen."
    parameters_schema = {}
    permission_level = PermissionLevel.READ

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        try:
            x, y = pyautogui.position()
            return ToolResult(success=True, output=json.dumps({"x": x, "y": y}))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class MouseMoveTool(Tool):
    name = "mouse_move"
    description = "Move the mouse to absolute screen coordinates."
    parameters_schema = {
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "duration": {"type": "number", "default": 0.5}
        },
        "required": ["x", "y"]
    }
    permission_level = PermissionLevel.LOW_RISK

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        try:
            x = int(params["x"])
            y = int(params["y"])
            duration = float(params.get("duration", 0.5))
            
            # Simple bounds check
            screen_width, screen_height = pyautogui.size()
            x = max(0, min(x, screen_width))
            y = max(0, min(y, screen_height))
            
            pyautogui.moveTo(x, y, duration=duration)
            return ToolResult(success=True, output=f"Moved mouse to ({x}, {y})")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class MouseClickTool(Tool):
    name = "mouse_click"
    description = "Click the mouse at the current location or given coordinates."
    parameters_schema = {
        "type": "object",
        "properties": {
            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
            "clicks": {"type": "integer", "default": 1},
            "x": {"type": "integer"},
            "y": {"type": "integer"}
        }
    }
    permission_level = PermissionLevel.MEDIUM_RISK

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        if not user_confirmed and self.permission_level >= PermissionLevel.MEDIUM_RISK:
            return ToolResult(success=False, error="AWAITING_CONFIRMATION")
            
        try:
            button = params.get("button", "left")
            clicks = int(params.get("clicks", 1))
            x = params.get("x")
            y = params.get("y")
            
            if x is not None and y is not None:
                screen_width, screen_height = pyautogui.size()
                x = max(0, min(int(x), screen_width))
                y = max(0, min(int(y), screen_height))
                pyautogui.click(x=x, y=y, clicks=clicks, button=button)
                return ToolResult(success=True, output=f"Clicked {button} button {clicks} times at ({x}, {y})")
            else:
                pyautogui.click(clicks=clicks, button=button)
                return ToolResult(success=True, output=f"Clicked {button} button {clicks} times at current position")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class MouseScrollTool(Tool):
    name = "mouse_scroll"
    description = "Scroll the mouse wheel. Positive amount scrolls up, negative down."
    parameters_schema = {
        "type": "object",
        "properties": {
            "clicks": {"type": "integer", "description": "Amount to scroll"}
        },
        "required": ["clicks"]
    }
    permission_level = PermissionLevel.LOW_RISK

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        try:
            clicks = int(params["clicks"])
            pyautogui.scroll(clicks)
            return ToolResult(success=True, output=f"Scrolled {clicks} clicks")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
