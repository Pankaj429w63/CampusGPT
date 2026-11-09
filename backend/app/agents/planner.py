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

    # 1. Timetable pattern heuristics
    if any(k in q for k in ["timetable", "schedule", "classes", "lecture", "routine", "free period", "free slot", "next class"]):
        # Disambiguate pure faculty directory requests like "List AIML faculty members"
        if not ("list" in q and "faculty" in q):
            return QueryIntent.TIMETABLE

    # 2. Check for timetable context: section, batch, lab, subject code, or faculty room allocation
    from app.timetable.service import timetable_service
    tt_data = timetable_service.get_data()
    has_class = timetable_service.normalize_sheet_alias(query) is not None
    has_batch = bool(re.search(r"\b([a-c][1-3]|ml[1-4])\b", q))
    has_lab = "lab" in q
    has_room_q = any(k in q for k in ["which room", "where is", "room number", "what room", "which lab", "where does", "room does"])
    
    words = [w.strip("?,.()[]") for w in query.split()]
    has_known_fac = any(w.upper() in tt_data.faculty_lookup for w in words)
    has_known_sub = any(w.upper() in tt_data.subject_lookup for w in words)

    # Where is the lab or room for a class/batch: "Where is the SY-A A1 lab?"
    if has_room_q and (has_class or has_batch or has_lab or has_known_fac):
        return QueryIntent.TIMETABLE

    # Who teaches a subject in a specific section: "Who teaches SML in SY-A?"
    if any(k in q for k in ["who teaches", "who is teaching", "teaches in", "teach in", "teacher for"]) and (has_class or has_known_sub):
        return QueryIntent.TIMETABLE

    # Room where faculty teaches: "Which room does PVK teach in?"
    if has_room_q and has_known_fac:
        return QueryIntent.TIMETABLE

    # Class timetable request: "Show Monday timetable for TY-B" or "classes for SY-A"
    if has_class and any(k in q for k in ["class", "classes", "timetable", "routine", "schedule", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]):
        return QueryIntent.TIMETABLE

    # 3. Faculty pattern heuristics
    if any(k in q for k in ["faculty", "professor", "who teaches", "hod", "office hour", "dr.", "prof."]):
        return QueryIntent.FACULTY

    # 4. Calendar & General Regulations
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
            
            # Use real structured timetable service
            from app.timetable.service import timetable_service
            tt_data = timetable_service.get_data()
            q_lower = question.lower()
            
            # 1. Determine sheet name from query
            detected_sheet = timetable_service.normalize_sheet_alias(question)
            
            # Check for ambiguity if query asks for a section/batch schedule without specifying which one
            if any(k in q_lower for k in ["my timetable", "the timetable", "show schedule"]) and not detected_sheet and not any(k in q_lower for k in ["sy", "ty", "b.tech", "m.tech", "all"]):
                answer = (
                    "Please specify which class section you would like the timetable for "
                    "(e.g., **SY-A**, **SY-B**, **SY-C**, **TY-A**, **TY-B**, **TY-C**, **B.Tech-A**, **B.Tech-B**, **M.Tech-FY**, or **M.Tech-SY**)."
                )
                sources = [{
                    "document": "Master TT-26-27-ODD Sem.xlsx",
                    "page": 1,
                    "score": 1.0,
                    "preview": "Class section ambiguity prompt"
                }]
                return answer, sources, metadata

            target_sheet = detected_sheet or "SY-A"

            # 2. Check for faculty room query: e.g. "Which room does PVK teach in?"
            words = [w.strip("?,.()[]") for w in question.split()]
            matching_fac = [w.upper() for w in words if w.upper() in tt_data.faculty_lookup]
            if matching_fac and any(k in q_lower for k in ["which room", "what room", "where", "room does"]):
                fac_code = matching_fac[0]
                fac_name = tt_data.faculty_lookup[fac_code]
                entries = timetable_service.search_by_faculty(fac_code)
                if entries:
                    lines = [f"**Classroom & Lab Allocations for {fac_name} ({fac_code}):**\n"]
                    seen_rooms = set()
                    for e in entries:
                        key = (e.class_name, e.subject_code, e.room_name or e.room_code, e.day)
                        if key not in seen_rooms:
                            seen_rooms.add(key)
                            b_str = f" [Batch {e.batch}]" if e.batch and e.batch != "All" else ""
                            lines.append(f"• **{e.day}** ({e.time_slot}): **{e.class_name}** — {e.subject_name or e.subject_code}{b_str} in **{e.room_name or e.room_code}**")
                    answer = "\n".join(lines)
                else:
                    answer = f"No active classroom sessions found in the timetable for {fac_name} ({fac_code})."
                sources = [{
                    "document": "Master TT-26-27-ODD Sem.xlsx",
                    "page": 1,
                    "score": 1.0,
                    "preview": f"Faculty room allocation lookup for {fac_code}"
                }]
                return answer, sources, metadata

            # 3. Check for specific lab / batch location: e.g. "Where is the SY-A A1 lab?"
            batch_m = re.search(r"\b([a-c][1-3]|ml[1-4])\b", q_lower)
            if ("where is" in q_lower or "which room" in q_lower or "location" in q_lower) and (batch_m or "lab" in q_lower):
                target_batch = batch_m.group(1).upper() if batch_m else None
                entries = timetable_service.get_class_timetable(target_sheet, batch=target_batch)
                lab_entries = [e for e in entries if e.is_lab]
                if lab_entries:
                    lines = [f"**Laboratory Room Allocations for {target_sheet}" + (f" Batch {target_batch}" if target_batch else "") + ":**\n"]
                    for le in lab_entries:
                        b_str = f" [Batch {le.batch}]" if le.batch else ""
                        fac_str = f" with {le.faculty_name or le.faculty_initials}" if (le.faculty_name or le.faculty_initials) else ""
                        lines.append(f"• **{le.day}** ({le.time_slot}): **{le.subject_name or le.subject_code}**{b_str}{fac_str} &rarr; **{le.room_name or le.room_code}**")
                    answer = "\n".join(lines)
                else:
                    answer = f"No lab room allocations found for {target_sheet}."
                sources = [{
                    "document": "Master TT-26-27-ODD Sem.xlsx",
                    "page": 1,
                    "score": 1.0,
                    "preview": f"Lab room allocation for {target_sheet}"
                }]
                return answer, sources, metadata

            # 4. Check for course instructor in class: e.g. "Who teaches SML in SY-A?"
            matching_sub = [w.upper() for w in words if w.upper() in tt_data.subject_lookup]
            if (any(k in q_lower for k in ["who teaches", "who is teaching", "faculty for", "teacher for"]) or matching_sub) and matching_sub:
                sub_code = matching_sub[0]
                sub_name = tt_data.subject_lookup[sub_code]
                entries = [e for e in timetable_service.get_class_timetable(target_sheet) if e.subject_code.upper() == sub_code or (e.subject_name and sub_code in e.subject_name.upper())]
                if entries:
                    faculty_roles = {}
                    for e in entries:
                        fac = e.faculty_name or e.faculty_initials
                        if not fac:
                            continue
                        role = "Lab" if e.is_lab else ("Tutorial" if e.is_tutorial else "Theory")
                        if fac not in faculty_roles:
                            faculty_roles[fac] = set()
                        faculty_roles[fac].add(f"{role} (Batch {e.batch})" if e.batch and e.batch != "All" else role)
                    
                    lines = [f"**Course Faculty for {sub_name} ({sub_code}) in {target_sheet}:**\n"]
                    for fac, roles in faculty_roles.items():
                        lines.append(f"• **{fac}**: {', '.join(sorted(roles))}")
                    answer = "\n".join(lines)
                else:
                    answer = f"No scheduled slots found for {sub_name} ({sub_code}) in {target_sheet}."
                sources = [{
                    "document": "Master TT-26-27-ODD Sem.xlsx",
                    "page": 1,
                    "score": 1.0,
                    "preview": f"Course faculty allocation for {sub_code} in {target_sheet}"
                }]
                return answer, sources, metadata

            # 5. Check for free period queries
            if any(k in question.lower() for k in ["free period", "free slot", "empty slot", "when is free", "free time"]):
                free_slots = timetable_service.get_free_periods(target_sheet)
                if not free_slots:
                    answer = f"There are no free periods found for **{target_sheet}**."
                else:
                    lines = [f"**Free Periods for {target_sheet}:**\n"]
                    for fs in free_slots:
                        if "slot" in fs and "message" in fs:
                            lines.append(f"• {fs['message']}")
                        else:
                            lines.append(f"• Slot {fs.get('slot_index')}: **{fs.get('time_slot')}** ({fs.get('day')})")
                    answer = "\n".join(lines)
                sources = [{
                    "document": "Master TT-26-27-ODD Sem.xlsx",
                    "page": 1,
                    "score": 1.0,
                    "preview": f"Free period analysis for sheet {target_sheet}"
                }]
                return answer, sources, metadata

            # 6. Check for next class queries
            if any(k in question.lower() for k in ["next class", "current class", "upcoming class", "what class is now"]):
                next_info = timetable_service.get_next_class(target_sheet)
                curr = next_info.get("current_class")
                nxt = next_info.get("next_class")
                lines = [f"**Class Status for {target_sheet}:**\n", f"• {next_info.get('message', '')}"]
                if curr:
                    lines.append(f"  - Current: **{curr.subject_name or curr.subject_code}** ({curr.time_slot}) in Room **{curr.room_name or curr.room_code or 'TBD'}**")
                if nxt:
                    lines.append(f"  - Upcoming: **{nxt.subject_name or nxt.subject_code}** ({nxt.time_slot}) in Room **{nxt.room_name or nxt.room_code or 'TBD'}**")
                answer = "\n".join(lines)
                sources = [{
                    "document": "Master TT-26-27-ODD Sem.xlsx",
                    "page": 1,
                    "score": 1.0,
                    "preview": f"Next class schedule tracking for {target_sheet}"
                }]
                return answer, sources, metadata

            # 7. Check for room lookup in timetable
            room_m = re.search(r"\b(room|lab|classroom)\s*([A-Za-z0-9]+)\b", question.lower())
            if room_m and not any(k in question.lower() for k in ["sy", "ty", "b.tech", "schedule", "today"]):
                room_q = room_m.group(2)
                room_entries = timetable_service.search_by_room(room_q)
                if room_entries:
                    lines = [f"**Timetable Allocation for Room {room_q.upper()}:**\n"]
                    for re_e in room_entries[:8]:
                        lines.append(f"• **{re_e.day}** ({re_e.time_slot}): {re_e.class_name} — {re_e.subject_name or re_e.subject_code} ({re_e.faculty_name or re_e.faculty_initials or 'TBD'})")
                    answer = "\n".join(lines)
                    sources = [{
                        "document": "Master TT-26-27-ODD Sem.xlsx",
                        "page": 1,
                        "score": 1.0,
                        "preview": f"Room schedule allocation for {room_q}"
                    }]
                    return answer, sources, metadata

            # 8. Check if today's timetable is requested
            if "today" in question.lower():
                today_res = timetable_service.get_today_timetable(target_sheet)
                if today_res.get("is_holiday"):
                    answer = f"**{target_sheet} Schedule:** {today_res.get('message')}"
                else:
                    lines = [f"**Today's Timetable for {target_sheet} ({today_res['day']}):**\n"]
                    for e in today_res["entries"]:
                        if e.is_break:
                            lines.append(f"• **{e.time_slot}**: *{e.subject_name}*")
                        elif e.is_activity:
                            lines.append(f"• **{e.time_slot}**: {e.subject_name}")
                        else:
                            batch_str = f" [Batch {e.batch}]" if e.batch and e.batch != "All" else ""
                            fac_str = f" — *{e.faculty_name or e.faculty_initials}*" if (e.faculty_name or e.faculty_initials) else ""
                            rm_str = f" ({e.room_name or e.room_code})" if (e.room_name or e.room_code) else ""
                            lines.append(f"• **{e.time_slot}**: **{e.subject_name or e.subject_code}**{batch_str}{fac_str}{rm_str}")
                    answer = "\n".join(lines)
                sources = [{
                    "document": "Master TT-26-27-ODD Sem.xlsx",
                    "page": 1,
                    "score": 1.0,
                    "preview": f"Today's schedule for {target_sheet}"
                }]
                return answer, sources, metadata

            # 9. Specific day or full weekly timetable
            day = None
            for d in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]:
                if d in question.lower():
                    day = d.capitalize()
                    break

            entries = timetable_service.get_class_timetable(target_sheet, day=day)
            if not entries:
                answer = f"No timetable entries found for **{target_sheet}**" + (f" on **{day}**." if day else ".")
            else:
                day_header = f" for {day}" if day else " Weekly Schedule"
                lines = [f"**Academic Timetable for {target_sheet}{day_header}:**\n"]
                current_d = None
                for e in entries:
                    if not day and e.day != current_d:
                        current_d = e.day
                        lines.append(f"\n### {current_d}")
                    if e.is_break:
                        lines.append(f"• **{e.time_slot}**: *{e.subject_name}*")
                    elif e.is_activity:
                        lines.append(f"• **{e.time_slot}**: {e.subject_name}")
                    else:
                        batch_str = f" [Batch {e.batch}]" if e.batch and e.batch != "All" else ""
                        fac_str = f" — *{e.faculty_name or e.faculty_initials}*" if (e.faculty_name or e.faculty_initials) else ""
                        rm_str = f" ({e.room_name or e.room_code})" if (e.room_name or e.room_code) else ""
                        lines.append(f"• **{e.time_slot}**: **{e.subject_name or e.subject_code}**{batch_str}{fac_str}{rm_str}")
                answer = "\n".join(lines)

            sources = [{
                "document": "Master TT-26-27-ODD Sem.xlsx",
                "page": 1,
                "score": 1.0,
                "preview": f"Official Master Timetable record for {target_sheet}"
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
                sources = [{
                    "document": "faculty_directory_2026.json",
                    "page": 1,
                    "score": 1.0,
                    "preview": "Verified institutional faculty directory record"
                }]
                return answer, sources, metadata
            else:
                # If no match in the mock/structured directory, fall back to the institutional RAG knowledge base
                metadata["deterministic"] = False
                metadata["selected_tool"] = QueryIntent.RAG_KNOWLEDGE
                TOOL_CALLS_TOTAL.labels(tool_name="rag_knowledge_retrieval", status="attempt").inc()
                answer, sources = await ask_campusgpt_rag(question)
                TOOL_CALLS_TOTAL.labels(tool_name="rag_knowledge_retrieval", status="success").inc()
                return answer, sources, metadata

        elif intent == QueryIntent.CALENDAR:
            STAGE_LATENCY_SECONDS.labels(stage="deterministic_calendar").observe(time.perf_counter() - t_start)
            TOOL_CALLS_TOTAL.labels(tool_name="calendar_lookup", status="success").inc()
            planner_metrics.successful_calls += 1
            metadata["deterministic"] = True
            
            cal = query_academic_calendar_tool()["calendar"]
            odd = cal["odd_semester"]
            even = cal["even_semester"]
            
            answer = (
                f"**Academic Calendar (Academic Year {cal['academic_year']}):**\n\n"
                f"### **{odd['term']}**\n"
                f"• **Induction & Session Commencement**: {odd['induction_registration']}\n"
                f"• **Teaching Commencement**: {odd['teaching_commencement']}\n"
                f"• **Open House**: {odd['open_house']}\n"
                f"• **Student Consultative Meeting**: {odd['student_consultative_meeting']}\n"
                f"• **Mid-Term Feedback**: {odd['mid_term_feedback']}\n"
                f"• **Unit Test**: {odd['unit_test']}\n"
                f"• **Techfest & Cultural Fest**: {odd['techfest_cultural_fest']}\n"
                f"• **Diwali Vacation**: {odd['diwali_vacation']}\n"
                f"• **Preparatory Leave**: {odd['preparatory_leave']}\n"
                f"• **End Semester Examination (ESE ODD 2026)**: {odd['end_semester_examination']}\n"
                f"• **Vacation**: {odd['vacation']}\n"
                f"• **Next Session Starts**: {odd['next_session_start']}\n\n"
                f"### **{even['term']}**\n"
                f"• **Registration & Session Commencement**: {even['registration_and_commencement']}\n"
                f"• **Open House**: {even['open_house']}\n"
                f"• **Student Consultative Meeting**: {even['student_consultative_meeting']}\n"
                f"• **Mid-Term Feedback**: {even['mid_term_feedback']}\n"
                f"• **Unit Test**: {even['unit_test']}\n"
                f"• **Industry Conclave**: {even['industry_conclave']}\n"
                f"• **Final Practical Exams & Project Exhibition**: {even['final_practical_exams']}\n"
                f"• **Backlog Exam / Prep Leave**: {even['backlog_exam_and_prep_leave']}\n"
                f"• **End Semester Examination (EVEN 2027)**: {even['end_semester_examination']}\n"
                f"• **Vacation / VAC**: {even['vacation_and_vac']}\n"
                f"• **Next Session Starts**: {even['next_session_start']}\n\n"
                f"**Academic Regulations & Attendance**:\n"
                f"• Mandatory attendance threshold: **{cal['mandatory_attendance_threshold']}**.\n"
                f"• Weightage: CIE **{cal['cie_weightage']}** | SEE **{cal['see_weightage']}**.\n"
                f"• Minimum passing grade: {cal['minimum_passing_grade']}."
            )
            sources = [{
                "document": "Academic_Calendar_2026-27.pdf.pdf",
                "page": 1,
                "score": 1.0,
                "preview": f"Official academic calendar for {cal['academic_year']} (ODD 2026 and EVEN 2027 Semesters)"
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

