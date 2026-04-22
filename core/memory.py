import json, os
from datetime import date

STUDENTS_DIR = "students/"


def load_student(name: str, grade: int):
    path = f"{STUDENTS_DIR}{name.lower()}_class{grade}.json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_student(profile: dict):
    os.makedirs(STUDENTS_DIR, exist_ok=True)
    path = f"{STUDENTS_DIR}{profile['student_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


def create_new_profile(name: str, grade: int) -> dict:
    return {
        "student_id": f"{name.lower()}_class{grade}",
        "name": name,
        "grade": grade,
        "created_at": str(date.today()),
        "last_session": str(date.today()),
        "session_count": 0,
        "identity_current": {},
        "identity_history": [],
        "futures_generated": [],
        "conversation_history": [],
        "language_preference": "hinglish",
    }
