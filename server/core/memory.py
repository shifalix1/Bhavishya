import json
import os
import hashlib
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDENTS_DIR = os.path.join(BASE_DIR, "students/")


# ── Path helpers ──────────────────────────────────────────────────────────────


def _path_by_uid(name: str, grade: int, uid: str) -> str:
    return os.path.join(STUDENTS_DIR, f"{name.lower()}_class{grade}_{uid}.json")


def _path_by_username(username: str) -> str:
    return os.path.join(STUDENTS_DIR, f"u_{username.lower()}.json")


# ── PIN hashing (sha256, no extra deps) ──────────────────────────────────────


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def verify_pin(pin: str, pin_hash: str) -> bool:
    return hash_pin(pin) == pin_hash


# ── Username lookups ──────────────────────────────────────────────────────────


def username_exists(username: str) -> bool:
    return os.path.exists(_path_by_username(username))


def load_by_username(username: str):
    path = _path_by_username(username)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ── Legacy uid-based lookup (kept so old sessions still work) ─────────────────


def load_student(name: str, grade: int, uid: str):
    # Try username path first (uid == username in new profiles)
    profile = load_by_username(uid)
    if profile:
        return profile
    # Fall back to old name_classN_uid.json path
    path = _path_by_uid(name, grade, uid)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ── Save ─────────────────────────────────────────────────────────────────────


def save_student(profile: dict):
    os.makedirs(STUDENTS_DIR, exist_ok=True)
    if profile.get("username"):
        path = _path_by_username(profile["username"])
    else:
        path = os.path.join(STUDENTS_DIR, f"{profile['student_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


# ── Create ────────────────────────────────────────────────────────────────────


def create_new_profile(
    name: str, grade: int, uid: str, username: str = None, pin: str = None
) -> dict:
    uname = (username or uid).lower()
    return {
        "student_id": f"u_{uname}",
        "username": uname,
        "pin_hash": hash_pin(pin) if pin else None,
        "name": name,
        "grade": grade,
        "uid": uname,
        "created_at": str(date.today()),
        "last_session": str(date.today()),
        "session_count": 0,
        "identity_current": {},
        "identity_history": [],
        "futures_generated": [],
        "conversation_history": [],
        "aawaz_history": [],
        "language_preference": "hinglish",
    }


# ── Conversation helpers ──────────────────────────────────────────────────────


def add_message(profile: dict, role: str, content: str) -> dict:
    if "conversation_history" not in profile:
        profile["conversation_history"] = []
    profile["conversation_history"].append(
        {"role": role, "content": content, "timestamp": str(datetime.now())}
    )
    return profile


def get_last_n_messages(profile: dict, n: int = 5) -> list:
    if "conversation_history" not in profile:
        return []
    return [
        {"role": m["role"], "content": m["content"]}
        for m in profile["conversation_history"]
    ][-n:]
