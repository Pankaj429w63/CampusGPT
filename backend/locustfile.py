from locust import HttpUser, task, between
import random

SAMPLE_QUESTIONS = [
    "What is my timetable today?",
    "Show me the schedule for Wednesday",
    "Who is the professor teaching Database Management Systems?",
    "When are the semester end examinations?",
    "What are the attendance requirements?",
    "What is the passing grade criteria?"
]

class CampusGPTUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def ask_campusgpt(self):
        question = random.choice(SAMPLE_QUESTIONS)
        self.client.post("/ask", json={"question": question})

    @task(1)
    def check_health_and_readiness(self):
        self.client.get("/health")
        self.client.get("/ready")

    @task(1)
    def check_agents_status(self):
        self.client.get("/agents/status")

