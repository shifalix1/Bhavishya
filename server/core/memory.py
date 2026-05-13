import json
import os
import bcrypt
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDENTS_DIR = os.path.join(BASE_DIR, "students/")


# ── Path helpers ──────────────────────────────────────────────────────────────


def _path_by_uid(name: str, grade: int, uid: str) -> str:
    return os.path.join(STUDENTS_DIR, f"{name.lower()}_class{grade}_{uid}.json")


def _path_by_username(username: str) -> str:
    return os.path.join(STUDENTS_DIR, f"u_{username.lower()}.json")


# ── PIN hashing (FIX #4: bcrypt replaces bare SHA-256) ───────────────────────


def hash_pin(pin: str) -> str:
    """Returns a bcrypt hash string. Includes salt automatically."""
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_pin(pin: str, pin_hash: str) -> bool:
    """Works with both new bcrypt hashes and old SHA-256 hashes (migration path)."""
    try:
        return bcrypt.checkpw(pin.encode(), pin_hash.encode())
    except Exception:
        # Legacy SHA-256 fallback so existing accounts don't break
        import hashlib

        return hashlib.sha256(pin.encode()).hexdigest() == pin_hash


# ── Username lookups ──────────────────────────────────────────────────────────


def username_exists(username: str) -> bool:
    return os.path.exists(_path_by_username(username))


def load_by_username(username: str):
    path = _path_by_username(username)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ── Legacy uid-based lookup ───────────────────────────────────────────────────


def load_student(name: str, grade: int, uid: str):
    profile = load_by_username(uid)
    if profile:
        return profile
    path = _path_by_uid(name, grade, uid)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ── Save ──────────────────────────────────────────────────────────────────────


def save_student(profile: dict):
    """Atomic write - temp file + os.replace prevents corruption on interrupt."""
    os.makedirs(STUDENTS_DIR, exist_ok=True)
    if profile.get("username"):
        path = _path_by_username(profile["username"])
    else:
        path = os.path.join(STUDENTS_DIR, f"{profile['student_id']}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


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
        "darpan_run": False,  # FIX #8: tracks whether Darpan has been called
        "identity_current": {},
        "identity_history": [],
        "futures_generated": [],
        "conversation_history": [],
        "aawaz_history": [],
        "language_preference": "hinglish",
        "micro_observations": [],
    }


# ── Conversation helpers ──────────────────────────────────────────────────────


def add_message(profile: dict, role: str, content: str) -> dict:
    if "conversation_history" not in profile:
        profile["conversation_history"] = []
    profile["conversation_history"].append(
        {"role": role, "content": content, "timestamp": str(datetime.now())}
    )
    return profile


def trim_conversation_history(profile: dict, limit: int = 50) -> dict:
    """FIX #9: keep only the last `limit` messages to prevent unbounded growth."""
    if "conversation_history" in profile:
        profile["conversation_history"] = profile["conversation_history"][-limit:]
    return profile


def get_last_n_messages(profile: dict, n: int = 5) -> list:
    """
    Returns last n messages from conversation_history.
    Also prepends a summary of aawaz onboarding history so Margdarshak
    has context from the very first conversation - the richest identity signal.
    """
    aawaz = profile.get("aawaz_history", [])
    aawaz_user_msgs = [m for m in aawaz if m.get("role") == "user"]

    result = []
    if aawaz_user_msgs:
        combined = " | ".join(m["content"] for m in aawaz_user_msgs[:6])
        result.append(
            {
                "role": "context",
                "content": f"[From onboarding conversation]: {combined}",
            }
        )

    if "conversation_history" in profile:
        recent = [
            {"role": m["role"], "content": m["content"]}
            for m in profile["conversation_history"]
        ][-n:]
        result.extend(recent)

    return result


# ── Identity delta - the longitudinal moat ────────────────────────────────────


def _semantic_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    stop = {
        "the",
        "a",
        "an",
        "is",
        "it",
        "they",
        "their",
        "and",
        "or",
        "not",
        "by",
        "of",
        "in",
        "to",
        "that",
        "this",
        "for",
        "on",
        "but",
        "with",
        "are",
        "was",
        "be",
        "have",
        "has",
        "from",
        "at",
        "as",
        "who",
    }

    def tokenize(s):
        return {
            w.strip(".,!?-").lower()
            for w in s.split()
            if w.lower() not in stop and len(w) > 2
        }

    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def get_identity_delta(old: dict, new: dict) -> dict:
    if not old or not new:
        return {"changed": [], "stable": [], "contradictions": []}

    changed = []
    stable = []
    contradictions = []

    scalar_fields = ["thinking_style", "energy_signature", "family_pressure_map"]
    for field in scalar_fields:
        old_val = old.get(field, "")
        new_val = new.get(field, "")
        if old_val and new_val:
            if _semantic_similarity(old_val, new_val) >= 0.35:
                stable.append({"field": field, "value": new_val})
            else:
                changed.append({"field": field, "old": old_val, "new": new_val})

    list_fields = ["core_values", "hidden_strengths", "active_fears"]
    for field in list_fields:
        old_items = set(x.lower() for x in old.get(field, []))
        new_items = set(x.lower() for x in new.get(field, []))
        if old_items and new_items:
            if old_items == new_items:
                stable.append({"field": field, "value": list(new.get(field, []))})
            else:
                added = new_items - old_items
                removed = old_items - new_items
                if added or removed:
                    changed.append(
                        {"field": field, "added": list(added), "removed": list(removed)}
                    )

    old_fears = set(x.lower() for x in old.get("active_fears", []))
    new_values = set(x.lower() for x in new.get("core_values", []))
    overlap = old_fears & new_values
    for item in overlap:
        contradictions.append(
            f"'{item}' was an active fear last session but appears as a core value now"
        )

    return {"changed": changed, "stable": stable, "contradictions": contradictions}


def get_identity_callback(profile: dict) -> str | None:
    history = profile.get("identity_history", [])
    if len(history) < 2:
        return None

    SIMILARITY_THRESHOLD = 0.35

    styles = [
        h["snapshot"].get("thinking_style", "")
        for h in history
        if h.get("snapshot", {}).get("thinking_style")
    ]
    if (
        len(styles) >= 2
        and _semantic_similarity(styles[0], styles[-1]) >= SIMILARITY_THRESHOLD
    ):
        return f"I remember this coming up before too: {styles[-1]}"

    energies = [
        h["snapshot"].get("energy_signature", "")
        for h in history
        if h.get("snapshot", {}).get("energy_signature")
    ]
    if (
        len(energies) >= 2
        and _semantic_similarity(energies[0], energies[-1]) >= SIMILARITY_THRESHOLD
    ):
        return f"This reminds me of something from when we first talked: {energies[-1]}"

    if len(history) >= 2:
        old_values = set(
            x.lower() for x in history[0].get("snapshot", {}).get("core_values", [])
        )
        new_values = set(
            x.lower() for x in history[-1].get("snapshot", {}).get("core_values", [])
        )
        stable_values = list(old_values & new_values)
        if stable_values:
            return f"You keep circling back to '{stable_values[0]}'. Every time."

    return None


# ── Micro-observation helpers ─────────────────────────────────────────────────


def add_micro_observation(profile: dict, observation: str) -> dict:
    if "micro_observations" not in profile:
        profile["micro_observations"] = []
    profile["micro_observations"].append(
        {
            "text": observation,
            "timestamp": str(datetime.now()),
            "session": profile.get("session_count", 0),
        }
    )
    profile["micro_observations"] = profile["micro_observations"][-20:]
    return profile


def get_latest_observation(profile: dict) -> str | None:
    obs = profile.get("micro_observations", [])
    if not obs:
        return None

    priority_keywords = [
        "keeps coming up",
        "not sure if you noticed",
        "saying a lot more",
        "something shifted",
        "almost saying something",
        "way you write changes",
        "family keeps coming",
    ]
    for keyword in priority_keywords:
        for o in reversed(obs):
            if keyword in o.get("text", "").lower():
                return o["text"]
    return obs[-1]["text"]
