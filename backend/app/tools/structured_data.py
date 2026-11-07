from typing import List, Dict, Any, Optional

# Structured deterministic data for timetable queries
TIMETABLE_DATABASE = [
    {
        "day": "Monday",
        "department": "Computer Science & Engineering",
        "semester": "Semester 4",
        "section": "SY-A",
        "schedule": [
            {"time": "09:00 AM - 10:30 AM", "course": "Data Structures & Algorithms", "hall": "Room 302, Tech Block", "faculty": "Dr. Sharma"},
            {"time": "10:45 AM - 12:15 PM", "course": "Database Management Systems", "hall": "CS Lab 2", "faculty": "Prof. Mehta"},
            {"time": "01:30 PM - 03:00 PM", "course": "Discrete Mathematics", "hall": "Room 204, Tech Block", "faculty": "Dr. Gupta"},
            {"time": "03:15 PM - 04:45 PM", "course": "Computer Networks Lab", "hall": "Networking Lab", "faculty": "Prof. Verma"}
        ]
    },
    {
        "day": "Tuesday",
        "department": "Computer Science & Engineering",
        "semester": "Semester 4",
        "section": "SY-A",
        "schedule": [
            {"time": "09:00 AM - 10:30 AM", "course": "Operating Systems", "hall": "Room 302, Tech Block", "faculty": "Prof. Verma"},
            {"time": "10:45 AM - 12:15 PM", "course": "Formal Language & Automata", "hall": "Room 304, Tech Block", "faculty": "Dr. Rao"},
            {"time": "01:30 PM - 04:30 PM", "course": "DBMS Laboratory Practice", "hall": "CS Lab 3", "faculty": "Prof. Mehta"}
        ]
    },
    {
        "day": "Wednesday",
        "department": "Computer Science & Engineering",
        "semester": "Semester 4",
        "section": "SY-A",
        "schedule": [
            {"time": "09:00 AM - 10:30 AM", "course": "Data Structures & Algorithms", "hall": "Room 302, Tech Block", "faculty": "Dr. Sharma"},
            {"time": "10:45 AM - 12:15 PM", "course": "Artificial Intelligence Fundamentals", "hall": "Auditorium Hall B", "faculty": "Dr. Sunita Rao"},
            {"time": "01:30 PM - 03:00 PM", "course": "Object-Oriented Programming (Java)", "hall": "Software Lab 1", "faculty": "Prof. Kulkarni"}
        ]
    },
    {
        "day": "Thursday",
        "department": "Computer Science & Engineering",
        "semester": "Semester 4",
        "section": "SY-A",
        "schedule": [
            {"time": "09:00 AM - 10:30 AM", "course": "Computer Networks", "hall": "Room 302, Tech Block", "faculty": "Prof. Verma"},
            {"time": "10:45 AM - 12:15 PM", "course": "Database Management Systems", "hall": "Room 302, Tech Block", "faculty": "Prof. Mehta"},
            {"time": "01:30 PM - 04:30 PM", "course": "DSA Laboratory Session", "hall": "Computing Center Lab 1", "faculty": "Dr. Sharma"}
        ]
    },
    {
        "day": "Friday",
        "department": "Computer Science & Engineering",
        "semester": "Semester 4",
        "section": "SY-A",
        "schedule": [
            {"time": "09:00 AM - 10:30 AM", "course": "Software Engineering Methodologies", "hall": "Room 201, Tech Block", "faculty": "Dr. Sunita Rao"},
            {"time": "10:45 AM - 12:15 PM", "course": "Operating Systems", "hall": "Room 302, Tech Block", "faculty": "Prof. Verma"},
            {"time": "02:00 PM - 04:00 PM", "course": "Technical Seminar & Project Mentorship", "hall": "Seminar Hall A", "faculty": "Faculty Mentors"}
        ]
    }
]

# Structured Faculty Directory
FACULTY_DIRECTORY = [
    {
        "name": "Dr. Rajesh Sharma",
        "designation": "Head of Department & Professor",
        "department": "Computer Science & Engineering",
        "courses": ["Data Structures & Algorithms", "Advanced Algorithms"],
        "office": "Room 401, Tech Block",
        "email": "rajesh.sharma@campus.edu",
        "office_hours": "Monday & Wednesday, 02:00 PM - 04:00 PM"
    },
    {
        "name": "Dr. Sunita Rao",
        "designation": "Associate Professor",
        "department": "Artificial Intelligence & Data Science",
        "courses": ["Artificial Intelligence", "Deep Learning", "Software Engineering"],
        "office": "Room 405, Tech Block",
        "email": "sunita.rao@campus.edu",
        "office_hours": "Tuesday & Thursday, 11:00 AM - 01:00 PM"
    },
    {
        "name": "Prof. Amit Mehta",
        "designation": "Assistant Professor",
        "department": "Computer Science & Engineering",
        "courses": ["Database Management Systems", "Distributed Databases"],
        "office": "Room 312, Tech Block",
        "email": "amit.mehta@campus.edu",
        "office_hours": "Wednesday & Friday, 03:00 PM - 05:00 PM"
    },
    {
        "name": "Prof. Neha Verma",
        "designation": "Assistant Professor",
        "department": "Computer Science & Networks",
        "courses": ["Operating Systems", "Computer Networks", "Cybersecurity"],
        "office": "Room 314, Tech Block",
        "email": "neha.verma@campus.edu",
        "office_hours": "Monday & Thursday, 01:00 PM - 02:30 PM"
    }
]

# Structured Academic Calendar & Regulations
ACADEMIC_CALENDAR = {
    "current_semester": "Spring / Even Semester 2026",
    "commencement_of_classes": "January 12, 2026",
    "continuous_internal_evaluation_1": "March 2 - March 7, 2026",
    "continuous_internal_evaluation_2": "April 13 - April 18, 2026",
    "last_instruction_day": "May 8, 2026",
    "semester_end_examinations": "May 18 - June 5, 2026",
    "declaration_of_results": "June 25, 2026",
    "mandatory_attendance_threshold": "75%",
    "minimum_passing_grade": "40% in SEE and 40% in aggregate (Grade P)",
    "cie_weightage": "40%",
    "see_weightage": "60%"
}

def query_timetable_tool(day: Optional[str] = None, section: Optional[str] = "SY-A") -> Dict[str, Any]:
    day_match = (day or "").strip().lower()
    results = []
    
    for entry in TIMETABLE_DATABASE:
        if not day_match or day_match in entry["day"].lower() or ("today" in day_match):
            results.append(entry)
            
    if not results:
        # Default fallback to Monday schedule if specific day is not recognized
        results = [TIMETABLE_DATABASE[0]]
        
    return {
        "status": "success",
        "tool": "timetable_lookup",
        "matched_days": [r["day"] for r in results],
        "schedule": results,
    }

def query_faculty_tool(faculty_name_or_subject: str) -> Dict[str, Any]:
    query_str = faculty_name_or_subject.strip().lower()
    matches = []
    
    for f in FACULTY_DIRECTORY:
        name_match = query_str in f["name"].lower()
        dept_match = query_str in f["department"].lower()
        course_match = any(query_str in c.lower() for c in f["courses"])
        
        if name_match or dept_match or course_match:
            matches.append(f)
            
    if not matches:
        return {
            "status": "not_found",
            "tool": "faculty_lookup",
            "message": f"No faculty record found matching query: '{faculty_name_or_subject}'.",
            "matches": []
        }
        
    return {
        "status": "success",
        "tool": "faculty_lookup",
        "count": len(matches),
        "matches": matches
    }

def query_academic_calendar_tool(topic: Optional[str] = None) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": "academic_calendar_lookup",
        "calendar": ACADEMIC_CALENDAR
    }

