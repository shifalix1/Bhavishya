import json
import os
import bcrypt
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDENTS_DIR = os.path.join(BASE_DIR, "students/")

COMPRESSION_THRESHOLD = 40
COMPRESS_COUNT = 20


# Path helpers


def _path_by_uid(name: str, grade: int, uid: str) -> str:
    return os.path.join(STUDENTS_DIR, f"{name.lower()}_class{grade}_{uid}.json")


def _path_by_username(username: str) -> str:
    return os.path.join(STUDENTS_DIR, f"u_{username.lower()}.json")


# PIN hashing


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode(), pin_hash.encode())
    except Exception:
        import hashlib

        return hashlib.sha256(pin.encode()).hexdigest() == pin_hash


# Username lookups


def username_exists(username: str) -> bool:
    return os.path.exists(_path_by_username(username))


def load_by_username(username: str):
    path = _path_by_username(username)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# Legacy uid-based lookup


def load_student(name: str, grade: int, uid: str):
    profile = load_by_username(uid)
    if profile:
        return profile
    path = _path_by_uid(name, grade, uid)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# Save (atomic)


def save_student(profile: dict):
    os.makedirs(STUDENTS_DIR, exist_ok=True)
    if profile.get("username"):
        path = _path_by_username(profile["username"])
    else:
        path = os.path.join(STUDENTS_DIR, f"{profile['student_id']}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# Create


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
        "darpan_run": False,
        "identity_current": {},
        "identity_history": [],
        "futures_generated": [],
        "conversation_history": [],
        "aawaz_history": [],
        "language_preference": "english",
        "micro_observations": [],
        "context_summary": "",
        "sessions": [],  # structured snapshots, built by save_session_snapshot()
        "margdarshak_history": [],
    }


# Conversation helpers


def add_message(profile: dict, role: str, content: str) -> dict:
    """
    FIX: stamp every message with session_index at write time.
    The old /history/{uid} divided aawaz_history by total_sessions —
    broken when session lengths differ. This stamp enables exact segmentation.
    """
    if "conversation_history" not in profile:
        profile["conversation_history"] = []
    profile["conversation_history"].append(
        {
            "role": role,
            "content": content,
            "timestamp": str(datetime.now()),
            "session_index": profile.get("session_count", 0),
        }
    )
    return profile


def trim_conversation_history(profile: dict, limit: int = 50) -> dict:
    if "conversation_history" in profile:
        profile["conversation_history"] = profile["conversation_history"][-limit:]
    return profile


def needs_compression(profile: dict) -> bool:
    return len(profile.get("conversation_history", [])) >= COMPRESSION_THRESHOLD


async def compress_history(profile: dict, summarizer_fn) -> dict:
    history = profile.get("conversation_history", [])
    if len(history) < COMPRESS_COUNT:
        return profile

    to_compress = history[:COMPRESS_COUNT]
    to_keep = history[COMPRESS_COUNT:]
    raw_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in to_compress)

    try:
        new_summary = await summarizer_fn(raw_text)
    except Exception:
        return profile

    existing_summary = profile.get("context_summary", "").strip()
    profile["context_summary"] = (
        existing_summary + " | " + new_summary.strip()
        if existing_summary
        else new_summary.strip()
    )
    profile["conversation_history"] = to_keep
    return profile


def get_last_n_messages(profile: dict, n: int = 5) -> list:
    result = []

    summary = profile.get("context_summary", "").strip()
    if summary:
        result.append(
            {
                "role": "context",
                "content": f"[Summary of earlier conversation]: {summary}",
            }
        )

    aawaz = profile.get("aawaz_history", [])
    aawaz_user_msgs = [m for m in aawaz if m.get("role") == "user"]
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


# Session snapshot


def save_session_snapshot(profile: dict) -> dict:
    """
    Persist a complete, self-contained session object into profile["sessions"].
    Call this after Darpan runs (in /session route) and again after
    Margdarshak answers (in /margdarshak/question route) to keep snapshot fresh.
    Overwrites the existing snapshot for this session_count — never duplicates.

    Shape consumed by Sidebar.jsx SessionDrawer:
    {
      "session_index": N,
      "session": N,
      "date": "2026-05-10",
      "aawaz_turns": [{"role": ..., "content": ...}, ...],
      "identity": { darpan fingerprint },
      "margdarshak": [{"question": ..., "answer": ...}, ...],
      "futures": [{"type": ..., "title": ...}, ...],
      "identity_delta": {"changed": [], "stable": [], "contradictions": []},
      "confidence_arc": [prev_conf, curr_conf],
      "context_summary": "...",
    }
    """
    if "sessions" not in profile:
        profile["sessions"] = []

    session_num = profile.get("session_count", 0)

    # Aawaz turns for this session
    all_aawaz = profile.get("aawaz_history", [])
    session_aawaz = [
        m
        for m in all_aawaz
        if m.get("session_index", 1) == session_num
        # Legacy: messages without session_index stamp belong to session 1
        or (session_num == 1 and "session_index" not in m)
    ]

    # Margdarshak Q&A for this session
    marg_history = profile.get("margdarshak_history", [])
    marg_qa = [
        {"question": m.get("question", ""), "answer": m.get("answer", "")}
        for m in marg_history
        if m.get("session") == session_num
    ]

    # Identity delta vs the previous completed snapshot
    prev_snap = profile["sessions"][-1] if profile["sessions"] else None
    # Don't diff against ourselves if snapshot already exists for this session
    if prev_snap and prev_snap.get("session") == session_num:
        prev_snap = profile["sessions"][-2] if len(profile["sessions"]) >= 2 else None
    prev_identity = prev_snap.get("identity") if prev_snap else None
    curr_identity = profile.get("identity_current") or {}
    identity_delta = get_identity_delta(prev_identity, curr_identity)

    prev_conf = (prev_identity or {}).get("identity_confidence", 0)
    curr_conf = curr_identity.get("identity_confidence", 0)

    # Futures generated this session
    all_futures = profile.get("futures_generated", [])
    session_futures = []
    for entry in all_futures:
        if entry.get("session") == session_num:
            for fut in entry.get("futures", []):
                session_futures.append(
                    {
                        "type": fut.get("path_type", fut.get("type", "")),
                        "title": fut.get("title", ""),
                    }
                )

    snapshot = {
        "session_index": session_num,
        "session": session_num,
        "date": str(date.today()),
        "aawaz_turns": [
            {"role": m["role"], "content": m["content"]} for m in session_aawaz
        ],
        "identity": curr_identity if curr_identity else None,
        "margdarshak": marg_qa,
        "futures": session_futures,
        "identity_delta": identity_delta,
        "confidence_arc": [prev_conf, curr_conf],
        "context_summary": profile.get("context_summary", ""),
    }

    existing_idx = next(
        (
            i
            for i, s in enumerate(profile["sessions"])
            if s.get("session") == session_num
        ),
        None,
    )
    if existing_idx is not None:
        profile["sessions"][existing_idx] = snapshot
    else:
        profile["sessions"].append(snapshot)

    return profile


# Structured history for /history/{uid}


def get_sessions_structured(profile: dict) -> dict:
    """
    FIX: replaces the broken aawaz_history division logic in /history/{uid}.

    If profile["sessions"] has data (populated by save_session_snapshot),
    returns it directly — fast path for all new sessions.

    Falls back to reconstructing from session_index-stamped history for
    profiles created before this fix (no data loss on upgrade).
    """
    stored_sessions = profile.get("sessions", [])
    if stored_sessions:
        return {
            "sessions": sorted(stored_sessions, key=lambda s: s.get("session", 0)),
            "session_count": profile.get("session_count", 0),
            "identity_current": profile.get("identity_current", {}),
        }

    # ── Legacy fallback: reconstruct from stamps ──────────────────────────────
    session_count = profile.get("session_count", 0)
    if session_count == 0:
        return {"sessions": [], "session_count": 0, "identity_current": {}}

    aawaz_buckets: dict[int, list] = {}
    for m in profile.get("aawaz_history", []):
        idx = m.get("session_index", 1)
        aawaz_buckets.setdefault(idx, []).append(m)

    identity_history = profile.get("identity_history", [])
    identity_current = profile.get("identity_current", {})
    marg_history = profile.get("margdarshak_history", [])

    sessions = []
    for snum in range(1, session_count + 1):
        aawaz = aawaz_buckets.get(snum, [])

        snap_identity = (
            identity_current
            if snum == session_count
            else next(
                (
                    h.get("snapshot")
                    for h in identity_history
                    if h.get("session") == snum
                ),
                None,
            )
        )

        marg_qa = [
            {"question": m.get("question", ""), "answer": m.get("answer", "")}
            for m in marg_history
            if m.get("session") == snum
        ]

        futures_raw = [
            f for f in profile.get("futures_generated", []) if f.get("session") == snum
        ]
        futures = [
            {
                "type": fut.get("path_type", fut.get("type", "")),
                "title": fut.get("title", ""),
            }
            for entry in futures_raw
            for fut in entry.get("futures", [])
        ]

        prev_identity = (
            next(
                (
                    h.get("snapshot")
                    for h in identity_history
                    if h.get("session") == snum - 1
                ),
                None,
            )
            if snum > 1
            else None
        )

        prev_conf = (prev_identity or {}).get("identity_confidence", 0)
        curr_conf = (snap_identity or {}).get("identity_confidence", 0)

        sessions.append(
            {
                "session_index": snum,
                "session": snum,
                "date": (
                    profile.get("last_session", str(date.today()))
                    if snum == session_count
                    else ""
                ),
                "aawaz_turns": [
                    {"role": m["role"], "content": m["content"]} for m in aawaz
                ],
                "identity": snap_identity,
                "margdarshak": marg_qa,
                "futures": futures,
                "identity_delta": get_identity_delta(prev_identity, snap_identity),
                "confidence_arc": [prev_conf, curr_conf],
                "context_summary": (
                    profile.get("context_summary", "") if snum == session_count else ""
                ),
            }
        )

    return {
        "sessions": sessions,
        "session_count": session_count,
        "identity_current": identity_current,
    }


# Identity delta and callback helpers


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

    changed, stable, contradictions = [], [], []

    for field in ["thinking_style", "energy_signature", "family_pressure_map"]:
        old_val = old.get(field, "")
        new_val = new.get(field, "")
        if old_val and new_val:
            if _semantic_similarity(old_val, new_val) >= 0.35:
                stable.append({"field": field, "value": new_val})
            else:
                changed.append({"field": field, "old": old_val, "new": new_val})

    for field in ["core_values", "hidden_strengths", "active_fears"]:
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
    for item in old_fears & new_values:
        contradictions.append(
            f"'{item}' was an active fear last session but appears as a core value now"
        )

    return {"changed": changed, "stable": stable, "contradictions": contradictions}


def get_identity_callback(profile: dict) -> str | None:
    history = profile.get("identity_history", [])
    if len(history) < 2:
        return None

    THRESHOLD = 0.35

    styles = [
        h["snapshot"].get("thinking_style", "")
        for h in history
        if h.get("snapshot", {}).get("thinking_style")
    ]
    if len(styles) >= 2 and _semantic_similarity(styles[0], styles[-1]) >= THRESHOLD:
        return f"I remember this coming up before too: {styles[-1]}"

    energies = [
        h["snapshot"].get("energy_signature", "")
        for h in history
        if h.get("snapshot", {}).get("energy_signature")
    ]
    if (
        len(energies) >= 2
        and _semantic_similarity(energies[0], energies[-1]) >= THRESHOLD
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


# Micro-observation helpers


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
