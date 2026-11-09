"""
Comprehensive unit and integration tests for Timetable Endpoints, Planner Routing, and Ambiguity Handling.
"""
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.agents.planner import classify_query_intent, execute_planned_query, QueryIntent

client = TestClient(app)

def test_get_timetable_sheets_endpoint():
    response = client.get("/timetable/sheets")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "SY-A" in data["sheets"]
    assert "TY-A" in data["sheets"]
    assert "B.Tech-A" in data["sheets"]
    assert data["total_entries"] > 100

def test_get_class_schedule_endpoint():
    response = client.get("/timetable/class/SY-A?day=Monday")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["sheet_name"] == "SY-A"
    assert data["day"] == "Monday"
    assert data["count"] > 0
    assert any(e["day"] == "Monday" for e in data["entries"])

def test_get_today_schedule_endpoint():
    response = client.get("/timetable/today/SY-A")
    assert response.status_code == 200
    data = response.json()
    assert "day" in data
    assert "is_holiday" in data

def test_get_next_class_endpoint():
    response = client.get("/timetable/next/SY-A")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "message" in data

def test_get_free_periods_endpoint():
    response = client.get("/timetable/free/SY-A?day=Monday")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "free_slots" in data

def test_search_timetable_endpoint():
    # Search by room
    res_room = client.get("/timetable/search?room=503")
    assert res_room.status_code == 200
    data_room = res_room.json()
    assert data_room["status"] == "success"
    assert data_room["count"] > 0

    # Search by subject
    res_sub = client.get("/timetable/search?subject=Operating Systems")
    assert res_sub.status_code == 200
    data_sub = res_sub.json()
    assert data_sub["status"] == "success"
    assert data_sub["count"] > 0

    # Search without params should 400
    res_empty = client.get("/timetable/search")
    assert res_empty.status_code == 400

@pytest.mark.asyncio
async def test_planner_routing_and_timetable_queries():
    # 1. Timetable query routing
    intent = classify_query_intent("Show me the timetable for SY-A on Monday")
    assert intent == QueryIntent.TIMETABLE

    # 2. Execution of specific class timetable query
    ans, srcs, meta = await execute_planned_query("Show me the timetable for SY-A on Monday")
    assert meta["selected_tool"] == QueryIntent.TIMETABLE
    assert "SY-A" in ans or "Monday" in ans
    assert "Master TT-26-27-ODD Sem.xlsx" in srcs[0]["document"]

    # 3. Execution of today's timetable query
    ans_today, _, _ = await execute_planned_query("What is my timetable today for SY-A?")
    assert "SY-A" in ans_today or "Schedule" in ans_today

    # 4. Next class query
    ans_next, _, _ = await execute_planned_query("What is the next class for SY-A?")
    assert "Class Status" in ans_next or "SY-A" in ans_next

    # 5. Free periods query
    ans_free, _, _ = await execute_planned_query("When is the free period for SY-A?")
    assert "Free Periods for SY-A" in ans_free or "free" in ans_free.lower()

