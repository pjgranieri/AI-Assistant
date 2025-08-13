from typing import List, Optional, Literal, Any, TypedDict
from pydantic import BaseModel, Field

class PlannerTask(BaseModel):
    task_id: str
    title: str
    intent: str
    tool: str
    inputs: dict[str, Any]
    expected_outputs: List[str]
    depends_on: List[str] = Field(default_factory=list)
    success_criteria: Optional[str] = None
    failure_policy: Literal["abort", "skip", "retry"] = "retry"
    est_duration_min: Optional[int] = None

class PlannerTaskGraph(BaseModel):
    tasks: List[PlannerTask]

class PlannerPlanRequest(BaseModel):
    goal: str
    context: Optional[dict[str, Any]] = None

class PlannerPlanResponse(BaseModel):
    plan_id: str
    plan: PlannerTaskGraph