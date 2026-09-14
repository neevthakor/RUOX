import httpx
from typing import List, Dict, Any, Optional
from app.llm.base import LLMProvider

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b"):
        self.base_url = base_url
        self.model = model
        # Use a single client with standard timeouts
        self.client = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(120.0, connect=5.0))

    def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        if tools:
            payload["tools"] = tools

        try:
            response = self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            return {"error": f"LLM Timeout: {str(e)}"}
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
            with self.client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        yield json.loads(line)
        except httpx.TimeoutException as e:
            yield {"error": f"LLM Timeout: {str(e)}"}
        except Exception as e:
            yield {"error": str(e)}

    def supports_vision(self) -> bool:
        return "llava" in self.model or "vision" in self.model

    def supports_tools(self) -> bool:
        return True

    def is_available(self) -> bool:
        try:
            res = self.client.get("/")
            return res.status_code == 200
        except:
            return False
