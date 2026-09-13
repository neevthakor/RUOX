from pydantic import BaseModel, Field
from typing import Any, Optional, Dict
from app.security.permissions import PermissionLevel, global_security_state

class ToolResult(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)

class Tool:
    name: str = "BaseTool"
    description: str = "Base description"
    input_schema: dict = {}
    permission_level: PermissionLevel = PermissionLevel.READ
    timeout_seconds: int = 30
    requires_confirmation: bool = False

    def validate(self, input_data: dict) -> bool:
        # In a real implementation, use jsonschema or pydantic
        return True

    def execute(self, input_data: dict, user_confirmed: bool = False) -> ToolResult:
        # 1. Emergency stop check
        if not global_security_state.computer_control_enabled and self.permission_level > PermissionLevel.READ:
            return ToolResult(success=False, error="COMPUTER_CONTROL_DISABLED")
        
        # 2. Permission check
        if self.permission_level >= PermissionLevel.MEDIUM_RISK or self.requires_confirmation:
            if not user_confirmed:
                return ToolResult(success=False, error="AWAITING_CONFIRMATION")
                
        # 3. Execution
        try:
            result = self._run(input_data)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _run(self, input_data: dict) -> Any:
        raise NotImplementedError
