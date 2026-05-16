"""
Margdarshak - the guide layer of Bhavishya.

Not a chatbot. Generates structured guidance from a student's identity fingerprint.
Returns: current_read, next_move (action/why/type), watch_for, opening_line.

API routes to add in main.py:
  POST /api/margdarshak/guidance
    body: { uid, language }
    returns: { guidance: {...}, is_fallback: bool, generated_at: str }

  POST /api/margdarshak/question
    body: { uid, question, language, guidance: {...} }
    returns: { answer: str, is_fallback: bool }
"""

import json
import logging
import os
import re
from datetime import datetime, timezone

import ollama
from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger("bhavishya.margdarshak")

_CLOUD_MODEL = "gemma-4-26b-a4b-it"
_OLLAMA_MODEL = "gemma4:e4b"

_GUIDANCE_PROMPT_CACHE: str | None = None
_QUESTION_PROMPT_CACHE: str | None = None
_GEMINI_CLIENT: genai.Client | None = None


def _load_guidance_prompt() -> str:
    global _GUIDANCE_PROMPT_CACHE
    if _GUIDANCE_PROMPT_CACHE is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "prompts", "margdarshak_prompt.txt")
        with open(path, encoding="utf-8") as f:
            _GUIDANCE_PROMPT_CACHE = f.read()
    return _GUIDANCE_PROMPT_CACHE


def _load_question_prompt() -> str:
    global _QUESTION_PROMPT_CACHE
    if _QUESTION_PROMPT_CACHE is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "prompts", "margdarshak_question_prompt.txt")
        with open(path, encoding="utf-8") as f:
            _QUESTION_PROMPT_CACHE = f.read()
    return _QUESTION_PROMPT_CACHE


def init_client() -> None:
    """Pre-warm at startup. Safe to call multiple times."""
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        logger.info("[MARGDARSHAK] Gemini client initialised.")


def _get_client() -> genai.Client:
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _GEMINI_CLIENT


def _call_model(
    system_prompt: str, user_msg: str, mode: str, timeout: int = 25000
) -> str:
    if mode == "cloud":
        response = _get_client().models.generate_content(
            model=_CLOUD_MODEL,
            contents=user_msg,
            config={
                "system_instruction": system_prompt,
                "http_options": {"timeout": timeout},
            },
        )
        return response.text.strip()
    else:
        response = ollama.chat(
            model=_OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
        )
        return response["message"]["content"].strip()


def _parse_guidance_json(raw: str) -> dict:
    """Strip any markdown fences and parse JSON. Raises on failure."""
    clean = raw.strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean)
    clean = re.sub(r"\s*```$", "", clean)
    return json.loads(clean.strip())


def _validate_guidance(guidance: dict) -> None:
    """Raise ValueError if required shape is missing."""
    required_top = {"current_read", "next_move", "watch_for"}
    missing = required_top - guidance.keys()
    if missing:
        raise ValueError(f"Missing top-level keys: {missing}")
    move = guidance.get("next_move", {})
    if not isinstance(move, dict):
        raise ValueError("next_move must be a dict")
    required_move = {"action", "why", "type"}
    missing_move = required_move - move.keys()
    if missing_move:
        raise ValueError(f"Missing next_move keys: {missing_move}")
    valid_types = {"do", "watch", "ask", "reflect"}
    if move.get("type") not in valid_types:
        move["type"] = "do"


def run_margdarshak_guidance(
    identity_json: dict,
    language: str,
    session_count: int,
    is_first_guidance: bool = False,
    futures: list | None = None,
    identity_callback: str | None = None,
    career_data: list | None = None,
) -> tuple[dict, bool]:
    """
    Generate structured guidance for a student.
    Returns (guidance_dict, is_fallback).

    guidance_dict shape:
    {
        "current_read": str,
        "next_move": { "action": str, "why": str, "type": "do|watch|ask|reflect" },
        "watch_for": str,
        "opening_line": str,
        "generated_at": str (ISO UTC)
    }
    """
    system_prompt = _load_guidance_prompt().format(language_preference=language)

    context_lines = [
        f"detected_language: {language}",
        f"session_count: {session_count}",
        f"is_first_guidance: {'true' if is_first_guidance else 'false'}",
        f"identity_confidence: {identity_json.get('identity_confidence', 5)}/10",
        f"identity: {json.dumps(identity_json, ensure_ascii=False)}",
    ]

    if futures:
        slim_futures = [
            {
                "path_name": f.get("path_name", ""),
                "tagline": f.get("tagline", ""),
                "core_field": f.get("core_field", ""),
            }
            for f in futures[:3]
        ]
        context_lines.append(
            f"futures_simulated: {json.dumps(slim_futures, ensure_ascii=False)}"
        )

    if identity_callback:
        context_lines.append(f"returning_student_context: {identity_callback}")

    if career_data:
        slim_careers = [
            {
                "name": c.get("name", ""),
                "reality": c.get("honest_reality", {}).get(
                    "what_they_dont_tell_you", ""
                ),
                "ai_risk": c.get("ai_disruption", {}).get("risk", ""),
            }
            for c in career_data[:3]
        ]
        context_lines.append(
            f"relevant_career_data: {json.dumps(slim_careers, ensure_ascii=False)}"
        )

    user_msg = "\n".join(context_lines)
    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()

    try:
        raw = _call_model(system_prompt, user_msg, mode)
        guidance = _parse_guidance_json(raw)
        _validate_guidance(guidance)
        guidance.setdefault("opening_line", "")
        guidance["generated_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[MARGDARSHAK] Guidance generated. mode={mode} language={language}"
        )
        return guidance, False

    except Exception as e:
        logger.error(f"[MARGDARSHAK/{mode.upper()}] Guidance error: {e}")
        return _fallback_guidance(language), True


def run_margdarshak_question(
    question: str,
    identity_json: dict,
    guidance: dict,
    language: str,
) -> tuple[str, bool]:
    """
    Answer one student question about their guidance.
    Returns (answer_text, is_fallback).
    """
    system_prompt = _load_question_prompt().format(language_preference=language)

    user_msg = "\n".join(
        [
            f"detected_language: {language}",
            f"student_question: {question}",
            f"current_guidance: {json.dumps(guidance, ensure_ascii=False)}",
            f"identity_snapshot: {json.dumps({k: identity_json.get(k) for k in ('thinking_style', 'hidden_strengths', 'active_fears', 'energy_signature')}, ensure_ascii=False)}",
        ]
    )

    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()

    try:
        answer = _call_model(system_prompt, user_msg, mode)
        return answer.strip(), False
    except Exception as e:
        logger.error(f"[MARGDARSHAK/{mode.upper()}] Question error: {e}")
        if language == "english":
            return (
                "Give me a moment on that one. Bring it back in your next session.",
                True,
            )
        return (
            "Yeh sawaal next session mein le aana. Tab properly soch ke jawab dunga.",
            True,
        )


def _fallback_guidance(language: str) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    if language == "english":
        return {
            "current_read": (
                "Something went wrong before I could read your fingerprint properly. "
                "This happens sometimes. It does not mean anything is wrong with you. "
                "Come back in a moment and try again."
            ),
            "next_move": {
                "action": "Close this tab, take a 5-minute break, then return.",
                "why": "A reset often surfaces what a stuck start cannot.",
                "type": "do",
            },
            "watch_for": "When you return and the question feels a little clearer than before.",
            "opening_line": "",
            "generated_at": ts,
        }
    return {
        "current_read": (
            "Kuch interrupt ho gaya, teri fingerprint properly read nahi ho payi. "
            "Yeh kabhi kabhi hota hai, iska matlab kuch galat nahi hai. "
            "Ek second baad wapas aa."
        ),
        "next_move": {
            "action": "Tab band kar, 5 minute le, aur wapas aa.",
            "why": "Fresh start mein woh cheezein dikhti hain jo stuck start mein nahi dikhti.",
            "type": "do",
        },
        "watch_for": "Jab wapas aaye aur sawaal thoda clear lage pehle se.",
        "opening_line": "",
        "generated_at": ts,
    }
