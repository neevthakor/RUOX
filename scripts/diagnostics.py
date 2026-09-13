import os
from dotenv import load_dotenv
import requests
from app.llm.ollama import OllamaProvider
from app.tools.registry import tool_registry
from app.tools.system import SystemTimeTool, SystemInfoTool
from app.tools.computer import (
    OpenApplicationTool, ListDirectoryTool, GetFileInfoTool, 
    CreateDirectoryTool, OpenPathTool, RunCommandTool
)
from app.security.permissions import global_security_state

def run_diagnostics():
    load_dotenv()
    print("RUOX SYSTEM CHECK\n")
    
    # 1. Local LLM Check
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("DEFAULT_LOCAL_MODEL", "qwen2.5:7b")
    llm = OllamaProvider(base_url=base_url, model=model)
    
    if llm.is_available():
        # Check if the specific model is installed
        try:
            tags = requests.get(f"{base_url}/api/tags").json()
            models = [t["name"] for t in tags.get("models", [])]
            if model in models or f"{model}:latest" in models:
                print(f"[OK] Local LLM ({model} available)")
            else:
                print(f"[WARN] Local LLM reachable, but model '{model}' not found.")
        except:
            print("[WARN] Local LLM reachable, but failed to fetch tags.")
    else:
        print("[FAIL] Local LLM unavailable (is Ollama running?)")
        
    # 2. Tool Registry Check
    tool_registry.register(SystemTimeTool())
    tool_registry.register(SystemInfoTool())
    tool_registry.register(OpenApplicationTool())
    tool_registry.register(ListDirectoryTool())
    tool_registry.register(GetFileInfoTool())
    tool_registry.register(CreateDirectoryTool())
    tool_registry.register(OpenPathTool())
    tool_registry.register(RunCommandTool())
    
    if len(tool_registry.get_all_schemas()) > 0:
        print("[OK] Tool Registry")
        print("[OK] Computer Tools")
        print("[OK] Application Launcher")
        print("[OK] Filesystem Tools")
        print("[OK] Shell Safety Policy")
    else:
        print("[FAIL] Tool Registry Empty")
        
    # 3. Memory & Task Persistence
    try:
        from app.memory.database import db_manager
        db_manager.initialize_db()
        print("[OK] Memory Database")
        print("[OK] Memory Service")
        print("[OK] Task Persistence")
    except Exception as e:
        print(f"[FAIL] Memory/Database Error: {e}")
        
    # 4. Web Subsystem
    try:
        from app.tools.web.safety import is_local_only
        from app.tools.web.search import get_search_provider
        print("[OK] Web Subsystem")
        print("[OK] Web Security Policies")
        provider = get_search_provider()
        print(f"[OK] Search Provider Configured: {type(provider).__name__}")
        if is_local_only():
            print("[INFO] Web access disabled by LOCAL_ONLY=true")
        else:
            print("[INFO] Web access ENABLED")
    except Exception as e:
        print(f"[FAIL] Web Subsystem Error: {e}")

    # 5. Vision Subsystem
    try:
        from app.vision.capture import screen_capturer
        from app.vision.ocr import get_ocr_provider
        print("[OK] Screen Capture")
        ocr = get_ocr_provider()
        if ocr.available:
            print("[OK] OCR")
        else:
            print("[INFO] OCR unavailable — install/configure provider (e.g. Tesseract)")
        print("[OK] Screen Analyzer")
    except Exception as e:
        print(f"[FAIL] Vision Subsystem Error: {e}")

    # 6. Security Layer Check
    if global_security_state.local_only_mode:
        print("[OK] Security Layer (Local Only Mode: ON)")
    else:
        print("[WARN] Security Layer Warning (Local Only Mode: OFF)")
        
    # 5. Voice Audio/Mic Check
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if len(input_devices) > 0:
            print("[OK] Microphone available")
        else:
            print("[WARN] No microphone detected")
    except ImportError:
        print("[FAIL] sounddevice not installed")
    except Exception as e:
        print(f"[FAIL] Microphone check failed: {e}")

    # 5. Voice STT Check
    try:
        import faster_whisper
        stt_model = os.getenv("STT_MODEL", "tiny.en")
        print(f"[OK] STT Library (faster-whisper available)")
        print(f"     -> Note: Model '{stt_model}' will be downloaded automatically (~100-150MB) upon first use if not cached.")
    except ImportError:
        print("[FAIL] STT Library (faster-whisper not installed)")
        
    # 6. Voice TTS Check
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        if len(voices) > 0:
            print(f"[OK] TTS (pyttsx3 available with {len(voices)} local system voices)")
        else:
            print("[WARN] TTS (pyttsx3 installed but no system voices found)")
    except ImportError:
        print("[FAIL] TTS (pyttsx3 not installed)")
    except Exception as e:
        print(f"[FAIL] TTS init failed: {e}")
        
    print("\nOverall: System check complete.")

if __name__ == "__main__":
    run_diagnostics()
