import os
from app.security.permissions import PrivacyClass, global_security_state
from app.llm.base import LLMProvider

class LLMRouter:
    def __init__(self, local_provider: LLMProvider, cloud_provider: LLMProvider = None):
        self.local = local_provider
        self.cloud = cloud_provider

    def get_provider(self, privacy_class: PrivacyClass, complexity: str, requires_vision: bool = False) -> LLMProvider:
        # Master switch check
        if global_security_state.local_only_mode:
            return self.local
            
        if privacy_class == PrivacyClass.SECRET:
            return self.local
            
        if privacy_class in [PrivacyClass.SENSITIVE, PrivacyClass.PRIVATE]:
            return self.local
            
        if privacy_class == PrivacyClass.INTERNAL:
            if complexity == "HIGH" and self.cloud and self.cloud.is_available():
                # In real app, check user "cloud for complex tasks" setting
                return self.cloud
            return self.local
            
        if privacy_class == PrivacyClass.PUBLIC:
            if self.cloud and self.cloud.is_available():
                return self.cloud
            return self.local
            
        return self.local
