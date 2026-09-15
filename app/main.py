import os
import json
from dotenv import load_dotenv
from app.llm.ollama import OllamaProvider
from app.llm.router import LLMRouter
from app.tools.registry import tool_registry
from app.tools.system import SystemTimeTool, SystemInfoTool
from app.tools.computer import (
    OpenApplicationTool, ListDirectoryTool, GetFileInfoTool, 
    CreateDirectoryTool, OpenPathTool, RunCommandTool,
    MousePositionTool, MouseMoveTool, MouseClickTool, MouseScrollTool,
    KeyboardTypeTool, KeyboardHotkeyTool,
    WindowListTool, WindowFocusTool, WindowCloseTool
)
from app.core.agent import RUOXAgent
from app.core.state import Task

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="RUOX Local AI Assistant")
    parser.add_argument("--voice", action="store_true", help="Start RUOX in Voice Mode (Push-to-Talk)")
    args = parser.parse_args()

    load_dotenv()
    
    # Initialize components
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    local_llm = OllamaProvider(
        base_url=base_url,
        model=os.getenv("DEFAULT_LOCAL_MODEL", "qwen2.5:7b")
    )
    fast_llm = OllamaProvider(
        base_url=base_url,
        model=os.getenv("FAST_LOCAL_MODEL", "qwen2.5:0.5b")
    )
    strong_llm = OllamaProvider(
        base_url=base_url,
        model=os.getenv("STRONG_LOCAL_MODEL", "qwen2.5:14b")
    )
    router = LLMRouter(local_provider=local_llm, fast_provider=fast_llm, strong_provider=strong_llm)
    
    # Eagerly initialize and warm up providers in the background to avoid 35s penalty on first run
    fast_llm.warmup()
    strong_llm.warmup()
    
    from app.tools.memory import RememberInformationTool, SearchMemoryTool, ListMemoriesTool, ForgetMemoryTool, GetRecentTasksTool
    from app.tools.web import WebSearchTool, WebFetchTool, WebResearchTool
    from app.vision import ScreenContextTool, AnalyzeScreenTool, CaptureScreenTool
    from app.memory.database import db_manager
    from app.memory.task_store import task_store
    from app.memory.manager import memory_manager
    
    # Initialize DB
    db_manager.initialize_db()
    
    # Register tools
    tool_registry.register(SystemTimeTool())
    tool_registry.register(SystemInfoTool())
    tool_registry.register(OpenApplicationTool())
    tool_registry.register(ListDirectoryTool())
    tool_registry.register(GetFileInfoTool())
    tool_registry.register(CreateDirectoryTool())
    tool_registry.register(OpenPathTool())
    tool_registry.register(RunCommandTool())
    
    tool_registry.register(MousePositionTool())
    tool_registry.register(MouseMoveTool())
    tool_registry.register(MouseClickTool())
    tool_registry.register(MouseScrollTool())
    tool_registry.register(KeyboardTypeTool())
    tool_registry.register(KeyboardHotkeyTool())
    tool_registry.register(WindowListTool())
    tool_registry.register(WindowFocusTool())
    tool_registry.register(WindowCloseTool())
    
    tool_registry.register(RememberInformationTool())
    tool_registry.register(SearchMemoryTool())
    tool_registry.register(ListMemoriesTool())
    tool_registry.register(ForgetMemoryTool())
    tool_registry.register(GetRecentTasksTool())
    tool_registry.register(WebSearchTool())
    tool_registry.register(WebFetchTool())
    tool_registry.register(WebResearchTool())
    
    # Browser Agent Tools (P13)
    from app.tools.web.browser import BrowserOpenTool, BrowserObserveTool, BrowserClickTool, BrowserTypeTool, BrowserExtractTool
    tool_registry.register(BrowserOpenTool())
    tool_registry.register(BrowserObserveTool())
    tool_registry.register(BrowserClickTool())
    tool_registry.register(BrowserTypeTool())
    tool_registry.register(BrowserExtractTool())
    
    tool_registry.register(ScreenContextTool())
    tool_registry.register(AnalyzeScreenTool())
    tool_registry.register(CaptureScreenTool())
    
    # Proactive Tools (P15)
    from app.tools.proactive import ScheduleTaskTool, CancelScheduleTool
    tool_registry.register(ScheduleTaskTool())
    tool_registry.register(CancelScheduleTool())
    
    # Knowledge Tools (P16)
    from app.tools.knowledge import RememberKnowledgeTool, SearchKnowledgeTool
    tool_registry.register(RememberKnowledgeTool())
    tool_registry.register(SearchKnowledgeTool())
    
    # Initialize Agent
    agent = RUOXAgent(router)
    
    # Initialize Scheduler (P15)
    from app.proactive.scheduler import scheduler
    scheduler.start()
    
    # Initialize Task Engine (P14)
    from app.core.engine import init_engine
    init_engine(agent)
    
    if args.voice:
        print("Initializing Voice Engines...")
        from app.voice.audio import AudioRecorder
        from app.voice.stt import STTEngine
        from app.voice.tts import TTSEngine
        
        recorder = AudioRecorder()
        stt = STTEngine()
        stt.initialize()
        
        tts = TTSEngine()
        tts.initialize()
        
        print("RUOX Voice Mode Initialized.")
        print("Press Ctrl+C to exit.")
        print("Security Mode: LOCAL_ONLY=" + os.getenv("LOCAL_ONLY", "true"))
    else:
        print("RUOX Core Initialized. Type 'exit' to quit. Or use --voice for voice mode.")
        print("Security Mode: LOCAL_ONLY=" + os.getenv("LOCAL_ONLY", "true"))
    
    from app.core.config import get_system_context
    system_context = get_system_context()
    
    base_prompt = "You are RUOX, a secure local AI assistant. Keep responses extremely brief and concise when in voice mode." if args.voice else "You are RUOX, a secure local AI assistant. You can help the user with tasks and use tools when needed."
    
    # Create an ongoing session history
    session_messages = [
        {
            "role": "system",
            "content": f"{base_prompt}\n\n{system_context}"
        }
    ]
    
    while True:
        try:
            if args.voice:
                print("\n[Voice Mode] Ready.")
                audio_path = recorder.record_until_interrupt()
                if not audio_path:
                    continue
                
                print("Transcribing...")
                user_input = stt.transcribe(audio_path)
                
                # Cleanup temp file
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except:
                        pass
                        
                if not user_input.strip():
                    print("Could not transcribe anything. Please try again.")
                    continue
                    
                print(f"\nYou: {user_input}")
            else:
                user_input = input("\nYou: ")
                if user_input.strip().lower() in ['exit', 'quit']:
                    break
                if not user_input.strip():
                    continue
                
            # Fetch relevant memory context only if likely needed
            relevant_mems = memory_manager.search_relevant_memories(user_input, limit=3)
            
            recent_tasks = []
            words = set(user_input.lower().split())
            
            # Check for explicit resume
            if user_input.strip().lower() in ["resume task", "resume", "continue"]:
                incomplete = task_store.get_recent_tasks(limit=5)
                paused = [t for t in incomplete if t["status"] == "PAUSED"]
                if paused:
                    task_data = paused[0]
                    print(f"[RUOX] Resuming task: {task_data['goal']}")
                    # We would ideally reconstruct the task fully. For now, just create a new task with the old goal.
                    current_task = Task(goal=task_data['goal'])
                    current_task.messages = json.loads(task_data.get("metadata", "{}")).get("messages", [])
                    if not current_task.messages:
                        current_task.messages = [
                            {"role": "system", "content": f"{base_prompt}\n\n{system_context}"},
                            {"role": "user", "content": task_data['goal']}
                        ]
                    session_messages = current_task.messages
                else:
                    print("[RUOX] No paused tasks found.")
                    continue
            else:
                if any(w in words for w in ["task", "resume", "continue", "earlier", "previous", "status", "last"]):
                    recent_tasks = task_store.get_recent_tasks(limit=1)
                
                context_msg = None
                if relevant_mems or recent_tasks:
                    parts = []
                    if relevant_mems:
                        mem_text = "\n".join([f"- {m.content}" for m in relevant_mems])
                        parts.append(f"RELEVANT MEMORIES:\n{mem_text}")
                    if recent_tasks:
                        task_text = "\n".join([f"- {t['goal']} ({t['status']})" for t in recent_tasks])
                        parts.append(f"RECENT TASK HISTORY:\n{task_text}")
                    
                    context_msg = "[SYSTEM CONTEXT]\n" + "\n\n".join(parts)
                    session_messages.append({"role": "system", "content": context_msg})
                    
                session_messages.append({"role": "user", "content": user_input})
                current_task = Task(goal=user_input)
                current_task.messages = session_messages.copy()
            
            previous_msg_count = len(current_task.messages)
            
            current_task = agent.run_task(current_task)
            
            # Update session history
            session_messages = current_task.messages.copy()
            
            # Save messages in metadata for resumption
            meta = {"messages": session_messages}
            current_task.metadata = meta
            task_store.save_task(current_task)
            
            # Remove the temporary context block so it doesn't bloat the history forever
            if 'context_msg' in locals() and context_msg:
                session_messages = [msg for msg in session_messages if msg.get("content") != context_msg]
            session_messages = [msg for msg in session_messages if not (msg.get("role") == "system" and "Plan Execution Results" in msg.get("content", ""))]
            
            if args.voice and tts.is_available():
                # Read out all new assistant messages generated during the loop
                new_messages = current_task.messages[previous_msg_count:]
                for msg in new_messages:
                    if msg.get("role") == "assistant" and msg.get("content"):
                        tts.speak(msg["content"])
            
        except KeyboardInterrupt:
            print("\n[Interrupted]")
            if not args.voice:
                continue
            else:
                break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
