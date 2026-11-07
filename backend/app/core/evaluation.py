from typing import List, Dict, Any, Optional

# Benchmark evaluation dataset with queries, expected tool routing, and ground truth references
EVALUATION_DATASET: List[Dict[str, Any]] = [
    {
        "id": "tc-001",
        "query": "What is my timetable today?",
        "expected_tool": "timetable_lookup",
        "expected_keywords": ["Academic Timetable", "SY-A", "Data Structures"],
        "ground_truth": "Data Structures & Algorithms at 09:00 AM, Database Management Systems at 10:45 AM, Discrete Mathematics at 01:30 PM",
        "category": "timetable"
    },
    {
        "id": "tc-002",
        "query": "Who is the professor teaching Database Management Systems?",
        "expected_tool": "faculty_lookup",
        "expected_keywords": ["Prof. Amit Mehta", "Database Management Systems", "Room 312"],
        "ground_truth": "Prof. Amit Mehta teaches Database Management Systems",
        "category": "faculty"
    },
    {
        "id": "tc-003",
        "query": "Show me the semester academic calendar and exam dates",
        "expected_tool": "academic_calendar_lookup",
        "expected_keywords": ["Academic Calendar", "CIE 1", "Semester End Examinations"],
        "ground_truth": "Classes start January 12, 2026. SEE exams run May 18 - June 5, 2026",
        "category": "calendar"
    },
    {
        "id": "tc-004",
        "query": "What are the attendance requirements for appearing in final exams?",
        "expected_tool": "rag_knowledge_retrieval",
        "expected_keywords": ["75%", "attendance", "minimum"],
        "ground_truth": "75 percent minimum attendance is mandatory",
        "category": "rag"
    },
    {
        "id": "tc-005",
        "query": "What is the quantum teleportation policy of the university?",
        "expected_tool": "rag_knowledge_retrieval",
        "expected_keywords": ["do not contain", "insufficient"],
        "ground_truth": "The available university documents do not contain sufficient information",
        "category": "abstention"
    }
]

def calculate_mrr(retrieved_ids: List[str], target_id: str) -> float:
    for idx, item in enumerate(retrieved_ids):
        if target_id.lower() in item.lower():
            return 1.0 / (idx + 1)
    return 0.0

def calculate_precision_recall_at_k(retrieved: List[str], relevant: List[str], k: int = 3) -> Dict[str, float]:
    retrieved_k = retrieved[:k]
    if not retrieved_k:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0}
        
    hits = sum(1 for doc in retrieved_k if any(r.lower() in doc.lower() for r in relevant))
    precision = hits / len(retrieved_k)
    recall = hits / len(relevant) if relevant else 0.0
    
    return {
        "precision_at_k": round(precision, 4),
        "recall_at_k": round(recall, 4)
    }

def evaluate_abstention_accuracy(answer: str, is_unsupported_query: bool) -> bool:
    contains_abstention = any(
        phrase in answer.lower()
        for phrase in [
            "do not contain",
            "insufficient information",
            "no university document context",
            "not found"
        ]
    )
    return contains_abstention if is_unsupported_query else not contains_abstention

