import os
import re
import json
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()

_CLOUD_MODEL = "gemma-4-26b-a4b-it"
_OLLAMA_MODEL = "gemma4:e4b"

_PROMPT_CACHE: str | None = None
_GEMINI_CLIENT: genai.Client | None = None

_HEAVY_SIGNAL_RE = re.compile(
    r"fear|contradict|pressure|sacrifice|cost|honest|hard truth|worry|concern"
    r"|tension|gap|conflict|struggle|difficult|painful",
    re.IGNORECASE,
)


def _load_prompt() -> str:
    global _PROMPT_CACHE
    if _PROMPT_CACHE is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "prompts", "margdarshak_prompt.txt")
        with open(path, encoding="utf-8") as f:
            _PROMPT_CACHE = f.read()
    return _PROMPT_CACHE


def _get_client() -> genai.Client:
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _GEMINI_CLIENT


def run_margdarshak(
    question: str,
    identity_json: dict,
    history: list,
    language: str,
    micro_observation: str | None = None,
    identity_callback: str | None = None,
    career_data: list | None = None,
    # FIX #13: caller passes total bhavishya turns from the FULL conversation_history,
    # not from the trimmed `history` slice. This prevents the identity reveal re-firing
    # after the 5-message window drops the earlier bhavishya message.
    total_bhavishya_turns: int = 0,
) -> tuple[str, bool]:
    """
    Returns (response_text, is_fallback).
    is_fallback is True only when both cloud and Ollama fail.
    """
    base_prompt = _load_prompt()

    behavior_addendum = (
        "\n\nIMPORTANT TONE NOTE: Do NOT use structural headers or numbered labels "
        "like 'VALIDATE FIRST' or 'GAME PLAN' in your actual response. "
        "Those describe your internal process, not your output format. "
        "Write as a single flowing conversation - warm, direct, one idea at a time."
    )
    system_prompt = base_prompt + behavior_addendum

    # FIX #13: use total_bhavishya_turns (from full history) not the trimmed history slice
    is_first_response = total_bhavishya_turns == 0

    context_lines = [
        f"IS_FIRST_RESPONSE: {'yes' if is_first_response else 'no'}",
        f"Student question: {question}",
        f"Detected language: {language}",
        f"Student identity: {json.dumps(identity_json, ensure_ascii=False)}",
        f"Last 5 messages: {json.dumps(history, ensure_ascii=False)}",
    ]

    confidence = identity_json.get("identity_confidence", 5)
    if confidence <= 4:
        context_lines.append(
            f"\nIdentity confidence is LOW ({confidence}/10): limited signal from this student. "
            "Do not make strong claims about who they are. Ask questions instead of stating conclusions. "
            "Treat the identity JSON as a working hypothesis, not a diagnosis."
        )
    elif confidence >= 8:
        context_lines.append(
            f"\nIdentity confidence is HIGH ({confidence}/10): rich, specific signal. "
            "You can reference identity traits with conviction. This is a solid picture."
        )

    last_bhavishya = next(
        (m["content"] for m in reversed(history) if m.get("role") == "bhavishya"),
        None,
    )
    if last_bhavishya and _HEAVY_SIGNAL_RE.search(last_bhavishya):
        context_lines.append(
            "\nTONE NOTE: Your last response went deep. "
            "This one should be warmer and lighter. One idea, gently. Intelligence needs breathing room."
        )

    if identity_callback and micro_observation:
        micro_observation = None

    if micro_observation:
        context_lines.append(
            f"\nBehavioral observation from this session: {micro_observation}\n"
            "Reference this only if it fits naturally. "
            "Do not announce that you noticed it. Let it inform what you say."
        )

    if identity_callback:
        context_lines.append(
            f"\nMemory callback (returning student): {identity_callback}\n"
            "Weave this in once, like a sibling who genuinely remembers. "
            "Casual and imprecise, the way real memory works. Not a data readout."
        )

    if career_data:
        career_context = []
        for c in career_data[:3]:
            entry = {"name": c.get("name", "")}
            if c.get("honest_reality", {}).get("what_they_dont_tell_you"):
                entry["reality"] = c["honest_reality"]["what_they_dont_tell_you"]
            if c.get("parent_frame"):
                entry["parent_frame"] = c["parent_frame"]
            if c.get("ai_disruption", {}).get("risk"):
                entry["ai_risk"] = c["ai_disruption"]["risk"]
                entry["ai_what_survives"] = c["ai_disruption"].get("what_survives", "")
            career_context.append(entry)
        context_lines.append(
            f"\nRelevant career grounding data: {json.dumps(career_context, ensure_ascii=False)}\n"
            "Use only when directly relevant to the student's question. "
            "One specific fact, woven naturally. Never list all careers. Never dump the data."
        )

    user_msg = "\n".join(context_lines)
    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()

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
            return response.text.strip(), False
        else:
            response = ollama.chat(
                model=_OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            return response["message"]["content"].strip(), False

    except Exception as e:
        print(f"[MARGDARSHAK/{mode.upper()}] Error: {e}")
        if language == "english":
            fallback = "Give me a second to think about that. What you're asking matters - let's go slow."
        else:
            fallback = "Ek second, yeh sochna chahta hoon. Tumhara sawaal important hai - dhire dhire baat karte hain."
        return fallback, True
