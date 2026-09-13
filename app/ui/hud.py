import customtkinter as ctk
import threading
import queue
import time
import os
import ctypes
from typing import Dict, Any

from app.core.agent import RUOXAgent
from app.llm.ollama import OllamaProvider
from app.llm.router import LLMRouter
from app.core.state import Task
from app.memory.manager import memory_manager
from app.memory.task_store import task_store
from app.core.config import get_system_context

# Configure Appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class RUOXHUD(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("RUOX HUD")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        # Grid layout (1x2): Left=Chat, Right=Status
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.ui_queue = queue.Queue()
        self.agent_thread = None
        self.cancel_requested = False
        self.pending_approval_args = None
        
        self._init_backend()
        self._build_ui()
        
        # Periodic update loop
        self.after(100, self._process_queue)
        self.after(2000, self._update_status_panels)

    def _init_backend(self):
        self.local_llm = OllamaProvider(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("DEFAULT_LOCAL_MODEL", "qwen2.5:7b")
        )
        self.router = LLMRouter(local_provider=self.local_llm)
        
        from app.tools.registry import tool_registry
        from app.tools.system import SystemTimeTool, SystemInfoTool
        from app.tools.computer import (
            OpenApplicationTool, ListDirectoryTool, GetFileInfoTool, 
            CreateDirectoryTool, OpenPathTool, RunCommandTool
        )
        from app.tools.memory import RememberInformationTool, SearchMemoryTool, ListMemoriesTool, ForgetMemoryTool, GetRecentTasksTool
        from app.tools.web import WebSearchTool, WebFetchTool, WebResearchTool
        from app.vision import ScreenContextTool, AnalyzeScreenTool, CaptureScreenTool
        from app.memory.database import db_manager
        
        db_manager.initialize_db()
        tool_registry.register(SystemTimeTool())
        tool_registry.register(SystemInfoTool())
        tool_registry.register(OpenApplicationTool())
        tool_registry.register(ListDirectoryTool())
        tool_registry.register(GetFileInfoTool())
        tool_registry.register(CreateDirectoryTool())
        tool_registry.register(OpenPathTool())
        tool_registry.register(RunCommandTool())
        tool_registry.register(RememberInformationTool())
        tool_registry.register(SearchMemoryTool())
        tool_registry.register(ListMemoriesTool())
        tool_registry.register(ForgetMemoryTool())
        tool_registry.register(GetRecentTasksTool())
        tool_registry.register(WebSearchTool())
        tool_registry.register(WebFetchTool())
        tool_registry.register(WebResearchTool())
        tool_registry.register(ScreenContextTool())
        tool_registry.register(AnalyzeScreenTool())
        tool_registry.register(CaptureScreenTool())
        
        # Callbacks map to thread-safe queue puts
        callbacks = {
            "on_print": lambda text, end: self.ui_queue.put({"type": "print", "text": text, "end": end}),
            "on_token": lambda text: self.ui_queue.put({"type": "token", "text": text}),
            "on_state_change": lambda state, meta=None: self.ui_queue.put({"type": "state", "state": state, "meta": meta}),
            "on_input": self._blocking_approval,
            "on_cancel_check": lambda: self.cancel_requested
        }
        self.agent = RUOXAgent(self.router, callbacks=callbacks)
        self.current_task = Task(goal="Interactive session started via HUD.")
        system_context = get_system_context()
        self.current_task.messages = [{
            "role": "system",
            "content": f"You are RUOX, a secure local AI assistant.\n\n{system_context}"
        }]
        
        # Voice Engines
        from app.voice.audio import AudioRecorder
        from app.voice.stt import STTEngine
        from app.voice.tts import TTSEngine
        self.recorder = AudioRecorder()
        self.stt = STTEngine()
        self.tts = TTSEngine()
        
        # We delay slow STT/TTS loading until needed to keep UI startup fast, or run in background
        def init_voice():
            try:
                self.stt.initialize()
                self.tts.initialize()
                self.ui_queue.put({"type": "print", "text": "Voice Engines Ready.", "end": "\n"})
            except Exception as e:
                self.ui_queue.put({"type": "print", "text": f"Voice Engine init error: {e}", "end": "\n"})
                
        threading.Thread(target=init_voice, daemon=True).start()
        
    def _start_listening(self, event=None):
        if self.agent_thread and self.agent_thread.is_alive():
            return
        self.set_state("LISTENING")
        self.recorder.start_recording()
        
    def _stop_listening(self, event=None):
        if self.status_label.cget("text") != "LISTENING":
            return
        audio_path = self.recorder.stop_recording()
        self.set_state("TRANSCRIBING")
        
        def transcribe_and_send():
            try:
                if audio_path:
                    text = self.stt.transcribe(audio_path)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                    if text.strip():
                        # We use the thread-safe queue to trigger send_message with this text
                        self.ui_queue.put({"type": "send_input", "text": text})
                    else:
                        self.ui_queue.put({"type": "state", "state": "IDLE"})
                else:
                    self.ui_queue.put({"type": "state", "state": "IDLE"})
            except Exception as e:
                self.ui_queue.put({"type": "print", "text": f"STT Error: {e}", "end": "\n"})
                self.ui_queue.put({"type": "state", "state": "IDLE"})
                
        threading.Thread(target=transcribe_and_send, daemon=True).start()

    def _blocking_approval(self, prompt_text: str) -> str:
        """Called by the agent thread when it hits input(). Blocks until UI sets the result."""
        self.approval_result = None
        while self.approval_result is None:
            if self.cancel_requested:
                self.cancel_requested = False
                return "n"
            time.sleep(0.1)
        return self.approval_result

    def _build_ui(self):
        # --- LEFT MAIN AREA ---
        self.left_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        # Top Bar
        self.top_bar = ctk.CTkFrame(self.left_frame, height=40, corner_radius=5)
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.logo_label = ctk.CTkLabel(self.top_bar, text="RUOX :: CORE", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.pack(side="left", padx=15)
        
        self.status_label = ctk.CTkLabel(self.top_bar, text="IDLE", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00FF00")
        self.status_label.pack(side="right", padx=15)

        # Chat Text Box
        self.chat_box = ctk.CTkTextbox(self.left_frame, wrap="word", state="disabled", font=ctk.CTkFont(size=14))
        self.chat_box.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        # Approval Frame (Hidden by default)
        self.approval_frame = ctk.CTkFrame(self.left_frame, fg_color="#442222", corner_radius=8)
        
        self.approval_label = ctk.CTkLabel(self.approval_frame, text="ACTION REQUIRES APPROVAL", font=ctk.CTkFont(weight="bold"))
        self.approval_label.pack(pady=5)
        self.approval_desc = ctk.CTkLabel(self.approval_frame, text="", wraplength=400)
        self.approval_desc.pack(pady=5)
        
        self.approval_btn_frame = ctk.CTkFrame(self.approval_frame, fg_color="transparent")
        self.approval_btn_frame.pack(pady=10)
        self.btn_deny = ctk.CTkButton(self.approval_btn_frame, text="DENY", fg_color="#AA0000", hover_color="#FF0000", command=lambda: self._resolve_approval("n"))
        self.btn_deny.pack(side="left", padx=10)
        self.btn_approve = ctk.CTkButton(self.approval_btn_frame, text="APPROVE", fg_color="#00AA00", hover_color="#00FF00", command=lambda: self._resolve_approval("y"))
        self.btn_approve.pack(side="right", padx=10)

        # Bottom Input Area
        self.input_frame = ctk.CTkFrame(self.left_frame, corner_radius=0, fg_color="transparent")
        self.input_frame.grid(row=2, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.input_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Enter command...", height=40)
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_entry.bind("<Return>", lambda e: self.send_message())
        
        self.send_btn = ctk.CTkButton(self.input_frame, text="SEND", width=80, height=40, command=self.send_message)
        self.send_btn.grid(row=0, column=1)
        
        self.mic_btn = ctk.CTkButton(self.input_frame, text="MIC (PTT)", width=80, height=40, fg_color="#228B22", hover_color="#32CD32")
        self.mic_btn.grid(row=0, column=2, padx=(10,0))
        self.mic_btn.bind("<ButtonPress-1>", self._start_listening)
        self.mic_btn.bind("<ButtonRelease-1>", self._stop_listening)
        
        self.stop_btn = ctk.CTkButton(self.input_frame, text="STOP", width=80, height=40, fg_color="#AA0000", hover_color="#FF0000", command=self.stop_agent)
        self.stop_btn.grid(row=0, column=3, padx=(10,0))

        # --- RIGHT SIDE PANEL ---
        self.right_frame = ctk.CTkFrame(self, width=300, corner_radius=8)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.sys_title = ctk.CTkLabel(self.right_frame, text="SYSTEM STATUS", font=ctk.CTkFont(size=16, weight="bold"))
        self.sys_title.pack(pady=10)
        
        # Security Card
        self.sec_frame = ctk.CTkFrame(self.right_frame, corner_radius=5)
        self.sec_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.sec_frame, text="SECURITY", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5)
        local_mode = os.getenv("LOCAL_ONLY", "true").lower() == "true"
        self.lbl_sec_local = ctk.CTkLabel(self.sec_frame, text="LOCAL_ONLY: " + ("ON" if local_mode else "OFF"), text_color="#00FF00" if local_mode else "#FF0000")
        self.lbl_sec_local.pack(anchor="w", padx=10)
        
        # Model Card
        self.model_frame = ctk.CTkFrame(self.right_frame, corner_radius=5)
        self.model_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.model_frame, text="MODEL", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5)
        self.lbl_model = ctk.CTkLabel(self.model_frame, text=os.getenv("DEFAULT_LOCAL_MODEL", "qwen2.5:7b"))
        self.lbl_model.pack(anchor="w", padx=10)
        
        # Memory & Tasks Card
        self.mem_frame = ctk.CTkFrame(self.right_frame, corner_radius=5)
        self.mem_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.mem_frame, text="MEMORY & TASKS", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5)
        self.lbl_mem_count = ctk.CTkLabel(self.mem_frame, text="Memories: 0")
        self.lbl_mem_count.pack(anchor="w", padx=10)
        self.lbl_task_active = ctk.CTkLabel(self.mem_frame, text="Active Task: None")
        self.lbl_task_active.pack(anchor="w", padx=10)
        
        # Vision Status Card
        self.vision_frame = ctk.CTkFrame(self.right_frame, corner_radius=5)
        self.vision_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.vision_frame, text="VISION", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5)
        self.lbl_vis_cap = ctk.CTkLabel(self.vision_frame, text="Capture: READY", text_color="#00FF00")
        self.lbl_vis_cap.pack(anchor="w", padx=10)
        
        # Log Box
        self.log_frame = ctk.CTkFrame(self.right_frame, corner_radius=5)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkLabel(self.log_frame, text="SYSTEM EVENTS", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5)
        self.log_box = ctk.CTkTextbox(self.log_frame, wrap="word", state="disabled", height=150)
        self.log_box.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.append_log("HUD Initialized.")

    def _resolve_approval(self, choice):
        self.approval_result = choice
        self.approval_frame.grid_forget()
        if choice == "y":
            self.set_state("TOOL_EXECUTION")
        else:
            self.set_state("IDLE")

    def append_chat(self, text, tag=None):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", text)
        if tag:
            # tkinter tags could be used for colors, but simplified here
            pass
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"> {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_state(self, state, meta=None):
        colors = {
            "IDLE": "#00FF00",
            "LISTENING": "#00AAFF",
            "THINKING": "#FFAA00",
            "TOOL_EXECUTION": "#FF00AA",
            "WAITING_APPROVAL": "#FF0000",
            "ERROR": "#FF0000"
        }
        self.status_label.configure(text=state, text_color=colors.get(state, "#FFFFFF"))
        
        if state == "WAITING_APPROVAL":
            tool_name = meta.get("tool", "Unknown") if meta else "Unknown"
            desc = meta.get("desc", "") if meta else ""
            args = meta.get("args", {}) if meta else {}
            arg_str = "\n".join([f"  {k}: {v}" for k,v in args.items()])
            self.approval_desc.configure(text=f"Action: {tool_name}\n\n{desc}\n\nArgs:\n{arg_str}")
            self.approval_frame.grid(row=1, column=0, sticky="se", pady=10, padx=10)
        elif state == "TOOL_EXECUTION":
            tool = meta.get("tool", "") if meta else ""
            self.append_log(f"Running tool: {tool}")
            
    def _process_queue(self):
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                mtype = msg.get("type")
                if mtype == "print":
                    # We only log structural debug prints to the event log, NOT chat
                    text = msg.get("text", "")
                    if text.startswith("[RUOX is attempting") or text.startswith("Tool") or "failed" in text.lower():
                        self.append_log(text.strip())
                elif mtype == "token":
                    self.append_chat(msg.get("text", ""))
                elif mtype == "state":
                    self.set_state(msg.get("state"), msg.get("meta"))
                elif mtype == "send_input":
                    self.send_message(text=msg.get("text"))
        except queue.Empty:
            pass
            
        if self.agent_thread and not self.agent_thread.is_alive() and self.status_label.cget("text") not in ["IDLE", "WAITING_APPROVAL", "ERROR"]:
            self.set_state("IDLE")
            self.append_chat("\n\n")

        self.after(100, self._process_queue)
        
    def _update_status_panels(self):
        try:
            mems = memory_manager.get_all_memories()
            self.lbl_mem_count.configure(text=f"Memories: {len(mems)}")
            
            recent_tasks = task_store.get_recent_tasks(limit=1)
            if recent_tasks:
                self.lbl_task_active.configure(text=f"Task: {recent_tasks[0]['status']}")
        except:
            pass
        self.after(2000, self._update_status_panels)

    def send_message(self, text=None):
        if text is None:
            text = self.input_entry.get().strip()
            if not text:
                return
            self.input_entry.delete(0, 'end')
            
        self.append_chat(f"USER: {text}\n", "user")
        
        self.current_task.messages.append({"role": "user", "content": text})
        
        # Inject dynamic context only if relevant data exists (Optimization)
        relevant_mems = memory_manager.search_relevant_memories(text, limit=3)
        recent_tasks = task_store.get_recent_tasks(limit=1) # Reduced from 3 to 1 to save tokens
        
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
            self.current_task.messages.insert(-1, {"role": "system", "content": context_msg})
        
        # We start the agent thread
        if self.agent_thread and self.agent_thread.is_alive():
            self.append_log("Agent is already running!")
            return
            
        self.append_chat("RUOX: ", "agent")
        
        def run_agent():
            try:
                self.current_task.goal = text
                previous_msg_count = len(self.current_task.messages)
                
                self.agent.run_task(self.current_task)
                task_store.save_task(self.current_task)
                
                # Speak new messages
                if not self.cancel_requested:
                    new_messages = self.current_task.messages[previous_msg_count:]
                    text_to_speak = ""
                    for msg in new_messages:
                        if msg.get("role") == "assistant" and msg.get("content"):
                            text_to_speak += msg["content"] + " "
                    
                    if text_to_speak.strip() and self.tts.is_available():
                        self.ui_queue.put({"type": "state", "state": "SPEAKING"})
                        self.tts.speak(text_to_speak)
                
            except Exception as e:
                self.ui_queue.put({"type": "state", "state": "ERROR"})
                self.ui_queue.put({"type": "print", "text": f"Thread Error: {e}", "end": "\n"})
            finally:
                # Cleanup system message context
                if context_msg:
                    self.current_task.messages = [m for m in self.current_task.messages if m.get("content") != context_msg]

        self.agent_thread = threading.Thread(target=run_agent, daemon=True)
        self.agent_thread.start()

    def stop_agent(self):
        # We can trigger a soft cancel. The thread logic in run_agent might not preempt cleanly 
        # unless it hits an approval, but Ollama stream generator unfortunately blocks. 
        # However, we can set cancel_requested so pending approvals are auto-denied.
        self.cancel_requested = True
        if self.tts.is_available():
            self.tts.stop()
        if self.status_label.cget("text") == "LISTENING":
            self._stop_listening()
        self.append_log("Stop requested by user.")
        self.set_state("IDLE")

if __name__ == "__main__":
    app = RUOXHUD()
    app.mainloop()
