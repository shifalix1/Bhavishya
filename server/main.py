import logging
import os
import re

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bhavishya.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("bhavishya")

from core.darpan import run_darpan
from core.simulator import run_simulator
from core.margdarshak import run_margdarshak
from core.aawaz import (
    run_aawaz_transcribe,
    run_aawaz_chat,
    is_ready_for_darpan,
    extract_micro_observations,
)
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
    add_micro_observation,
    get_latest_observation,
    get_identity_delta,
    get_identity_callback,
)
from core.language import detect_language
from core.careers import get_careers_for_identity

app = FastAPI(title="Bhavishya API", version="2.2.0")

# Read allowed origins from env for deployment flexibility.
# Falls back to localhost dev ports if not set.
_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


def validate_username(username: str) -> None:
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-20 characters: letters, numbers, or underscore only.",
        )


def validate_pin(pin: str) -> None:
    if not pin.isdigit() or len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits.")


def get_or_create_student(name: str, grade: int, uid: str) -> dict:
    profile = load_student(name, grade, uid)
    if not profile:
        profile = create_new_profile(name, grade, uid)
    return profile


# Request models


class RegisterRequest(BaseModel):
    username: str
    pin: str
    name: str
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
    language: Optional[str] = "english"
    # Anomalies extracted from an uploaded image by /aawaz/transcribe.
    # Frontend sends this once on the first chat turn after an image upload.
    # Backend persists it so subsequent turns don't need to re-send it.
    image_anomalies: Optional[str] = None


# Routers

auth_router = APIRouter(prefix="", tags=["auth"])
aawaz_router = APIRouter(prefix="/aawaz", tags=["aawaz"])
core_router = APIRouter(prefix="", tags=["core"])


@app.get("/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "model": os.getenv("BHAVISHYA_MODE", "cloud"),
        "version": "2.2.0",
    }


# Auth routes


@auth_router.post("/register")
async def register(req: RegisterRequest):
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
    logger.info(f"New student registered: {req.username} (grade {req.grade})")

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


@auth_router.post("/login")
async def login(req: LoginRequest):
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
        logger.warning(f"Failed login attempt for username: {req.username}")
        raise HTTPException(status_code=401, detail="Wrong PIN.")

    logger.info(f"Student logged in: {req.username}")
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


@auth_router.post("/onboard")
async def onboard(req: OnboardRequest):
    """Legacy onboard flow kept for backward compatibility."""
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


# Aawaz routes


@aawaz_router.post("/transcribe")
async def aawaz_transcribe(req: AawazTranscribeRequest):
    if not req.audio_b64 and not req.image_b64 and not req.text_fallback:
        raise HTTPException(status_code=400, detail="No input provided.")

    logger.info(
        f"[AAWAZ/TRANSCRIBE] {req.name} | "
        f"audio={'yes' if req.audio_b64 else 'no'} "
        f"image={'yes' if req.image_b64 else 'no'}"
    )

    try:
        result = await run_aawaz_transcribe(
            audio_b64=req.audio_b64,
            audio_mime=req.audio_mime or "audio/webm",
            image_b64=req.image_b64,
            image_mime=req.image_mime or "image/jpeg",
            text_fallback=req.text_fallback,
            grade=req.grade,
            name=req.name,
        )
    except RuntimeError as e:
        logger.error(f"[AAWAZ/TRANSCRIBE] RuntimeError: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return result


@aawaz_router.post("/chat")
async def aawaz_chat(req: AawazChatRequest):
    profile = get_or_create_student(req.name, req.grade, req.uid)
    history = profile.get("aawaz_history", [])

    logger.info(
        f"[AAWAZ/CHAT] {req.name} | "
        f"exchange #{len([m for m in history if m['role'] == 'user']) + 1} | "
        f"lang={req.language}"
    )

    # Use freshly sent anomalies if present, otherwise read from profile.
    # Frontend only needs to send image_anomalies once; we persist and replay it.
    image_anomalies = req.image_anomalies
    if image_anomalies:
        profile["image_anomalies"] = image_anomalies
    elif profile.get("image_anomalies"):
        image_anomalies = profile["image_anomalies"]

    try:
        response = await run_aawaz_chat(
            message=req.message,
            history=history,
            grade=req.grade,
            name=req.name,
            language=req.language or "hinglish",
            image_anomalies=image_anomalies,
        )
    except RuntimeError as e:
        logger.error(f"[AAWAZ/CHAT] Both cloud and Ollama failed for {req.name}: {e}")
        raise HTTPException(
            status_code=503,
            detail="AI is temporarily unavailable. Please try again in a moment.",
        )

    history.append({"role": "user", "content": req.message})
    history.append({"role": "aawaz", "content": response})
    profile["aawaz_history"] = history

    observations = extract_micro_observations(history)
    for obs in observations:
        profile = add_micro_observation(profile, obs)

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
        "micro_observation": get_latest_observation(profile),
    }


# Core routes


@core_router.post("/session")
async def run_session(req: SessionRequest):
    profile = get_or_create_student(req.name, req.grade, req.uid)
    previous_identity = profile.get("identity_current") or None

    logger.info(
        f"[SESSION] {req.name} | session #{profile.get('session_count', 0) + 1}"
    )

    # Enrich Darpan's input with behavioral signals observed during onboarding.
    # Darpan sees the pattern evidence alongside the raw text, which raises confidence.
    enriched_input = req.student_input
    obs = profile.get("micro_observations", [])
    if obs:
        recent_obs = [o["text"] for o in obs[-3:]]
        enriched_input += (
            "\n\n[Behavioral signals observed during conversation: "
            + " | ".join(recent_obs)
            + "]"
        )

    identity = run_darpan(enriched_input, req.grade, previous_identity)

    delta = (
        get_identity_delta(previous_identity, identity) if previous_identity else None
    )

    profile["identity_current"] = identity
    if "identity_history" not in profile:
        profile["identity_history"] = []
    profile["identity_history"].append(
        {"session": profile["session_count"] + 1, "snapshot": identity}
    )
    profile["session_count"] += 1
    profile = add_message(profile, "user", req.student_input)
    save_student(profile)

    return {
        "identity": identity,
        "identity_confidence": identity.get("identity_confidence", 3),
        "session_count": profile["session_count"],
        "delta": delta,
        "should_simulate": True,
        "message": (
            "First session done. Come back soon."
            if profile["session_count"] == 1
            else "Back again. Let us see what changed."
        ),
    }


@core_router.post("/simulate")
async def simulate(req: SimulateRequest):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found.")

    if not profile.get("identity_current"):
        raise HTTPException(
            status_code=400, detail="No identity found. Run /session first."
        )

    identity = profile["identity_current"]
    career_data = get_careers_for_identity(identity, n=5)

    logger.info(f"[SIMULATE] {req.name} | session #{profile.get('session_count', 0)}")

    futures = run_simulator(
        identity_json=identity,
        grade=profile["grade"],
        session_count=profile.get("session_count", 1),
        career_data=career_data,
    )

    if "futures_generated" not in profile:
        profile["futures_generated"] = []
    profile["futures_generated"].append(
        {
            "session": profile.get("session_count", 1),
            "futures": futures.get("futures", []),
        }
    )
    save_student(profile)

    is_fallback = futures.get("_fallback", False)
    return {**futures, "is_fallback": is_fallback}


@core_router.post("/chat")
async def chat(req: ChatRequest):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile or not profile.get("identity_current"):
        raise HTTPException(
            status_code=400, detail="No identity found. Run /session first."
        )

    language = detect_language(req.question)
    history = get_last_n_messages(profile, n=5)

    bhavishya_turns = sum(
        1
        for m in profile.get("conversation_history", [])
        if m.get("role") == "bhavishya"
    )

    # Delayed signal pacing: surface observations and callbacks every 3rd turn.
    # Instant pattern recognition reads as AI. A beat of delay reads as human.
    # Exception: returning students (session_count > 1) get the callback on their
    # very first chat message so longitudinal memory fires the moment they re-enter.
    is_returning_first_chat = (
        profile.get("session_count", 0) > 1 and bhavishya_turns == 0
    )
    allow_signals = is_returning_first_chat or (bhavishya_turns % 3 == 2)

    micro_obs = get_latest_observation(profile) if allow_signals else None
    callback = get_identity_callback(profile) if allow_signals else None

    career_data = get_careers_for_identity(profile["identity_current"], n=3)

    logger.info(
        f"[CHAT] {req.name} | lang={language} | turns={bhavishya_turns} | "
        f"callback={'yes' if callback else 'no'} | "
        f"observation={'yes' if micro_obs else 'no'}"
    )

    # run_margdarshak returns (response_text, is_fallback)
    response, is_fallback = run_margdarshak(
        question=req.question,
        identity_json=profile["identity_current"],
        history=history,
        language=language,
        micro_observation=micro_obs,
        identity_callback=callback,
        career_data=career_data,
    )

    profile = add_message(profile, "user", req.question)
    profile = add_message(profile, "bhavishya", response)
    save_student(profile)

    return {
        "response": response,
        "language_detected": language,
        "had_callback": callback is not None,
        "is_fallback": is_fallback,
        "identity_confidence": profile["identity_current"].get(
            "identity_confidence", 5
        ),
    }


@app.get("/profile/{name}/{grade}/{uid}", tags=["meta"])
async def get_profile(name: str, grade: int, uid: str):
    profile = load_student(name, grade, uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found.")
    return profile


@app.get("/profile/u/{username}", tags=["meta"])
async def get_profile_by_username(username: str):
    """Direct profile fetch by username - used by frontend after login."""
    profile = load_by_username(username)
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found.")
    return profile


app.include_router(auth_router)
app.include_router(aawaz_router)
app.include_router(core_router)
