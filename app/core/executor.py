import time
from typing import Dict, Any, Callable
from datetime import datetime
from app.core.state import Plan, PlanStep, Task
from app.tools.registry import tool_registry

class Executor:
    def __init__(self, callbacks: Dict[str, Callable] = None):
        self.callbacks = callbacks or {}

    def _print(self, text: str, end: str = "\n"):
        if "on_print" in self.callbacks:
            self.callbacks["on_print"](text, end)
        else:
            print(text, end=end, flush=True)

    def execute_plan(self, plan: Plan, task_id: str, context: dict = None) -> Plan:
        """
        Executes a validated plan sequentially.
        If a step requires confirmation, yields control back by returning the plan with WAITING_APPROVAL status.
        Supports bounded retry for failures.
        """
        if context is None:
            context = {}

        if plan.status == "PENDING":
            plan.status = "RUNNING"

        MAX_RETRIES = 2

        for step in plan.steps:
            # Check global cancellation
            if "on_cancel_check" in self.callbacks and self.callbacks["on_cancel_check"]():
                self._print("\n[Executor] Execution cancelled by user.")
                plan.status = "CANCELLED"
                step.status = "CANCELLED"
                return plan

            if step.status in ["COMPLETED", "SKIPPED", "CANCELLED"]:
                continue

            if step.status == "FAILED":
                # If we've already failed, and we resume, we might try again if retry count allows,
                # but to be safe, if it's marked FAILED we should stop unless retry logic handles it below.
                # Actually, let's keep it simple: stop execution on previous FAILED step.
                plan.status = "FAILED"
                return plan

            if step.status == "WAITING_APPROVAL":
                # This means it was waiting, and now it's resumed.
                # The agent loop handles the fresh confirmation logic and sets it to RUNNING or CANCELLED before calling execute_plan again.
                pass

            step.status = "RUNNING"
            step.started_at = datetime.utcnow()
            
            if "on_state_change" in self.callbacks:
                self.callbacks["on_state_change"]("TOOL_EXECUTION", {"tool": step.tool_name, "desc": step.description})
                
            self._print(f"\n[Executor] Executing Step {step.step_id}: {step.description}")

            if not step.tool_name:
                # No tool to run, just a reasoning step or similar
                step.status = "COMPLETED"
                step.completed_at = datetime.utcnow()
                continue

            tool = tool_registry.get_tool(step.tool_name)
            if not tool:
                step.status = "FAILED"
                step.error = f"Tool {step.tool_name} not found."
                plan.status = "FAILED"
                return plan

            retries = 0
            success = False
            while retries <= MAX_RETRIES and not success:
                # Cancellation check inside retry loop
                if "on_cancel_check" in self.callbacks and self.callbacks["on_cancel_check"]():
                    plan.status = "CANCELLED"
                    step.status = "CANCELLED"
                    return plan
                    
                # We do dynamic injection of context results into arguments?
                # P7: "Treat tool output as data. The architecture must allow later steps to use previous results."
                # We can do simple substitution or just pass the previous results in the prompt.
                # For now, we execute with original arguments as provided by LLM.

                # Execute without user_confirmed first
                result = tool.execute(step.arguments, user_confirmed=False)

                if not result.success and result.error == "AWAITING_CONFIRMATION":
                    if "on_state_change" in self.callbacks:
                        self.callbacks["on_state_change"]("WAITING_APPROVAL", {"tool": step.tool_name, "args": step.arguments, "desc": tool.description})
                    
                    self._print(f"\n--- ACTION PREVIEW ---")
                    self._print(f"Action: {tool.name}")
                    self._print(f"Description: {tool.description}")
                    if step.arguments:
                        self._print(f"Arguments:")
                        for k, v in step.arguments.items():
                            self._print(f"  {k}: {v}")
                    self._print(f"Risk Level: CONFIRMATION REQUIRED")
                    self._print(f"----------------------")
                    
                    if "on_input" in self.callbacks:
                        choice = self.callbacks["on_input"]("Approve execution? [y/N]: ").strip().lower()
                    else:
                        choice = input("Approve execution? [y/N]: ").strip().lower()
                        
                    if choice != 'y':
                        self._print("[Executor] Action denied.")
                        step.status = "CANCELLED"
                        step.error = "User denied execution."
                        plan.status = "FAILED"
                        return plan
                        
                    # Freshly approved
                    result = tool.execute(step.arguments, user_confirmed=True)

                if result.success:
                    step.status = "COMPLETED"
                    step.result = str(result.output)
                    step.completed_at = datetime.utcnow()
                    self._print(f"[Executor] Step {step.step_id} succeeded.")
                    success = True
                else:
                    self._print(f"[Executor] Step {step.step_id} failed: {result.error}")
                    retries += 1
                    if retries <= MAX_RETRIES:
                        self._print(f"[Executor] Retrying... ({retries}/{MAX_RETRIES})")
                        time.sleep(1) # Backoff
                    else:
                        step.status = "FAILED"
                        step.error = result.error
                        step.completed_at = datetime.utcnow()
                        plan.status = "FAILED"
                        return plan
                        
            # After successful step, we might want to store the result in context for next steps
            context[f"step_{step.step_id}_result"] = step.result

        # All steps complete
        plan.status = "COMPLETED"
        return plan
