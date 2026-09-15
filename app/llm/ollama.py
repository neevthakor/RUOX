import httpx
from typing import List, Dict, Any, Optional
from app.llm.base import LLMProvider
import threading

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b"):
        self.base_url = base_url
        self.model = model
        # Increase connection pool limits and reuse client
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        self.client = httpx.Client(base_url=self.base_url, timeout=httpx.Timeout(120.0, connect=5.0), limits=limits)

    def warmup(self):
        """Preload model in the background to avoid 35-second cold start."""
        def _warm():
            try:
                # A fast generate request just to load the model into VRAM
                # We can just request a single token or use keep_alive.
                payload = {"model": self.model, "prompt": "", "stream": False, "options": {"num_predict": 1}}
                self.client.post("/api/generate", json=payload, timeout=60.0)
            except Exception as e:
                print(f"[Ollama] Warmup failed for {self.model}: {e}")
                
        t = threading.Thread(target=_warm, daemon=True)
        t.start()

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
        import time
        if hasattr(self, '_last_avail_check'):
            # Cache for 60 seconds since model lists rarely change
            if time.time() - self._last_avail_check < 60.0:
                return self._last_avail_status
                
        try:
            res = self.client.get("/api/tags", timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                self._last_avail_status = (self.model in models)
            else:
                self._last_avail_status = False
        except:
            self._last_avail_status = False
            
        self._last_avail_check = time.time()
        return self._last_avail_status
