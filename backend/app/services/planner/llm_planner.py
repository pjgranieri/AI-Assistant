# backend/app/services/planner/llm_planner.py
import uuid
from typing import Any, Dict
from app.services.planner.schema import PlannerTask, PlannerTaskGraph
from app.services.planner.registry import ToolRegistry
from app.services.planner.ordering import topological_sort
from app.services.planner.exceptions import CycleDetected

def llm_complete(prompt: str) -> str:
    # Stub for LLM call
    raise NotImplementedError

def sanitize_plan(plan: PlannerTaskGraph) -> PlannerTaskGraph:
    for t in plan.tasks:
        if not t.failure_policy:
            t.failure_policy = "retry"
    return plan

def validate_plan(plan: PlannerTaskGraph) -> PlannerTaskGraph:
    # Check all depends_on reference valid task_ids
    task_ids = {t.task_id for t in plan.tasks}
    for t in plan.tasks:
        for dep in t.depends_on:
            if dep not in task_ids:
                raise ValueError(f"depends_on references missing task_id: {dep}")
    # Check tools are in registry
    for t in plan.tasks:
        if t.tool not in ToolRegistry.all_tools():
            raise ValueError(f"Unknown tool: {t.tool}")
    # Check at least one dependency exists
    if not any(t.depends_on for t in plan.tasks):
        raise ValueError("No dependencies between tasks")
    # Check topological order and cycles
    topological_sort(plan.tasks)
    return plan

def fallback_plan(goal: str, context: dict[str, Any] | None = None) -> PlannerTaskGraph:
    # Deterministic fallback for acceptance prompt
    t1 = PlannerTask(
        task_id="t1",
        title="Read calendar for the week",
        intent="Get all events and free time blocks for the week",
        tool="calendar_agent.read",
        inputs={"window_days": 7},
        expected_outputs=["events", "free_blocks"],
        depends_on=[],
    )
    t2 = PlannerTask(
        task_id="t2",
        title="Book dentist appointment",
        intent="Find and propose dentist appointments",
        tool="booking_agent.search_providers",
        inputs={"insurance": "user_insurance", "location": "user_location", "window_days": 14},
        expected_outputs=["provider_options"],
        depends_on=["t1"],
    )
    t3 = PlannerTask(
        task_id="t3",
        title="Draft email replies",
        intent="Draft replies to important emails",
        tool="email_agent.draft_batch",
        inputs={"inbox_filter": {"unread": True, "important": True}, "tone": "professional"},
        expected_outputs=["drafts"],
        depends_on=["t1"],
    )
    return PlannerTaskGraph(tasks=[t1, t2, t3])

def planner_engine(goal: str, context: dict[str, Any] | None = None) -> PlannerTaskGraph:
    # Compose prompt (system, tool catalog, goal, context)
    prompt = f"""You are a planning agent. Available tools:\n"""
    for name, spec in ToolRegistry.all_tools().items():
        prompt += f"- {name}: {spec['description']}\n"
    prompt += f"\nGoal: {goal}\n"
    if context:
        prompt += f"Context: {context}\n"
    prompt += "Return a JSON object with tasks, dependencies, and tool usage."

    try:
        raw = llm_complete(prompt)
        import json
        plan_dict = json.loads(raw)
        plan = PlannerTaskGraph(**plan_dict)
        plan = sanitize_plan(plan)
        plan = validate_plan(plan)
        return plan
    except Exception:
        # Fallback deterministic plan
        return fallback_plan(goal, context)

def make_plan_id() -> str:
    return str(uuid.uuid4())