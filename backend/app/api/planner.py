from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import uuid4
from app.services.planner.schema import PlannerPlanRequest, PlannerPlanResponse, PlannerTaskGraph
from app.services.planner.llm_planner import planner_engine, make_plan_id
from app.db.models.plan import Plan
from app.deps import get_db

router = APIRouter()

@router.post("/plan", response_model=PlannerPlanResponse)
def plan_endpoint(
    req: PlannerPlanRequest,
    db: Session = Depends(get_db),
):
    plan = planner_engine(req.goal, req.context)
    plan_id = make_plan_id()
    plan_obj = Plan(
        id=plan_id,
        user_id=None,
        goal=req.goal,
        plan_json=plan.model_dump(),
    )
    db.add(plan_obj)
    db.commit()
    return PlannerPlanResponse(plan_id=plan_id, plan=plan)