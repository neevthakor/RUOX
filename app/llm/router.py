import os
from app.security.permissions import PrivacyClass, global_security_state
from app.llm.base import LLMProvider

class LLMRouter:
    def __init__(self, local_provider: LLMProvider, cloud_provider: LLMProvider = None, fast_provider: LLMProvider = None, strong_provider: LLMProvider = None):
        self.local = local_provider
        self.cloud = cloud_provider
        self.fast = fast_provider or local_provider
        self.strong = strong_provider or local_provider

    def get_provider(self, privacy_class: PrivacyClass, complexity: str, requires_vision: bool = False) -> LLMProvider:
        # Determine base local provider based on complexity intent
        if complexity in ["DIRECT_SIMPLE", "TOOL_SIMPLE"]:
            selected_local = self.fast if self.fast.is_available() else self.local
        elif complexity in ["PLAN", "DIRECT_COMPLEX", "TOOL_COMPLEX", "BROWSER", "AUTONOMOUS_TASK", "PROACTIVE", "KNOWLEDGE"]:
            selected_local = self.strong if self.strong.is_available() else self.local
        else:
            selected_local = self.local
            
        # Fallback if selected is not available
        if not selected_local.is_available():
            selected_local = self.local

        # Master switch check
        if global_security_state.local_only_mode:
            return selected_local
            
        if privacy_class == PrivacyClass.SECRET:
            return selected_local
            
        if privacy_class in [PrivacyClass.SENSITIVE, PrivacyClass.PRIVATE]:
            return selected_local
            
        if privacy_class == PrivacyClass.INTERNAL:
            if complexity in ["PLAN", "DIRECT_COMPLEX", "TOOL_COMPLEX"] and self.cloud and self.cloud.is_available():
                return self.cloud
            return selected_local
            
        if privacy_class == PrivacyClass.PUBLIC:
            if self.cloud and self.cloud.is_available():
                return self.cloud
            return selected_local
            
        return selected_local
