import pytest
from app.agents.planner import classify_query_intent, QueryIntent

def test_planner_routing():
    # Timetable queries
    assert classify_query_intent("What is my timetable today?") == QueryIntent.TIMETABLE
    assert classify_query_intent("Show me classes on Monday") == QueryIntent.TIMETABLE
    assert classify_query_intent("lecture schedule for Tuesday") == QueryIntent.TIMETABLE

    # Faculty queries
    assert classify_query_intent("Who is the professor teaching Deep Learning?") == QueryIntent.FACULTY
    assert classify_query_intent("Office hours for Dr. Sharma") == QueryIntent.FACULTY
    assert classify_query_intent("Who is the HOD of Computer Science?") == QueryIntent.FACULTY

    # Calendar queries
    assert classify_query_intent("Show me the academic calendar dates") == QueryIntent.CALENDAR
    assert classify_query_intent("When are the semester end examinations?") == QueryIntent.CALENDAR

    # General RAG Knowledge queries
    assert classify_query_intent("Explain the campus wifi login procedure") == QueryIntent.RAG_KNOWLEDGE
    assert classify_query_intent("What are the hostel room rules?") == QueryIntent.RAG_KNOWLEDGE

