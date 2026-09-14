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
        from app.core.planner import Planner
        from app.core.executor import Executor
        
        planner = Planner(self.router.get_provider(PrivacyClass.PRIVATE, "MEDIUM"))
        executor = Executor(callbacks=self.callbacks)
        
        t_start = time.time()
        self._print(f"Starting task: {task.goal}")
        task.status = "RUNNING"
        
        llm = self.router.get_provider(PrivacyClass.PRIVATE, "MEDIUM")
        
        if not task.messages:
            task.messages.append({
                "role": "system",
                "content": "You are RUOX, a secure local AI assistant. Keep responses brief."
            })
            task.messages.append({"role": "user", "content": task.goal})
            
        intent = planner.classify_intent(task.goal)
        self._print(f"[Agent] Intent classified as: {intent}")
        
        if intent == "PLAN":
            if "on_state_change" in self.callbacks:
                self.callbacks["on_state_change"]("THINKING")
                
            self._print("\n[Agent] Generating execution plan...")
            plan = planner.generate_plan(task.goal, task.messages)
            
            if not plan:
                self._print("\n[Agent] Failed to generate plan. Falling back to default execution.")
                task.status = "FAILED"
                return task
                
            if not planner.validate_plan(plan):
                self._print("\n[Agent] Plan validation failed. Safety check rejected plan.")
                # We could ask for clarification, but we fail closed
                task.messages.append({
                    "role": "assistant",
                    "content": "I generated a plan, but it failed safety validation. Task aborted."
                })
                task.status = "FAILED"
                return task
                
            task.plan = plan
            
            self._print("\n[Agent] Validated Plan:")
            for step in plan.steps:
                self._print(f"  {step.step_id}. {step.description} (Tool: {step.tool_name})")
                
            # Execute plan
            executed_plan = executor.execute_plan(plan, task.task_id)
            
            # Feed results back to LLM for final response
            context_results = []
            for step in executed_plan.steps:
                if step.status == "COMPLETED" and step.result:
                    context_results.append(f"Step {step.step_id} ({step.description}) Result: {step.result}")
                elif step.status == "FAILED":
                    context_results.append(f"Step {step.step_id} ({step.description}) FAILED: {step.error}")
            
            if context_results:
                task.messages.append({
                    "role": "system",
                    "content": "Plan Execution Results:\n" + "\n".join(context_results) + "\n\nProvide a final concise response to the user."
                })
            else:
                task.messages.append({
                    "role": "system",
                    "content": "Plan completed but no results were gathered. Provide a final response."
                })
                
            # Now fall through to the LLM generation for final response
            # we want a single generation turn, similar to DIRECT/TOOL
            
        # Standard generation loop (handles DIRECT, TOOL, and final response of PLAN)
        MAX_AGENT_ITERATIONS = 5
        iteration_count = 0
        
        while task.status == "RUNNING":
            iteration_count += 1
            if iteration_count > MAX_AGENT_ITERATIONS:
                self._print("\n[Agent] MAX_AGENT_ITERATIONS reached. Task failed safely to prevent infinite loop.")
                task.status = "FAILED"
                task.messages.append({"role": "assistant", "content": "I apologize, but I was unable to complete the request within the iteration limit."})
                break
                
            if "on_state_change" in self.callbacks:
                self.callbacks["on_state_change"]("THINKING")
                
            recent_text = " ".join([m["content"] for m in task.messages[-3:] if m["role"] == "user"])
            
            # If we are in PLAN mode and just generating the final response, we don't necessarily need tools
            # If we are in DIRECT mode, we strictly don't pass tools to save context and speed up.
            if intent == "TOOL":
                tools = tool_registry.get_schemas_for_context(recent_text)
            else:
                tools = None
                
            system_msgs = [m for m in task.messages if m["role"] == "system"]
            recent_msgs = [m for m in task.messages if m["role"] != "system"][-10:]
            bounded_messages = system_msgs + recent_msgs
            
            sys_chars = sum(len(m["content"]) for m in system_msgs)
            hist_chars = sum(len(m["content"]) for m in recent_msgs)
            
            self._print(f"\n[RUOX PERF] tools={len(tools) if tools else 0} sys_chars={sys_chars} hist_chars={hist_chars}")
            self._print("\nRUOX: ", end="", flush=True)
            
            full_content = ""
            tool_calls = []
            first_token_received = False
            t_req_start = time.time()
            
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
                        
                self._print("")
                if first_token_received:
                    self._print(f"[Perf] Generation time: {time.time() - t_first_token:.2f}s")
                    
            except Exception as e:
                self._print(f"\n[Generation Interrupted: {e}]")
                task.status = "WAITING_USER"
                return task

            message = {"role": "assistant", "content": full_content}
            if tool_calls:
                message["tool_calls"] = tool_calls
            task.messages.append(message)
                
            if "tool_calls" in message and message["tool_calls"]:
                for tcall in message["tool_calls"]:
                    func = tcall.get("function", {})
                    name = func.get("name")
                    args = func.get("arguments", {})
                    
                    if not name:
                        task.messages.append({"role": "tool", "content": "Error: Tool name empty.", "name": "unknown"})
                        continue
                        
                    if isinstance(args, str):
                        try: args = json.loads(args)
                        except: 
                            task.messages.append({"role": "tool", "content": f"Error: Malformed arguments: {args}", "name": name})
                            continue
                            
                    if "on_state_change" in self.callbacks:
                        self.callbacks["on_state_change"]("TOOL_EXECUTION", {"tool": name})
                        
                    self._print(f"\n[RUOX is attempting to use tool: {name}]")
                    step = TaskStep(id=len(task.steps)+1, action=name)
                    task.steps.append(step)
                    
                    tool = tool_registry.get_tool(name)
                    if tool:
                        result = tool.execute(args, user_confirmed=False)
                        
                        if not result.success and result.error == "AWAITING_CONFIRMATION":
                            if "on_state_change" in self.callbacks:
                                self.callbacks["on_state_change"]("WAITING_APPROVAL", {"tool": name, "args": args, "desc": tool.description})
                                
                            self._print(f"\n--- ACTION PREVIEW ---")
                            self._print(f"Action: {tool.name}\nRisk Level: CONFIRMATION REQUIRED")
                            
                            choice = self._input("Approve execution? [y/N]: ").strip().lower()
                            if choice != 'y':
                                self._print("[RUOX] Action denied.")
                                task.messages.append({"role": "tool", "content": "Error: User denied.", "name": name})
                                continue
                            
                            result = tool.execute(args, user_confirmed=True)
                            
                        if not result.success:
                            step.status = "failed"
                            step.observation = result.error
                            task.messages.append({"role": "tool", "content": f"Error: {result.error}", "name": name})
                        else:
                            step.status = "done"
                            step.observation = str(result.output)
                            task.messages.append({"role": "tool", "content": str(result.output), "name": name})
                    else:
                        task.messages.append({"role": "tool", "content": f"Error: Tool {name} not found.", "name": name})
                
                # Loop back for LLM response
                continue
            else:
                task.status = "WAITING_USER"
                
        return task
