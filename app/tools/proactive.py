import json
from app.tools.base import Tool, ToolResult
from app.proactive.scheduler import scheduler
from datetime import datetime, timedelta
from typing import Dict, Any

class ScheduleTaskTool(Tool):
    name = "schedule_task"
    description = "Schedules a task to run at a specific time or on a recurring basis. Provide either 'minutes_from_now' or 'cron_expr'."
    requires_confirmation = False

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        goal = kwargs.get("goal")
        minutes_from_now = kwargs.get("minutes_from_now")
        cron_expr = kwargs.get("cron_expr")
        
        if not goal:
            return ToolResult(success=False, error="Goal required")
            
        trigger_time = None
        if minutes_from_now is not None:
            trigger_time = datetime.now().astimezone() + timedelta(minutes=int(minutes_from_now))
            
        sched_id = scheduler.schedule_task(goal=goal, trigger_time=trigger_time, cron_expr=cron_expr)
        
        msg = f"Task scheduled with ID {sched_id}."
        if trigger_time:
            msg += f" Will run at {trigger_time.isoformat()}."
        if cron_expr:
            msg += f" Will run on cron {cron_expr}."
            
        return ToolResult(success=True, output=msg)

class CancelScheduleTool(Tool):
    name = "cancel_schedule"
    description = "Cancels a scheduled task or reminder based on its goal description."
    requires_confirmation = False

    def execute(self, kwargs: Dict[str, Any], user_confirmed: bool = False) -> ToolResult:
        query = kwargs.get("goal_query")
        if not query:
            return ToolResult(success=False, error="Goal query required")
            
        success = scheduler.cancel_schedule(query)
        if success:
            return ToolResult(success=True, output=f"Cancelled schedule matching: {query}")
        return ToolResult(success=False, error=f"No active schedule found matching: {query}")
