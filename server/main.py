import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request, Query
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

# Core imports

from core.darpan import run_darpan, init_client as darpan_init
from core.simulator import run_simulator, init_client as simulator_init
from core.margdarshak import (
    run_margdarshak_guidance,
    run_margdarshak_question,
    init_client as margdarshak_init,
)
from core.aawaz import (
    run_aawaz_transcribe,
    run_aawaz_chat,
    is_ready_for_darpan,
    extract_micro_observations,
    init_client as aawaz_init,
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
    needs_compression,
    compress_history,
)
from core.language import detect_language
from core.careers import get_careers_for_identity

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Rolling summarizer
# Injected into compress_history() so memory.py stays model-agnostic.
# Uses the cloud client from margdarshak (already initialised at startup).

_SUMMARY_MODEL = "gemma-4-26b-a4b-it"
_SUMMARY_SYSTEM = (
    "You are a memory compression assistant. "
    "You will receive a sequence of conversation turns between a student and Bhavishya AI. "
    "Your job: write a dense, factual 3-5 sentence summary that captures: "
    "(1) the student's core motivations and interests mentioned, "
    "(2) any family pressure or constraints revealed, "
    "(3) any specific fears or hopes expressed, "
    "(4) any key decisions or turning points discussed. "
    "Write in third person. Plain prose only. No bullet points. No headers."
)


async def _summarize_history_block(text: str) -> str:
    """
    Async summarizer injected into compress_history().
    Uses a lightweight generation call — minimal tokens, 10s timeout.
    Falls back to a simple truncated excerpt if the model call fails.
    """
    from google import genai as _genai

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        # No API key: return a naive first-200-word excerpt instead of crashing.
        words = text.split()
        return "Earlier in the conversation: " + " ".join(words[:200])

    try:
        client = _genai.Client(api_key=api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=_SUMMARY_MODEL,
            contents=text,
            config={
                "system_instruction": _SUMMARY_SYSTEM,
                "http_options": {"timeout": 10000},
            },
        )
        return response.text.strip()
    except Exception as e:
        logger.warning(
            f"[SUMMARIZER] LLM summarization failed ({e}); using excerpt fallback."
        )
        words = text.split()
        return "Earlier in the conversation: " + " ".join(words[:200])


async def _maybe_compress(profile: dict) -> dict:
    """
    Check if rolling compression is needed and run it if so.
    Called in chat and session endpoints before save_student().
    """
    if needs_compression(profile):
        logger.info(
            f"[MEMORY] Compressing history for {profile.get('username', '?')} "
            f"({len(profile.get('conversation_history', []))} messages -> rolling summary)"
        )
        profile = await compress_history(profile, _summarize_history_block)
    return profile


# Lifespan: startup pre-warm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Pre-warm all four Gemini client singletons at startup.
    This runs the TLS handshake and object init once, before any request arrives,
    eliminating the per-module lazy-init race under concurrent load.
    """
    logger.info("[STARTUP] Pre-warming Gemini clients...")
    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()
    if mode == "cloud":
        await asyncio.to_thread(aawaz_init)
        await asyncio.to_thread(darpan_init)
        await asyncio.to_thread(margdarshak_init)
        await asyncio.to_thread(simulator_init)
        logger.info("[STARTUP] All Gemini clients ready.")
    else:
        logger.info("[STARTUP] Ollama mode - skipping Gemini client pre-warm.")
    yield
    # Shutdown: nothing to clean up for stateless HTTP clients.
    logger.info("[SHUTDOWN] Bhavishya API shutting down.")


# App

app = FastAPI(title="Bhavishya API", version="3.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

# X-API-Key auth middleware
_API_KEY = os.getenv("BHAVISHYA_API_KEY", "")
UNPROTECTED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.method == "OPTIONS":  # ← let CORS preflight through
        return await call_next(request)
    if request.url.path in UNPROTECTED_PATHS:
        return await call_next(request)
    if not _API_KEY:
        logger.warning("BHAVISHYA_API_KEY not set - running unauthenticated!")
        return await call_next(request)
    if request.headers.get("X-API-Key", "") != _API_KEY:
        return JSONResponse(
            status_code=401, content={"detail": "Invalid or missing API key."}
        )
    return await call_next(request)


# Helpers
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
_CONV_HISTORY_LIMIT = 50  # emergency safety cap; compression fires at 40


def validate_username(username: str) -> None:
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-20 characters: letters, numbers, or underscore only.",
        )


def validate_pin(pin: str) -> None:
    if not pin.isdigit() or len(pin) != 4:
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits.")


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


class MargdarshakGuidanceRequest(BaseModel):
    uid: str
    name: str
    grade: int
    language: Optional[str] = "english"


class MargdarshakQuestionRequest(BaseModel):
    uid: str
    name: str
    grade: int
    question: str
    language: Optional[str] = "english"
    guidance: Optional[dict] = None


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


# Routers
auth_router = APIRouter(prefix="", tags=["auth"])
aawaz_router = APIRouter(prefix="/aawaz", tags=["aawaz"])
core_router = APIRouter(prefix="", tags=["core"])


# Health


@app.get("/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "model": os.getenv("BHAVISHYA_MODE", "cloud"),
        "version": "3.0.0",
    }


# Auth routes


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
        raise HTTPException(status_code=401, detail="Incorrect PIN.")

    logger.info(f"Login: {req.username} | session #{profile.get('session_count', 0)}")

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
    """Legacy onboard flow (no PIN). Still supported for hackathon demo personas."""
    profile = load_student(req.name, req.grade, req.uid)
    if profile:
        logger.info(f"Returning student (legacy onboard): {req.name}")
        return {
            "username": profile.get("username", req.uid),
            "name": profile["name"],
            "grade": profile["grade"],
            "uid": profile.get("uid", req.uid),
            "is_returning": True,
            "session_count": profile.get("session_count", 0),
            "has_identity": bool(profile.get("identity_current")),
            "has_futures": bool(profile.get("futures_generated")),
        }

    profile = create_new_profile(name=req.name.strip(), grade=req.grade, uid=req.uid)
    save_student(profile)
    logger.info(f"New student (legacy onboard): {req.name} (grade {req.grade})")

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


# Aawaz routes


@aawaz_router.post("/transcribe")
@limiter.limit("10/minute")
async def aawaz_transcribe(req: AawazTranscribeRequest, request: Request):
    profile = load_student(req.name, req.grade, req.uid)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found. Please register or onboard first.",
        )

    result = await run_aawaz_transcribe(
        audio_b64=req.audio_b64,
        audio_mime=req.audio_mime or "audio/webm",
        image_b64=req.image_b64,
        image_mime=req.image_mime or "image/jpeg",
        text_fallback=req.text_fallback,
        grade=req.grade,
        name=req.name,
    )

    if result.get("image_description"):
        profile["image_anomalies"] = result["image_description"]
        save_student(profile)

    return result


@aawaz_router.post("/chat")
@limiter.limit("10/minute")
async def aawaz_chat(req: AawazChatRequest, request: Request):
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

    image_anomalies = req.image_anomalies or profile.get("image_anomalies")

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


# Core routes


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
    profile["darpan_run"] = True
    profile = add_message(profile, "user", req.student_input)

    # Rolling summary check before save
    profile = await _maybe_compress(profile)
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


@core_router.post("/margdarshak/guidance")
@limiter.limit("10/minute")
async def margdarshak_guidance(req: MargdarshakGuidanceRequest, request: Request):
    """
    Generate Margdarshak structured guidance from identity fingerprint.
    Returns: current_read, next_move (action/why/type), watch_for, opening_line.
    Requires identity_current (Darpan must have run first).
    """
    profile = load_student(req.name, req.grade, req.uid)
    if not profile or not profile.get("identity_current"):
        raise HTTPException(
            status_code=400,
            detail="No identity found. Complete a Darpan session first.",
        )

    identity = profile["identity_current"]
    language = req.language or profile.get("language_preference", "english")
    is_first_guidance = not bool(profile.get("margdarshak_guidance"))

    futures_list = profile.get("futures_generated", [])
    latest_futures = futures_list[-1].get("futures", []) if futures_list else None

    callback = get_identity_callback(profile)
    career_data = get_careers_for_identity(identity, n=3)

    logger.info(
        f"[MARGDARSHAK/GUIDANCE] {req.name} | lang={language} | "
        f"first={'yes' if is_first_guidance else 'no'} | "
        f"sessions={profile.get('session_count', 0)}"
    )

    guidance, is_fallback = await asyncio.to_thread(
        run_margdarshak_guidance,
        identity_json=identity,
        language=language,
        session_count=profile.get("session_count", 1),
        is_first_guidance=is_first_guidance,
        futures=latest_futures,
        identity_callback=callback,
        career_data=career_data,
    )

    profile["margdarshak_guidance"] = guidance
    profile["margdarshak_question_used"] = False
    save_student(profile)

    return {
        "guidance": guidance,
        "is_fallback": is_fallback,
        "identity_confidence": identity.get("identity_confidence", 5),
        "session_count": profile.get("session_count", 1),
        "question_used": profile.get("margdarshak_question_used", False),
    }


@core_router.post("/margdarshak/question")
@limiter.limit("5/minute")
async def margdarshak_question(req: MargdarshakQuestionRequest, request: Request):
    """
    Student's one question per guidance cycle to Margdarshak.
    Scarcity is intentional.
    """
    profile = load_student(req.name, req.grade, req.uid)
    if not profile or not profile.get("identity_current"):
        raise HTTPException(
            status_code=400,
            detail="No identity found. Complete a Darpan session first.",
        )

    if profile.get("margdarshak_question_used"):
        raise HTTPException(
            status_code=429,
            detail="One question per session. Come back after your next Darpan session.",
        )

    identity = profile["identity_current"]
    language = req.language or profile.get("language_preference", "english")
    guidance = req.guidance or profile.get("margdarshak_guidance") or {}

    logger.info(f"[MARGDARSHAK/QUESTION] {req.name} | lang={language}")

    answer, is_fallback = await asyncio.to_thread(
        run_margdarshak_question,
        question=req.question,
        identity_json=identity,
        guidance=guidance,
        language=language,
    )

    profile["margdarshak_question_used"] = True
    if "margdarshak_history" not in profile:
        profile["margdarshak_history"] = []
    profile["margdarshak_history"].append(
        {
            "question": req.question,
            "answer": answer,
            "session": profile.get("session_count", 1),
        }
    )
    save_student(profile)

    return {
        "answer": answer,
        "is_fallback": is_fallback,
        "question_used": True,
    }


@core_router.get("/history/{uid}")
@limiter.limit("20/minute")
async def get_history(uid: str, request: Request):
    """
    Returns per-session history for the sidebar:
    aawaz_history, identity_history, margdarshak_history, futures_generated
    grouped by session number.
    """
    profile = load_by_username(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found.")

    total_sessions = profile.get("session_count", 0)
    identity_history = profile.get("identity_history", [])
    futures_generated = profile.get("futures_generated", [])
    margdarshak_history = profile.get("margdarshak_history", [])
    aawaz_history = profile.get("aawaz_history", [])

    sessions = []
    for i in range(1, total_sessions + 1):
        identity_snap = next(
            (h["snapshot"] for h in identity_history if h.get("session") == i), None
        )
        futures_snap = next(
            (f["futures"] for f in futures_generated if f.get("session") == i), None
        )
        marg_entries = [m for m in margdarshak_history if m.get("session") == i]

        sessions.append(
            {
                "session": i,
                "identity": identity_snap,
                "futures": futures_snap,
                "margdarshak": marg_entries,
            }
        )

    return {
        "username": profile.get("username"),
        "name": profile.get("name"),
        "total_sessions": total_sessions,
        "aawaz_history": aawaz_history,  # all aawaz turns (not per-session, shared)
        "sessions": sessions,
    }


# Router registration
app.include_router(auth_router)
app.include_router(aawaz_router)
app.include_router(core_router)
