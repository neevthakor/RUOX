import json
from app.core.state import Task, TaskStep
from app.tools.registry import tool_registry
from app.llm.base import LLMProvider
from app.security.permissions import PrivacyClass

class RUOXAgent:
    def __init__(self, llm_router):
        self.router = llm_router

    def run_task(self, task: Task):
        print(f"Starting task: {task.goal}")
        task.status = "RUNNING"
        
        llm = self.router.get_provider(PrivacyClass.PRIVATE, "MEDIUM")
        tools = tool_registry.get_all_schemas()
        
        # System prompt initialization if no messages exist
        if not task.messages:
            task.messages.append({
                "role": "system",
                "content": "You are RUOX, a secure local AI assistant. You can help the user with tasks and use tools when needed."
            })
            task.messages.append({"role": "user", "content": task.goal})

        while task.status == "RUNNING":
            # Generate response from LLM using stream to allow interruption
            print("\nRUOX: ", end="", flush=True)
            full_content = ""
            tool_calls = []
            
            try:
                for chunk in llm.stream(task.messages, tools=tools):
                    if "error" in chunk:
                        print(f"\nLLM Error: {chunk['error']}")
                        task.status = "FAILED"
                        return task
                        
                    message_chunk = chunk.get("message", {})
                    if "content" in message_chunk and message_chunk["content"]:
                        content = message_chunk["content"]
                        print(content, end="", flush=True)
                        full_content += content
                        
                    if "tool_calls" in message_chunk and message_chunk["tool_calls"]:
                        # Ollama streaming tool calls usually arrive in a chunk or we just aggregate them
                        # For simplicity in this P1, if it's streaming tool calls we collect them.
                        tool_calls = message_chunk["tool_calls"]
                        
                print() # Newline after response
            except KeyboardInterrupt:
                print("\n[Generation Cancelled]")
                # We can save partial response if we want, but for now just break
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
                        print("\n[RUOX] Warning: Received empty tool name from LLM.")
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
                            print(f"\n[RUOX] Warning: Malformed arguments for tool {name}.")
                            task.messages.append({
                                "role": "tool",
                                "content": f"Error: Malformed arguments: {args}",
                                "name": name
                            })
                            continue
                    
                    print(f"\n[RUOX is attempting to use tool: {name}]")
                    step = TaskStep(id=len(task.steps)+1, action=name)
                    task.steps.append(step)
                    
                    tool = tool_registry.get_tool(name)
                    if tool:
                        # Attempt to execute first (it might fail if it needs confirmation)
                        result = tool.execute(args, user_confirmed=False)
                        
                        if not result.success and result.error == "AWAITING_CONFIRMATION":
                            # Dynamic or static confirmation required
                            print(f"\n--- ACTION PREVIEW ---")
                            print(f"Action: {tool.name}")
                            print(f"Description: {tool.description}")
                            if args:
                                print(f"Arguments:")
                                for k, v in args.items():
                                    print(f"  {k}: {v}")
                            print(f"Risk Level: CONFIRMATION REQUIRED")
                            print(f"----------------------")
                            
                            choice = input("Approve execution? [y/N]: ").strip().lower()
                            if choice != 'y':
                                print("[RUOX] Action denied.")
                                task.messages.append({
                                    "role": "tool",
                                    "content": "Error: User denied tool execution.",
                                    "name": name
                                })
                                continue
                            
                            # Execute again with confirmation
                            result = tool.execute(args, user_confirmed=True)
                            
                        if not result.success:
                            step.status = "failed"
                            step.observation = result.error
                            print(f"Tool {name} failed: {result.error}")
                            task.messages.append({
                                "role": "tool",
                                "content": f"Error: {result.error}",
                                "name": name
                            })
                        else:
                            step.status = "done"
                            step.observation = str(result.output)
                            print(f"Tool {name} succeeded.")
                            task.messages.append({
                                "role": "tool",
                                "content": str(result.output),
                                "name": name
                            })
                    else:
                        print(f"\n[RUOX] Warning: Unknown tool requested: {name}")
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
