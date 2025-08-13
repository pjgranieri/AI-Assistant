import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_planner_acceptance():
    prompt = "Plan my week… also book dentist and draft replies."
    resp = client.post("/planner/plan", json={"goal": prompt})
    assert resp.status_code == 200
    data = resp.json()
    plan = data["plan"]
    tasks = plan["tasks"]
    assert len(tasks) >= 3
    task_ids = {t["task_id"] for t in tasks}
    # All depends_on reference existing task_id
    for t in tasks:
        for dep in t.get("depends_on", []):
            assert dep in task_ids
    # At least one task depends on another
    assert any(t.get("depends_on") for t in tasks)
    # Tools used are in registry
    from backend.app.services.planner.registry import ToolRegistry
    tool_names = set(ToolRegistry.all_tools().keys())
    for t in tasks:
        assert t["tool"] in tool_names