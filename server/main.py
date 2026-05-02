from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import re
from dotenv import load_dotenv

load_dotenv()

from core.darpan import run_darpan
from core.simulator import run_simulator
from core.margdarshak import run_margdarshak
from core.aawaz import run_aawaz_transcribe, run_aawaz_chat, is_ready_for_darpan
from core.memory import (
    load_student,
    load_by_username,
    save_student,
    create_new_profile,
    add_message,
    get_last_n_messages,
    username_exists,
    verify_pin,
    hash_pin,
)
from core.language import detect_language
from core.careers import get_careers_for_identity

app = FastAPI(title="Bhavishya API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Username validation

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


def validate_username(username: str):
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-20 characters, letters/numbers/underscore only.",
        )


def validate_pin(pin: str):
    if not pin.isdigit() or len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits.")


# Request models


class RegisterRequest(BaseModel):
    username: str
    pin: str  # 4 digits
    name: str  # display name
    grade: int


class LoginRequest(BaseModel):
    username: str
    pin: str


class OnboardRequest(BaseModel):
    name: str
    grade: int
    uid: str


class SessionRequest(BaseModel):
    name: str
    grade: int
    student_input: str
    uid: str


class ChatRequest(BaseModel):
    name: str
    grade: int
    question: str
    uid: str


class SimulateRequest(BaseModel):
    name: str
    grade: int
    uid: str


class AawazTranscribeRequest(BaseModel):
    name: str
    grade: int
    uid: str
    audio_b64: Optional[str] = None
    audio_mime: Optional[str] = "audio/webm"
    image_b64: Optional[str] = None
    image_mime: Optional[str] = "image/jpeg"
    text_fallback: Optional[str] = None


class AawazChatRequest(BaseModel):
    name: str
    grade: int
    uid: str
    message: str
    language: Optional[str] = "hinglish"


# Health


@app.get("/health")
def health():
    return {"status": "ok", "model": os.getenv("BHAVISHYA_MODE", "cloud")}


# Auth: Register


@app.post("/register")
def register(req: RegisterRequest):
    validate_username(req.username)
    validate_pin(req.pin)

    if req.grade not in [9, 10, 11, 12]:
        raise HTTPException(status_code=400, detail="Grade must be 9, 10, 11, or 12.")

    if username_exists(req.username):
        raise HTTPException(
            status_code=409, detail="Username already taken. Try another."
        )

    profile = create_new_profile(
        name=req.name.strip(),
        grade=req.grade,
        uid=req.username.lower(),
        username=req.username.lower(),
        pin=req.pin,
    )
    save_student(profile)

    return {
        "username": profile["username"],
        "name": profile["name"],
        "grade": profile["grade"],
        "uid": profile["uid"],
        "is_returning": False,
        "session_count": 0,
        "has_identity": False,
        "has_futures": False,
    }


# Auth: Login


@app.post("/login")
def login(req: LoginRequest):
    validate_username(req.username)
    validate_pin(req.pin)

    profile = load_by_username(req.username)
    if not profile:
        raise HTTPException(status_code=404, detail="Username not found.")

    if not profile.get("pin_hash"):
        raise HTTPException(
            status_code=400,
            detail="This account has no PIN set. Use the legacy onboard flow.",
        )

    if not verify_pin(req.pin, profile["pin_hash"]):
        raise HTTPException(status_code=401, detail="Wrong PIN.")

    return {
        "username": profile["username"],
        "name": profile["name"],
        "grade": profile["grade"],
        "uid": profile["uid"],
        "is_returning": profile.get("session_count", 0) > 0,
        "session_count": profile.get("session_count", 0),
        "has_identity": bool(profile.get("identity_current")),
        "has_futures": bool(profile.get("futures_generated")),
    }

# Legacy Onboard (kept for backward compat)

@app.post("/onboard")
def onboard(req: OnboardRequest):
    profile = load_student(req.name, req.grade, req.uid)
    is_returning = profile is not None

    if not profile:
        profile = create_new_profile(req.name, req.grade, req.uid)
        save_student(profile)

    return {
        "is_returning": is_returning,
        "session_count": profile.get("session_count", 0),
        "has_identity": bool(profile.get("identity_current")),
        "has_futures": bool(profile.get("futures_generated")),
        "name": profile["name"],
        "grade": profile["grade"],
        "uid": req.uid,
    }

# Aawaz: transcribe

@app.post("/aawaz/transcribe")
def aawaz_transcribe(req: AawazTranscribeRequest):
    if not req.audio_b64 and not req.image_b64 and not req.text_fallback:
        raise HTTPException(status_code=400, detail="No input provided.")
    try:
        result = run_aawaz_transcribe(
            audio_b64=req.audio_b64,
            audio_mime=req.audio_mime or "audio/webm",
            image_b64=req.image_b64,
            image_mime=req.image_mime or "image/jpeg",
            text_fallback=req.text_fallback,
            grade=req.grade,
            name=req.name,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result

# Aawaz: chat

@app.post("/aawaz/chat")
def aawaz_chat(req: AawazChatRequest):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile:
        profile = create_new_profile(req.name, req.grade, req.uid)

    history = profile.get("aawaz_history", [])

    try:
        response = run_aawaz_chat(
            message=req.message,
            history=history,
            grade=req.grade,
            name=req.name,
            language=req.language or "hinglish",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    history.append({"role": "user", "content": req.message})
    history.append({"role": "aawaz", "content": response})
    profile["aawaz_history"] = history
    save_student(profile)

    ready = is_ready_for_darpan(history)
    combined_input = None
    if ready:
        user_msgs = [m["content"] for m in history if m["role"] == "user"]
        combined_input = "\n\n".join(user_msgs)

    return {
        "response": response,
        "ready_for_darpan": ready,
        "combined_input": combined_input,
        "exchange_count": len([m for m in history if m["role"] == "user"]),
    }

# Session

@app.post("/session")
def run_session(req: SessionRequest):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile:
        profile = create_new_profile(req.name, req.grade, req.uid)

    previous_identity = profile.get("identity_current") or None
    identity = run_darpan(req.student_input, req.grade, previous_identity)

    if "error" in identity:
        raise HTTPException(
            status_code=500, detail=f"Darpan failed: {identity['error']}"
        )

    profile["identity_current"] = identity
    profile["identity_history"].append(
        {"session": profile["session_count"] + 1, "snapshot": identity}
    )
    profile["session_count"] += 1
    profile = add_message(profile, "user", req.student_input)
    save_student(profile)

    return {
        "identity": identity,
        "session_count": profile["session_count"],
        "should_simulate": profile["session_count"] >= 2,
        "message": (
            "First session done. Come back soon."
            if profile["session_count"] == 1
            else "Back again. Let us see what changed."
        ),
    }

# Simulate

@app.post("/simulate")
def simulate(req: SimulateRequest):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile or not profile.get("identity_current"):
        raise HTTPException(
            status_code=400, detail="No identity found. Run /session first."
        )

    if profile.get("session_count", 0) < 2:
        raise HTTPException(
            status_code=400, detail="Futures only available after 2 sessions."
        )

    identity = profile["identity_current"]
    career_data = get_careers_for_identity(identity, n=5)
    futures = run_simulator(
        identity_json=identity,
        grade=profile["grade"],
        session_count=profile["session_count"],
        career_data=career_data,
    )

    if "error" in futures:
        raise HTTPException(
            status_code=500, detail=f"Simulator failed: {futures['error']}"
        )

    if "futures_generated" not in profile:
        profile["futures_generated"] = []
    profile["futures_generated"].append(
        {"session": profile["session_count"], "futures": futures.get("futures", [])}
    )
    save_student(profile)
    return futures

# Chat

@app.post("/chat")
def chat(req: ChatRequest):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile or not profile.get("identity_current"):
        raise HTTPException(
            status_code=400, detail="No identity found. Run /session first."
        )

    language = detect_language(req.question)
    history = get_last_n_messages(profile, n=5)
    response = run_margdarshak(
        question=req.question,
        identity_json=profile["identity_current"],
        history=history,
        language=language,
    )

    profile = add_message(profile, "user", req.question)
    profile = add_message(profile, "bhavishya", response)
    save_student(profile)

    return {"response": response, "language_detected": language}

# Profile

@app.get("/profile/{name}/{grade}/{uid}")
def get_profile(name: str, grade: int, uid: str):
    profile = load_student(name, grade, uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found.")
    return profile
