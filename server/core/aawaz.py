import os
import re
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AAWAZ_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "aawaz_prompt.txt")

CLOUD_MODEL = "gemma-4-26b-a4b-it"
OFFLINE_MODEL = "gemma4:2b"


def _load_system_prompt() -> str:
    with open(AAWAZ_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


async def run_aawaz_transcribe(
    audio_b64: str | None,
    audio_mime: str,
    image_b64: str | None,
    image_mime: str,
    text_fallback: str | None,
    grade: int,
    name: str,
) -> dict:
    """
    Multimodal intake: audio + optional image → transcript + marksheet_data + image_description.
    Returns image_description for ALL image uploads (not just marksheets).
    Gracefully falls back and never crashes caller.
    Note: transcription is cloud-only (multimodal). Ollama 2b can't do this.
    """
    if not audio_b64 and not image_b64:
        text = text_fallback or ""
        return {
            "transcript": text,
            "marksheet_data": None,
            "image_description": None,
            "combined_input": text,
            "mode": "text",
        }

    parts = []
    if audio_b64:
        parts.append({"inline_data": {"mime_type": audio_mime, "data": audio_b64}})
    if image_b64:
        parts.append({"inline_data": {"mime_type": image_mime, "data": image_b64}})

    instructions = []
    if audio_b64:
        instructions.append(
            f"This is audio from {name}, a Class {grade} Indian student. "
            "Transcribe exactly what they said. Keep original language (Hindi/English/Hinglish). "
            "Output under the label: TRANSCRIPT:"
        )
    if image_b64:
        instructions.append(
            "Analyse this image carefully.\n"
            "1. If it is a marksheet or report card: extract subject-wise marks as "
            "'Subject: marks/total' (one per line), and the class, school, year if visible. "
            "Output under the label: MARKSHEET:\n"
            "2. Regardless of what the image is, also write a brief 1-2 sentence plain-English "
            "description of what you see — a hobby drawing, a certificate, a photo, etc. "
            "Output under the label: IMAGE_DESCRIPTION:"
        )
    parts.append({"text": "\n\n".join(instructions)})

    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.generate_content(
            model=CLOUD_MODEL,
            contents=[{"role": "user", "parts": parts}],
        )
        raw = response.text.strip()
    except Exception as e:
        print(f"[AAWAZ/TRANSCRIBE] Cloud failed ({e}) — returning text fallback")
        fallback = text_fallback or ""
        return {
            "transcript": fallback,
            "marksheet_data": None,
            "image_description": None,
            "combined_input": fallback,
            "mode": "fallback",
            "error": str(e),
        }

    transcript = ""
    marksheet_data = None
    image_description = None

    # Parse TRANSCRIPT
    if "TRANSCRIPT:" in raw:
        t_start = raw.index("TRANSCRIPT:") + len("TRANSCRIPT:")
        # end at next label or EOF
        next_labels = []
        for label in ("MARKSHEET:", "IMAGE_DESCRIPTION:"):
            if label in raw:
                next_labels.append(raw.index(label))
        t_end = min(next_labels) if next_labels else len(raw)
        transcript = raw[t_start:t_end].strip()
    elif not image_b64:
        transcript = raw

    # Parse MARKSHEET
    if "MARKSHEET:" in raw:
        m_start = raw.index("MARKSHEET:") + len("MARKSHEET:")
        m_end = (
            raw.index("IMAGE_DESCRIPTION:") if "IMAGE_DESCRIPTION:" in raw else len(raw)
        )
        marksheet_data = raw[m_start:m_end].strip() or None

    # Parse IMAGE_DESCRIPTION
    if "IMAGE_DESCRIPTION:" in raw:
        d_start = raw.index("IMAGE_DESCRIPTION:") + len("IMAGE_DESCRIPTION:")
        image_description = raw[d_start:].strip() or None

    # For image-only (no audio), transcript comes from text_fallback
    if image_b64 and not audio_b64:
        transcript = text_fallback or ""

    combined = transcript
    if marksheet_data:
        combined = f"{transcript}\n\n[Marksheet:\n{marksheet_data}]".strip()
    elif image_description:
        combined = f"{transcript}\n\n[Image: {image_description}]".strip()

    mode = (
        "voice+image"
        if (audio_b64 and image_b64)
        else "voice" if audio_b64 else "image"
    )

    return {
        "transcript": transcript,
        "marksheet_data": marksheet_data,
        "image_description": image_description,
        "combined_input": combined,
        "mode": mode,
    }


async def run_aawaz_chat(
    message: str,
    history: list,
    grade: int,
    name: str,
    language: str = "hinglish",
) -> str:
    """
    Conversational intake. Cloud first, Ollama fallback.
    language: "hinglish" | "english"
    """
    base_prompt = _load_system_prompt()
    lang_instruction = (
        "\n\nIMPORTANT: The student has chosen ENGLISH mode. "
        "Reply entirely in clear, warm English."
        if language == "english"
        else "\n\nIMPORTANT: The student has chosen HINGLISH mode. "
        "Mix Hindi and English naturally — like an older sibling. "
        "Write in Roman script (no Devanagari), keep it warm and conversational."
    )
    # Strict speak-tag rule injected at runtime so it always overrides
    speak_rule = (
        "\n\nCRITICAL OUTPUT RULE: Your text response must NEVER contain <speak>, </speak>, "
        "or any XML/SSML tags. The frontend handles TTS separately. "
        "Write your response as plain conversational text only."
    )
    system_prompt = base_prompt + lang_instruction + speak_rule

    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()

    # Build Gemini-format contents, explicitly mapping roles
    contents = []
    for msg in history:
        gemini_role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": gemini_role, "parts": [{"text": msg["content"]}]})
    contents.append(
        {
            "role": "user",
            "parts": [{"text": f"[Student: {name}, Class: {grade}]\n{message}"}],
        }
    )

    if mode == "cloud":
        try:
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            response = client.models.generate_content(
                model=CLOUD_MODEL,
                contents=contents,
                config={"system_instruction": system_prompt},
            )
            return response.text.strip()
        except Exception as e:
            print(f"[AAWAZ/CLOUD] Failed ({e}) ~ falling back to Ollama")

    # Ollama fallback same explicit role mapping
    try:
        ollama_msgs = [{"role": "system", "content": system_prompt}]
        for msg in history:
            ollama_msgs.append(
                {
                    "role": "user" if msg["role"] == "user" else "assistant",
                    "content": msg["content"],
                }
            )
        ollama_msgs.append(
            {
                "role": "user",
                "content": f"[Student: {name}, Class: {grade}]\n{message}",
            }
        )
        response = ollama.chat(model=OFFLINE_MODEL, messages=ollama_msgs)
        return response["message"]["content"].strip()
    except Exception as e2:
        raise RuntimeError(f"Aawaz chat failed (cloud + ollama both down): {e2}")


# Darpan readiness heuristic

_SUBSTANCE_RE = re.compile(
    r"love|hate|passion|interest|hobby|khelna|banana|banata|banati|padhna|likhna"
    r"|papa|mummy|parents|ghar|family|chahte|chahti|bolte|bolti|force|pressure"
    r"|banna|doctor|engineer|artist|teacher|career|future"
    r"|acha lagta|bura lagta|comfortable|nervous|confident|dar|scared"
    r"|sochta|sochti|lagta|lagti|feel|samjha|samjhi|realize|pata chala"
    r"|banaya|banai|project|design|made|built|created|tried|experiment",
    re.IGNORECASE,
)


def is_ready_for_darpan(history: list) -> bool:
    user_msgs = [m for m in history if m["role"] == "user"]
    if len(user_msgs) < 4:
        return False
    total_chars = sum(len(m["content"]) for m in user_msgs)
    if total_chars < 500:
        return False
    avg_len = total_chars / len(user_msgs)
    if avg_len < 60:
        return False
    substance_hits = sum(1 for m in user_msgs if _SUBSTANCE_RE.search(m["content"]))
    return substance_hits >= 2
