import os
import re
import json
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()

_CLOUD_MODEL = "gemma-4-26b-a4b-it"
_OLLAMA_MODEL = "gemma4:e4b"

# Cached once at first call, never read from disk again.
_PROMPT_CACHE: str | None = None

# Singleton client - avoids TLS renegotiation on every call (~50ms saved per request).
_GEMINI_CLIENT: genai.Client | None = None

_REQUIRED_KEYS = [
    "thinking_style",
    "core_values",
    "hidden_strengths",
    "active_fears",
    "energy_signature",
    "identity_confidence",
]

# Generic fallback. Fires only when both cloud and Ollama fail.
# identity_confidence=3 tells Margdarshak not to make strong claims.
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


def _load_prompt() -> str:
    global _PROMPT_CACHE
    if _PROMPT_CACHE is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "prompts", "darpan_prompt.txt")
        with open(path, encoding="utf-8") as f:
            _PROMPT_CACHE = f.read()
    return _PROMPT_CACHE


def _get_client() -> genai.Client:
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _GEMINI_CLIENT


def run_darpan(student_input: str, grade: int, previous_session: dict = None) -> dict:
    system_prompt = _load_prompt()

    user_msg = f"Grade: {grade}\nStudent says: {student_input}"
    if previous_session:
        # Strip internal flags before sending to model.
        clean_prev = {k: v for k, v in previous_session.items() if k != "_fallback"}
        user_msg += f"\nPrevious identity snapshot: {json.dumps(clean_prev, ensure_ascii=False)}"

    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()
    raw = ""

    try:
        if mode == "cloud":
            response = _get_client().models.generate_content(
                model=_CLOUD_MODEL,
                contents=user_msg,
                config={
                    "system_instruction": system_prompt,
                    "http_options": {"timeout": 25000},
                },
            )
            raw = response.text.strip()
        else:
            response = ollama.chat(
                model=_OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = response["message"]["content"].strip()

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in Darpan response.")
        result = json.loads(match.group(0))

        for key in _REQUIRED_KEYS:
            if key not in result:
                raise ValueError(f"Missing required key: {key}")

        return result

    except json.JSONDecodeError as e:
        print(f"[DARPAN/{mode.upper()}] JSON parse failed: {e} | raw: {raw[:200]}")
        return _FALLBACK_IDENTITY
    except ValueError as e:
        print(f"[DARPAN/{mode.upper()}] Validation failed: {e}")
        return _FALLBACK_IDENTITY
    except Exception as e:
        print(f"[DARPAN/{mode.upper()}] Error: {e}")
        return _FALLBACK_IDENTITY
