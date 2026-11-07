import re
import time
from typing import Dict, Any, Tuple, List
import logging
from app.core.metrics import TOOL_CALLS_TOTAL, STAGE_LATENCY_SECONDS
from app.tools.structured_data import (
    query_timetable_tool,
    query_faculty_tool,
    query_academic_calendar_tool
)
from app.rag.pipeline import ask_campusgpt_rag

logger = logging.getLogger(__name__)

class QueryIntent:
    TIMETABLE = "timetable_lookup"
    FACULTY = "faculty_lookup"
    CALENDAR = "academic_calendar_lookup"
    RAG_KNOWLEDGE = "rag_knowledge_retrieval"

class AgentPlannerMetrics:
    def __init__(self):
        self.total_plans = 0
        self.tool_calls_count = {
            QueryIntent.TIMETABLE: 0,
            QueryIntent.FACULTY: 0,
            QueryIntent.CALENDAR: 0,
            QueryIntent.RAG_KNOWLEDGE: 0,
        }
        self.successful_calls = 0
        self.unnecessary_calls = 0

planner_metrics = AgentPlannerMetrics()

def classify_query_intent(query: str) -> str:
    """
    Deterministically routes questions to specialized tools:
    - Timetable questions -> deterministic schedule engine
    - Faculty questions -> deterministic faculty database
    - Calendar/regulations -> academic calendar tool
    - General institutional questions -> RAG pipeline
    """
    q = query.lower()

    # Timetable pattern heuristics
    if any(k in q for k in ["timetable", "schedule", "classes", "lecture", "routine"]):
        return QueryIntent.TIMETABLE

    # Faculty pattern heuristics
    if any(k in q for k in ["faculty", "professor", "who teaches", "hod", "office hour", "dr.", "prof."]):
        return QueryIntent.FACULTY

    # Calendar & General Regulations
    if any(k in q for k in ["calendar", "semester dates", "cie dates", "when are exams", "last date of instruction", "examinations", "exam dates"]):
        return QueryIntent.CALENDAR

    # Default to RAG knowledge base retrieval
    return QueryIntent.RAG_KNOWLEDGE

async def execute_planned_query(question: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Orchestrates execution of the selected tool and formats responses.
    Returns: (answer_string, sources_list, execution_metadata)
    """
    t_start = time.perf_counter()
    planner_metrics.total_plans += 1
    
    intent = classify_query_intent(question)
    planner_metrics.tool_calls_count[intent] += 1
    
    metadata = {
        "selected_tool": intent,
        "query": question,
        "deterministic": False
    }

    try:
        if intent == QueryIntent.TIMETABLE:
            STAGE_LATENCY_SECONDS.labels(stage="deterministic_timetable").observe(time.perf_counter() - t_start)
            TOOL_CALLS_TOTAL.labels(tool_name="timetable_lookup", status="success").inc()
            planner_metrics.successful_calls += 1
            metadata["deterministic"] = True
            
            # Extract day if mentioned
            day = None
            for d in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
                if d in question.lower():
                    day = d
                    break
            if not day and "today" in question.lower():
                day = "today"
                
            res = query_timetable_tool(day=day)
            day_data = res["schedule"][0]
            
            lines = [f"**Academic Timetable for {day_data['section']} ({day_data['day']}):**\n"]
            for slot in day_data["schedule"]:
                lines.append(f"• **{slot['time']}**: {slot['course']} — *{slot['faculty']}* ({slot['hall']})")
                
            answer = "\n".join(lines)
            sources = [{
                "document": "official_timetable_sy_a.json",
                "page": 1,
                "score": 1.0,
                "preview": f"Timetable schedule for {day_data['day']}"
            }]
            return answer, sources, metadata

        elif intent == QueryIntent.FACULTY:
            STAGE_LATENCY_SECONDS.labels(stage="deterministic_faculty").observe(time.perf_counter() - t_start)
            TOOL_CALLS_TOTAL.labels(tool_name="faculty_lookup", status="success").inc()
            planner_metrics.successful_calls += 1
            metadata["deterministic"] = True
            
            res = query_faculty_tool(question)
            if res["status"] == "success":
                lines = ["**Faculty Directory Matches:**\n"]
                for f in res["matches"]:
                    lines.append(
                        f"• **{f['name']}** — {f['designation']} ({f['department']})\n"
                        f"  - **Courses**: {', '.join(f['courses'])}\n"
                        f"  - **Office**: {f['office']} | **Email**: {f['email']}\n"
                        f"  - **Office Hours**: {f['office_hours']}"
                    )
                answer = "\n\n".join(lines)
            else:
                answer = res["message"]
                
            sources = [{
                "document": "faculty_directory_2026.json",
                "page": 1,
                "score": 1.0,
                "preview": "Verified institutional faculty directory record"
            }]
            return answer, sources, metadata

        elif intent == QueryIntent.CALENDAR:
            STAGE_LATENCY_SECONDS.labels(stage="deterministic_calendar").observe(time.perf_counter() - t_start)
            TOOL_CALLS_TOTAL.labels(tool_name="calendar_lookup", status="success").inc()
            planner_metrics.successful_calls += 1
            metadata["deterministic"] = True
            
            cal = query_academic_calendar_tool()["calendar"]
            answer = (
                f"**Academic Calendar ({cal['current_semester']}):**\n\n"
                f"• **Classes Commencement**: {cal['commencement_of_classes']}\n"
                f"• **Continuous Internal Evaluation 1 (CIE 1)**: {cal['continuous_internal_evaluation_1']}\n"
                f"• **Continuous Internal Evaluation 2 (CIE 2)**: {cal['continuous_internal_evaluation_2']}\n"
                f"• **Last Instructional Day**: {cal['last_instruction_day']}\n"
                f"• **Semester End Examinations (SEE)**: {cal['semester_end_examinations']}\n"
                f"• **Declaration of Results**: {cal['declaration_of_results']}\n\n"
                f"**Key Regulation**: Minimum mandatory attendance is **{cal['mandatory_attendance_threshold']}**."
            )
            sources = [{
                "document": "academic_calendar_2026.json",
                "page": 1,
                "score": 1.0,
                "preview": f"Official academic calendar for {cal['current_semester']}"
            }]
            return answer, sources, metadata

        else:
            # RAG Knowledge Retrieval Pipeline
            TOOL_CALLS_TOTAL.labels(tool_name="rag_knowledge_retrieval", status="attempt").inc()
            answer, sources = await ask_campusgpt_rag(question)
            TOOL_CALLS_TOTAL.labels(tool_name="rag_knowledge_retrieval", status="success").inc()
            planner_metrics.successful_calls += 1
            return answer, sources, metadata

    except Exception as e:
        logger.error(f"Error executing planner tool '{intent}': {e}")
        TOOL_CALLS_TOTAL.labels(tool_name=intent, status="error").inc()
        raise

