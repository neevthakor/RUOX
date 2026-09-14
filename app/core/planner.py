import json
from typing import List, Optional
from app.core.state import Plan, PlanStep, Task
from app.llm.base import LLMProvider
from app.tools.registry import tool_registry

class Planner:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def classify_intent(self, prompt: str) -> str:
        """
        Lightweight deterministic classifier: DIRECT, TOOL, PLAN
        """
        p = prompt.lower().strip()
        direct_prefixes = ["hello", "hi", "hey", "who are you", "what are you", "test", "what can you do"]
        if any(p.startswith(prefix) for prefix in direct_prefixes) and len(p.split()) <= 4:
            return "DIRECT"
            
        plan_keywords = ["and", "then", "verify", "check", "count", "research", "summarize", "find", "all"]
        # If it asks for time or simple math, it's a TOOL not a PLAN
        if "time" in p or "math" in p or "+" in p or "-" in p or "operating system" in p:
            return "TOOL"
            
        if any(w in p.split() for w in plan_keywords) and len(p.split()) > 3:
            return "PLAN"
            
        return "TOOL"

    def generate_plan(self, goal: str, context_messages: List[dict]) -> Optional[Plan]:
        schemas = tool_registry.get_schemas_for_context(goal)
        tool_descriptions = []
        for s in schemas:
            func = s.get("function", {})
            name = func.get("name")
            desc = func.get("description")
            params = func.get("parameters", {})
            tool_descriptions.append(f"- {name}: {desc}\n  Schema: {json.dumps(params)}")
            
        tools_text = "\n".join(tool_descriptions)
        
        sys_prompt = f"""You are the RUOX Planner. Your job is to create a step-by-step execution plan for the user's goal.
Available tools:
{tools_text}

Rules:
1. Output ONLY a valid JSON array of step objects. Do not write markdown blocks or explanation.
2. Each step must have: "description" (string), "tool_name" (string, optional), "arguments" (object, optional).
3. If a tool requires information you don't have, ask the user in a previous step or plan to search memory.
4. Do NOT guess risky parameters.
5. Include verification steps if modifying state.
6. The plan should be concise. Do not use tools unless necessary.

Example Output:
[
  {{"description": "Create a new folder called reports", "tool_name": "create_directory", "arguments": {{"path": "reports"}}}},
  {{"description": "Verify the folder exists", "tool_name": "get_file_info", "arguments": {{"path": "reports"}}}}
]
"""
        messages = [
            {"role": "system", "content": sys_prompt}
        ]
        
        for msg in context_messages:
            if msg.get("role") in ["user", "assistant"]:
                messages.append(msg)
                
        messages.append({"role": "user", "content": f"Create a plan for: {goal}\nOutput ONLY a JSON array."})
        
        result = self.llm.generate(messages)
        
        if "error" in result:
            print(f"[Planner] LLM Error: {result['error']}")
            return None
            
        content = result.get("message", {}).get("content", "").strip()
        
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        content = content.strip()
        
        try:
            steps_data = json.loads(content)
            if not isinstance(steps_data, list):
                raise ValueError("Expected a JSON array of steps.")
                
            plan = Plan()
            for i, step_dict in enumerate(steps_data):
                step = PlanStep(
                    step_id=i+1,
                    description=step_dict.get("description", f"Step {i+1}"),
                    tool_name=step_dict.get("tool_name"),
                    arguments=step_dict.get("arguments", {})
                )
                plan.steps.append(step)
                
            return plan
        except json.JSONDecodeError as e:
            print(f"[Planner] Failed to parse plan JSON: {e}\nContent: {content}")
            return None
        except Exception as e:
            print(f"[Planner] Error creating plan: {e}")
            return None

    def validate_plan(self, plan: Plan) -> bool:
        """
        Validates that all tools exist and arguments match roughly.
        Invalid tools cause the plan to fail validation.
        """
        for step in plan.steps:
            if step.tool_name:
                tool = tool_registry.get_tool(step.tool_name)
                if not tool:
                    step.status = "FAILED"
                    step.error = f"Unknown tool: {step.tool_name}"
                    return False
                    
                if not isinstance(step.arguments, dict):
                    step.status = "FAILED"
                    step.error = "Arguments must be a dictionary."
                    return False
                    
                step.requires_confirmation = tool.requires_confirmation
                
        return True
