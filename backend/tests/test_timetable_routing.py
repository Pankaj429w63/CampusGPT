from fastapi.testclient import TestClient
from app.main import app
from app.agents.planner import classify_query_intent, execute_planned_query, QueryIntent

client = TestClient(app)

def test_intent_routing_and_allocations():
    # 1. Who teaches SML in SY-A?
    q1 = "Who teaches SML in SY-A?"
    assert classify_query_intent(q1) == QueryIntent.TIMETABLE
    res1 = client.post("/ask", json={"question": q1})
    assert res1.status_code == 200
    data1 = res1.json()
    assert "Dr. Sumit Kumar" in data1["answer"]
    assert "Dr. Pooja Kamat" in data1["answer"]
    assert data1["sources"][0]["document"] == "Master TT-26-27-ODD Sem.xlsx"

    # 2. Where is the SY-A A1 lab?
    q2 = "Where is the SY-A A1 lab?"
    assert classify_query_intent(q2) == QueryIntent.TIMETABLE
    res2 = client.post("/ask", json={"question": q2})
    assert res2.status_code == 200
    data2 = res2.json()
    assert "Multimodal Sensor Analytics Lab" in data2["answer"] or "MSA" in data2["answer"]
    assert data2["sources"][0]["document"] == "Master TT-26-27-ODD Sem.xlsx"

    # 3. Which room does PVK teach in?
    q3 = "Which room does PVK teach in?"
    assert classify_query_intent(q3) == QueryIntent.TIMETABLE
    res3 = client.post("/ask", json={"question": q3})
    assert res3.status_code == 200
    data3 = res3.json()
    assert "Dr. Pooja Kamat" in data3["answer"] or "PVK" in data3["answer"]
    assert data3["sources"][0]["document"] == "Master TT-26-27-ODD Sem.xlsx"

    # 4. Ambiguity handling: "Show my timetable" without section
    q4 = "Show my timetable"
    assert classify_query_intent(q4) == QueryIntent.TIMETABLE
    res4 = client.post("/ask", json={"question": q4})
    assert res4.status_code == 200
    data4 = res4.json()
    assert "Please specify which class section" in data4["answer"]

    # 5. Non-timetable general queries preserve RAG
    q5 = "Explain the AIML department curriculum."
    assert classify_query_intent(q5) == QueryIntent.RAG_KNOWLEDGE

