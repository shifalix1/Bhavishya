import asyncio
import logging
import os
import re

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
    trim_conversation_history,
)
from core.language import detect_language
from core.careers import get_careers_for_identity

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Bhavishya API", version="2.3.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
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

# ── X-API-Key auth middleware ─────────────────────────────────────────────────
# Store BHAVISHYA_API_KEY in .env. All non-health endpoints require this header.
_API_KEY = os.getenv("BHAVISHYA_API_KEY", "")

UNPROTECTED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.url.path in UNPROTECTED_PATHS:
        return await call_next(request)
    if not _API_KEY:
        # Dev mode: no key configured → allow all (log a warning)
        logger.warning("BHAVISHYA_API_KEY not set - running unauthenticated!")
        return await call_next(request)
    incoming = request.headers.get("X-API-Key", "")
    if incoming != _API_KEY:
        return JSONResponse(
            status_code=401, content={"detail": "Invalid or missing API key."}
        )
    return await call_next(request)


# ── Helpers ───────────────────────────────────────────────────────────────────
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
_CONV_HISTORY_LIMIT = 50  # fix #9: cap stored messages


def validate_username(username: str) -> None:
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-20 characters: letters, numbers, or underscore only.",
        )


def validate_pin(pin: str) -> None:
    if not pin.isdigit() or len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits.")


# ── Request models ────────────────────────────────────────────────────────────


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
    image_anomalies: Optional[str] = None


# ── Routers ───────────────────────────────────────────────────────────────────
auth_router = APIRouter(prefix="", tags=["auth"])
aawaz_router = APIRouter(prefix="/aawaz", tags=["aawaz"])
core_router = APIRouter(prefix="", tags=["core"])


@app.get("/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "model": os.getenv("BHAVISHYA_MODE", "cloud"),
        "version": "2.3.0",
    }


# ── Auth routes ───────────────────────────────────────────────────────────────


@auth_router.post("/register")
@limiter.limit("10/minute")
async def register(req: RegisterRequest, request: Request):
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
@limiter.limit("20/minute")
async def login(req: LoginRequest, request: Request):
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
@limiter.limit("10/minute")
async def onboard(req: OnboardRequest, request: Request):
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


# ── Aawaz routes ──────────────────────────────────────────────────────────────


@aawaz_router.post("/transcribe")
@limiter.limit("10/minute")
async def aawaz_transcribe(req: AawazTranscribeRequest, request: Request):
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
@limiter.limit("10/minute")
async def aawaz_chat(req: AawazChatRequest, request: Request):
    # FIX #6: do NOT auto-create profile here. Require explicit register/onboard first.
    profile = load_student(req.name, req.grade, req.uid)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found. Please register or onboard first.",
        )

    history = profile.get("aawaz_history", [])

    logger.info(
        f"[AAWAZ/CHAT] {req.name} | "
        f"exchange #{len([m for m in history if m['role'] == 'user']) + 1} | "
        f"lang={req.language}"
    )

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

    # FIX #8: only signal readiness if darpan hasn't run yet
    already_run = profile.get("darpan_run", False)
    ready = False
    combined_input = None
    if not already_run:
        ready = is_ready_for_darpan(history)
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


# ── Core routes ───────────────────────────────────────────────────────────────


@core_router.post("/session")
@limiter.limit("10/minute")
async def run_session(req: SessionRequest, request: Request):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found.")

    previous_identity = profile.get("identity_current") or None

    logger.info(
        f"[SESSION] {req.name} | session #{profile.get('session_count', 0) + 1}"
    )

    enriched_input = req.student_input
    obs = profile.get("micro_observations", [])
    if obs:
        recent_obs = [o["text"] for o in obs[-3:]]
        enriched_input += (
            "\n\n[Behavioral signals observed during conversation: "
            + " | ".join(recent_obs)
            + "]"
        )

    identity = await asyncio.to_thread(
        run_darpan, enriched_input, req.grade, previous_identity
    )

    # FIX #11: warn when darpan output looks like the generic fallback
    thinking = identity.get("thinking_style", "")
    conf = identity.get("identity_confidence", 5)
    if conf <= 3 and "learns by doing" in thinking.lower():
        logger.warning(
            f"[DARPAN] Possible generic output for {req.name} - "
            f"confidence={conf}, thinking_style resembles fallback phrasing."
        )

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
    # FIX #8: mark darpan as run so aawaz/chat won't re-trigger
    profile["darpan_run"] = True
    profile = add_message(profile, "user", req.student_input)
    # FIX #9: trim conversation history
    profile = trim_conversation_history(profile, limit=_CONV_HISTORY_LIMIT)
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
@limiter.limit("5/minute")
async def simulate(req: SimulateRequest, request: Request):
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

    futures = await asyncio.to_thread(
        run_simulator,
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
@limiter.limit("20/minute")
async def chat(req: ChatRequest, request: Request):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile or not profile.get("identity_current"):
        raise HTTPException(
            status_code=400, detail="No identity found. Run /session first."
        )

    language = detect_language(req.question)
    history = get_last_n_messages(profile, n=5)

    # FIX #13: check full conversation_history length, not trimmed history
    bhavishya_turns = sum(
        1
        for m in profile.get("conversation_history", [])
        if m.get("role") == "bhavishya"
    )

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

    response, is_fallback = await asyncio.to_thread(
        run_margdarshak,
        question=req.question,
        identity_json=profile["identity_current"],
        history=history,
        language=language,
        micro_observation=micro_obs,
        identity_callback=callback,
        career_data=career_data,
        total_bhavishya_turns=bhavishya_turns,  # FIX #13
    )

    profile = add_message(profile, "user", req.question)
    profile = add_message(profile, "bhavishya", response)
    # FIX #9: trim on every chat turn
    profile = trim_conversation_history(profile, limit=_CONV_HISTORY_LIMIT)
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


# FIX #5: /profile endpoints removed. Profile data is only accessible via authenticated
# /login response. The open GET endpoints exposed pin_hash + full history to anyone.
# If you need a profile fetch, add it behind login auth with a session token.


app.include_router(auth_router)
app.include_router(aawaz_router)
app.include_router(core_router)
