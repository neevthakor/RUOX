from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def stream(self, messages: List[Dict[str, str]]):
        pass

    @abstractmethod
    def supports_vision(self) -> bool:
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
