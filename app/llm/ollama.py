import requests
from typing import List, Dict, Any, Optional
from app.llm.base import LLMProvider

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b"):
        self.base_url = base_url
        self.model = model

    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def stream(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None):
        import json
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        if tools:
            payload["tools"] = tools

        try:
            with requests.post(f"{self.base_url}/api/chat", json=payload, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        yield json.loads(line)
        except Exception as e:
            yield {"error": str(e)}

    def supports_vision(self) -> bool:
        # Depends on model, simplistic check
        return "llava" in self.model or "vision" in self.model

    def supports_tools(self) -> bool:
        return True

    def is_available(self) -> bool:
        try:
            res = requests.get(self.base_url)
            return res.status_code == 200
        except:
            return False
