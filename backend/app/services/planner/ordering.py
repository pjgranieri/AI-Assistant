from typing import List, Dict, Set
from app.services.planner.schema import PlannerTask, PlannerTaskGraph
from app.services.planner.exceptions import CycleDetected

def topological_sort(tasks: List[PlannerTask]) -> List[PlannerTask]:
    task_map: Dict[str, PlannerTask] = {t.task_id: t for t in tasks}
    visited: Set[str] = set()
    temp: Set[str] = set()
    result: List[PlannerTask] = []

    def visit(tid: str):
        if tid in temp:
            raise CycleDetected(f"Cycle detected at {tid}")
        if tid not in visited:
            temp.add(tid)
            for dep in task_map[tid].depends_on:
                if dep not in task_map:
                    continue
                visit(dep)
            temp.remove(tid)
            visited.add(tid)
            result.append(task_map[tid])

    for t in tasks:
        visit(t.task_id)
    # Return in topological order (dependencies first)
    return result[::-1]