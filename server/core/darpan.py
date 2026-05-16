import asyncio
import json
import logging
import os

import ollama
from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger("bhavishya.darpan")

_CLOUD_MODEL = "gemma-4-26b-a4b-it"
_OLLAMA_MODEL = "gemma4:e4b"

_PROMPT_CACHE: str | None = None
_GEMINI_CLIENT: genai.Client | None = None
_CLIENT_LOCK = asyncio.Lock()  # guards lazy init

_REQUIRED_KEYS = [
    "thinking_style",
    "core_values",
    "hidden_strengths",
    "active_fears",
    "energy_signature",
    "identity_confidence",
]

_FALLBACK_IDENTITY = {
    "thinking_style": "Learns by doing and experimenting rather than following instructions.",
    "core_values": ["independence", "creativity", "authenticity"],
    "hidden_strengths": [
        "Strong ability to notice patterns others overlook.",
        "Persistent in areas that genuinely interest them.",
    ],
    "active_fears": [
        "Choosing a path that feels wrong but is hard to reverse.",
        "Disappointing family while trying to figure things out.",
    ],
    "family_pressure_map": "Moderate family pressure toward conventional career paths.",
    "energy_signature": "Comes alive when working on self-directed projects with visible output.",
    "identity_confidence": 3,
    "changed_since_last": False,
    "change_summary": "",
    "_fallback": True,
}


# Initialisation


def _load_prompt() -> str:
    global _PROMPT_CACHE
    if _PROMPT_CACHE is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "prompts", "darpan_prompt.txt")
        with open(path, encoding="utf-8") as f:
            _PROMPT_CACHE = f.read()
    return _PROMPT_CACHE


def init_client() -> None:
    """
    Pre-warm the Gemini client at application startup (called from FastAPI lifespan).
    Safe to call multiple times; protected by module-level lock during async init.
    """
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        logger.info("[DARPAN] Gemini client initialised.")


def _get_client() -> genai.Client:
    """
    Synchronous accessor used inside asyncio.to_thread.
    By the time any request arrives, lifespan has already called init_client(),
    so this path only triggers in tests or direct script usage.
    """
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _GEMINI_CLIENT


# Core logic


def run_darpan(
    student_input: str,
    grade: int,
    previous_session: dict | None = None,
    language_preference: str = "english",
) -> dict:
    """
    Synchronous entry point — called via asyncio.to_thread from the FastAPI route.

    JSON mode means response.text is already valid JSON; we parse it directly.
    If the model still manages to return invalid JSON (extremely rare in JSON mode),
    we fall back gracefully instead of crashing.
    """
    system_prompt = _load_prompt().format(language_preference=language_preference)

    user_msg = f"Grade: {grade}\nStudent says: {student_input}"
    if previous_session:
        clean_prev = {k: v for k, v in previous_session.items() if k != "_fallback"}
        user_msg += f"\nPrevious identity snapshot: {json.dumps(clean_prev, ensure_ascii=False)}"

    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()

    try:
        if mode == "cloud":
            response = _get_client().models.generate_content(
                model=_CLOUD_MODEL,
                contents=user_msg,
                config={
                    "system_instruction": system_prompt,
                    # JSON mode: model is structurally constrained to emit valid JSON.
                    # No regex extraction required; json.loads() runs directly.
                    "response_mime_type": "application/json",
                    "http_options": {"timeout": 25000},
                },
            )
            result = json.loads(response.text)
        else:
            # Ollama does not support response_mime_type; keep the prompt-level JSON
            # instruction from darpan_prompt.txt and parse best-effort.
            response = ollama.chat(
                model=_OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                format="json",  # Ollama's equivalent of JSON mode
            )
            result = json.loads(response["message"]["content"])

        # Validate required keys are present
        missing = [k for k in _REQUIRED_KEYS if k not in result]
        if missing:
            logger.warning(f"[DARPAN/{mode.upper()}] Missing keys: {missing}")
            raise ValueError(f"Missing required keys: {missing}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[DARPAN/{mode.upper()}] JSON parse failed: {e}")
        return _FALLBACK_IDENTITY
    except ValueError as e:
        logger.warning(f"[DARPAN/{mode.upper()}] Validation failed: {e}")
        return _FALLBACK_IDENTITY
    except Exception as e:
        logger.error(f"[DARPAN/{mode.upper()}] Unexpected error: {e}")
        return _FALLBACK_IDENTITY
