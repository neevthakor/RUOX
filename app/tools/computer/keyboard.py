import pyautogui
from typing import Dict, Any
from app.tools.base import Tool, ToolResult
from app.security.permissions import PermissionLevel

class KeyboardTypeTool(Tool):
    name = "keyboard_type"
    description = "Type a string of characters using the keyboard."
    parameters_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type. Max 500 chars."},
            "interval": {"type": "number", "default": 0.05, "description": "Seconds between keys."}
        },
        "required": ["text"]
    }
    permission_level = PermissionLevel.MEDIUM_RISK

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        if not user_confirmed and self.permission_level >= PermissionLevel.MEDIUM_RISK:
            return ToolResult(success=False, error="AWAITING_CONFIRMATION")
            
        try:
            text = str(params["text"])
            if len(text) > 500:
                text = text[:500]
                
            interval = float(params.get("interval", 0.05))
            pyautogui.write(text, interval=interval)
            return ToolResult(success=True, output=f"Typed {len(text)} characters.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class KeyboardHotkeyTool(Tool):
    name = "keyboard_hotkey"
    description = "Press a sequence of keys simultaneously (e.g. 'ctrl', 'c' or 'enter')."
    parameters_schema = {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of keys to press together."
            }
        },
        "required": ["keys"]
    }
    permission_level = PermissionLevel.MEDIUM_RISK

    def execute(self, params: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        keys = params.get("keys", [])
        
        # Safe keys don't strictly require confirmation if it's just 'down' or 'tab', but we default to MEDIUM
        # and explicitly require confirmation for potentially destructive/high-risk combos.
        high_risk_keys = ["enter", "delete", "backspace", "tab", "esc", "win", "command"]
        is_high_risk = any(k.lower() in high_risk_keys for k in keys)
        
        # But per the plan, all keyboard events are MEDIUM risk unless we allow specific exceptions.
        # We will require confirmation for all hotkeys for safety, or let user check.
        if not user_confirmed:
            return ToolResult(success=False, error="AWAITING_CONFIRMATION")
            
        try:
            pyautogui.hotkey(*keys)
            return ToolResult(success=True, output=f"Pressed hotkey: {'+'.join(keys)}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
