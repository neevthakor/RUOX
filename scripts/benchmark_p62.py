import time
import os
from app.llm.ollama import OllamaProvider
from app.llm.router import LLMRouter
from app.core.agent import RUOXAgent
from app.core.state import Task
from app.tools.registry import tool_registry

from app.tools.system import SystemTimeTool, SystemInfoTool
from app.tools.computer import OpenApplicationTool, ListDirectoryTool, GetFileInfoTool, CreateDirectoryTool, OpenPathTool, RunCommandTool
from app.tools.memory import RememberInformationTool, SearchMemoryTool, ListMemoriesTool, ForgetMemoryTool, GetRecentTasksTool
from app.tools.web import WebSearchTool, WebFetchTool, WebResearchTool
from app.vision import ScreenContextTool, AnalyzeScreenTool, CaptureScreenTool

def register_all():
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

def measure_direct_ollama(prompt):
    print(f"\n--- DIRECT OLLAMA: '{prompt}' ---")
    provider = OllamaProvider("http://localhost:11434", "qwen2.5:7b")
    messages = [{"role": "user", "content": prompt}]
    t0 = time.time()
    stream = provider.stream(messages)
    ttft = None
    for chunk in stream:
        if ttft is None:
            ttft = time.time() - t0
    t_end = time.time()
    gen_time = t_end - (t0 + (ttft or 0))
    print(f"TTFT: {ttft:.2f}s | Generation: {gen_time:.2f}s | Total: {t_end - t0:.2f}s")

def measure_ruox(prompt):
    print(f"\n--- RUOX PIPELINE: '{prompt}' ---")
    provider = OllamaProvider("http://localhost:11434", "qwen2.5:7b")
    router = LLMRouter(provider)
    
    agent = RUOXAgent(router, callbacks={"on_input": lambda p: "n"})
    
    task = Task(goal=prompt)
    task.messages = [{"role": "system", "content": "You are RUOX."}]
    task.messages.append({"role": "user", "content": prompt})
    
    t0 = time.time()
    agent.run_task(task)
    t_end = time.time()
    
    print(f"Total Pipeline Time: {t_end - t0:.2f}s")

if __name__ == '__main__':
    register_all()
    prompts = [
        "Hello RUOX",
        "What is 2 + 2?",
        "What is the current time?",
        "What operating system am I running?"
    ]
    for p in prompts:
        measure_direct_ollama(p)
        measure_ruox(p)
