import json
import time
from app.core.state import Task, TaskStep
from app.tools.registry import tool_registry
from app.llm.base import LLMProvider
from app.security.permissions import PrivacyClass

class RUOXAgent:
    def __init__(self, llm_router, callbacks=None):
        self.router = llm_router
        self.callbacks = callbacks or {}

    def _print(self, text, end="\n", flush=False):
        if "on_print" in self.callbacks:
            self.callbacks["on_print"](text, end)
        else:
            print(text, end=end, flush=flush)

    def _input(self, prompt_text):
        if "on_input" in self.callbacks:
            return self.callbacks["on_input"](prompt_text)
        else:
            return input(prompt_text)

    def run_task(self, task: Task):
        t_start = time.time()
        self._print(f"Starting task: {task.goal}")
        task.status = "RUNNING"
        
        llm = self.router.get_provider(PrivacyClass.PRIVATE, "MEDIUM")
        
        # System prompt initialization if no messages exist
        if not task.messages:
            task.messages.append({
                "role": "system",
                "content": "You are RUOX, a secure local AI assistant. Keep responses brief."
            })
            task.messages.append({"role": "user", "content": task.goal})

        while task.status == "RUNNING":
            if "on_state_change" in self.callbacks:
                self.callbacks["on_state_change"]("THINKING")
                
            # Filter schemas based on current user goal or recent history
            recent_text = " ".join([m["content"] for m in task.messages[-3:] if m["role"] == "user"])
            tools = tool_registry.get_schemas_for_context(recent_text)
            
            # Bound context to prevent endless growth
            # Always keep system messages
            system_msgs = [m for m in task.messages if m["role"] == "system"]
            # Keep the last 10 messages (5 turns)
            recent_msgs = [m for m in task.messages if m["role"] != "system"][-10:]
            
            bounded_messages = system_msgs + recent_msgs
            
            # Print performance metrics
            sys_chars = sum(len(m["content"]) for m in system_msgs)
            hist_chars = sum(len(m["content"]) for m in recent_msgs)
            total_chars = sys_chars + hist_chars
            
            self._print(f"\n[RUOX PERF] tools={len(tools)} sys_chars={sys_chars} hist_chars={hist_chars} approx_context_chars={total_chars}")
            
            self._print("\nRUOX: ", end="", flush=True)
            full_content = ""
            tool_calls = []
            
            t_req_start = time.time()
            first_token_received = False
            
            try:
                for chunk in llm.stream(bounded_messages, tools=tools):
                    if "on_cancel_check" in self.callbacks and self.callbacks["on_cancel_check"]():
                        self._print("\n[Generation Cancelled by User]")
                        task.status = "WAITING_USER"
                        return task

                    if not first_token_received:
                        t_first_token = time.time()
                        self._print(f"\n[Perf] Time to first token: {t_first_token - t_req_start:.2f}s")
                        first_token_received = True

                    if "error" in chunk:
                        self._print(f"\nLLM Error: {chunk['error']}")
                        task.status = "FAILED"
                        if "on_state_change" in self.callbacks:
                            self.callbacks["on_state_change"]("ERROR")
                        return task
                        
                    message_chunk = chunk.get("message", {})
                    if "content" in message_chunk and message_chunk["content"]:
                        content = message_chunk["content"]
                        self._print(content, end="", flush=True)
                        full_content += content
                        if "on_token" in self.callbacks:
                            self.callbacks["on_token"](content)
                        
                    if "tool_calls" in message_chunk and message_chunk["tool_calls"]:
                        tool_calls = message_chunk["tool_calls"]
                        
                self._print("") # Newline after response
                t_end_gen = time.time()
                if first_token_received:
                    self._print(f"[Perf] Generation time: {t_end_gen - t_first_token:.2f}s")
            except KeyboardInterrupt:
                self._print("\n[Generation Cancelled]")
                task.status = "WAITING_USER"
                return task
            except Exception as e:
                # E.g. cancellation exception from UI
                self._print(f"\n[Generation Interrupted: {e}]")
                task.status = "WAITING_USER"
                return task

            message = {"role": "assistant", "content": full_content}
            if tool_calls:
                message["tool_calls"] = tool_calls
                
            task.messages.append(message)
                
            # Handle tool calls
            if "tool_calls" in message and message["tool_calls"]:
                for tcall in message["tool_calls"]:
                    func = tcall.get("function", {})
                    name = func.get("name")
                    args = func.get("arguments", {})
                    
                    if not name:
                        self._print("\n[RUOX] Warning: Received empty tool name from LLM.")
                        task.messages.append({
                            "role": "tool",
                            "content": "Error: Tool name was empty.",
                            "name": "unknown"
                        })
                        continue
                        
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except:
                            self._print(f"\n[RUOX] Warning: Malformed arguments for tool {name}.")
                            task.messages.append({
                                "role": "tool",
                                "content": f"Error: Malformed arguments: {args}",
                                "name": name
                            })
                            continue
                    
                    if "on_state_change" in self.callbacks:
                        self.callbacks["on_state_change"]("TOOL_EXECUTION", {"tool": name})
                        
                    self._print(f"\n[RUOX is attempting to use tool: {name}]")
                    t_tool_start = time.time()
                    step = TaskStep(id=len(task.steps)+1, action=name)
                    task.steps.append(step)
                    
                    tool = tool_registry.get_tool(name)
                    if tool:
                        result = tool.execute(args, user_confirmed=False)
                        
                        if not result.success and result.error == "AWAITING_CONFIRMATION":
                            if "on_state_change" in self.callbacks:
                                self.callbacks["on_state_change"]("WAITING_APPROVAL", {"tool": name, "args": args, "desc": tool.description})
                                
                            self._print(f"\n--- ACTION PREVIEW ---")
                            self._print(f"Action: {tool.name}")
                            self._print(f"Description: {tool.description}")
                            if args:
                                self._print(f"Arguments:")
                                for k, v in args.items():
                                    self._print(f"  {k}: {v}")
                            self._print(f"Risk Level: CONFIRMATION REQUIRED")
                            self._print(f"----------------------")
                            
                            choice = self._input("Approve execution? [y/N]: ").strip().lower()
                            if choice != 'y':
                                self._print("[RUOX] Action denied.")
                                task.messages.append({
                                    "role": "tool",
                                    "content": "Error: User denied tool execution.",
                                    "name": name
                                })
                                continue
                            
                            result = tool.execute(args, user_confirmed=True)
                            
                        t_tool_end = time.time()
                        self._print(f"[Perf] Tool {name} execution time: {t_tool_end - t_tool_start:.2f}s")
                        
                        if not result.success:
                            step.status = "failed"
                            step.observation = result.error
                            self._print(f"Tool {name} failed: {result.error}")
                            task.messages.append({
                                "role": "tool",
                                "content": f"Error: {result.error}",
                                "name": name
                            })
                        else:
                            step.status = "done"
                            step.observation = str(result.output)
                            self._print(f"Tool {name} succeeded.")
                            task.messages.append({
                                "role": "tool",
                                "content": str(result.output),
                                "name": name
                            })
                    else:
                        self._print(f"\n[RUOX] Warning: Unknown tool requested: {name}")
                        task.messages.append({
                            "role": "tool",
                            "content": f"Error: Tool {name} not found or not registered.",
                            "name": name
                        })
                # After handling all tool calls, we loop back to let the LLM produce the final response
                # Since task.status is still RUNNING, the loop continues and calls llm.stream() again
                continue
            else:
                # No tool calls, wait for next user input
                task.status = "WAITING_USER"
                
        return task
