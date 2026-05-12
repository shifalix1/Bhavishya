import os
import re
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AAWAZ_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "aawaz_prompt.txt")

CLOUD_MODEL = "gemma-4-26b-a4b-it"
OFFLINE_MODEL = "gemma4:e4b"

_SYSTEM_PROMPT_CACHE: str | None = None


def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        with open(AAWAZ_PROMPT_PATH, encoding="utf-8") as f:
            _SYSTEM_PROMPT_CACHE = f.read()
    return _SYSTEM_PROMPT_CACHE


def _strip_speak_tags(text: str) -> str:
    """Remove any <speak> tags the model produces. The frontend handles TTS; we send plain text."""
    text = re.sub(r"<speak>.*?</speak>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</?speak>", "", text, flags=re.IGNORECASE)
    return text.strip()


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
    Multimodal intake via Gemma 4 cloud (cloud-only, no Ollama fallback for multimodal).
    Returns: transcript, marksheet_data, image_description, combined_input, mode.
    image_description contains 2-3 specific anomalies extracted from the uploaded image.
    These become conversation hooks for Aawaz and identity signal for Darpan.
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
            "'Subject: marks/total' one per line, plus class, school, year if visible. "
            "Output under the label: MARKSHEET:\n"
            "2. Regardless of image type: find 2-3 specific anomalies, unfinished elements, "
            "or unexpected choices that are unusual or hard to explain at first glance. "
            "These are conversation hooks, not a summary. "
            "Examples: erased lines left visible, one section far more detailed than the rest, "
            "something repeated in different ways, a face left undrawn, a margin note that "
            "contradicts the main content, a process abandoned halfway. "
            "Each observation must be one concrete specific thing you literally see. "
            "Output under the label: IMAGE_DESCRIPTION: (one observation per line, no analysis)"
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
        print(f"[AAWAZ/TRANSCRIBE] Cloud failed: {e} - returning text fallback")
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

    if "TRANSCRIPT:" in raw:
        t_start = raw.index("TRANSCRIPT:") + len("TRANSCRIPT:")
        next_label_positions = [
            raw.index(label)
            for label in ("MARKSHEET:", "IMAGE_DESCRIPTION:")
            if label in raw
        ]
        t_end = min(next_label_positions) if next_label_positions else len(raw)
        transcript = raw[t_start:t_end].strip()
    elif not image_b64:
        transcript = raw

    if "MARKSHEET:" in raw:
        m_start = raw.index("MARKSHEET:") + len("MARKSHEET:")
        m_end = (
            raw.index("IMAGE_DESCRIPTION:") if "IMAGE_DESCRIPTION:" in raw else len(raw)
        )
        marksheet_data = raw[m_start:m_end].strip() or None

    if "IMAGE_DESCRIPTION:" in raw:
        d_start = raw.index("IMAGE_DESCRIPTION:") + len("IMAGE_DESCRIPTION:")
        image_description = raw[d_start:].strip() or None

    # Image-only upload: transcript comes from text fallback, not audio
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
    language: str = "english",
    image_anomalies: str | None = None,
) -> str:
    """
    Single conversational turn. Cloud first, Ollama fallback.
    image_anomalies: the IMAGE_DESCRIPTION string from a prior transcribe call.
    Injected into the system prompt so Aawaz can reference the uploaded artifact
    in follow-up questions naturally, without re-sending the image every turn.
    """
    base_prompt = _load_system_prompt()

    lang_instruction = (
        "\n\nIMPORTANT: Student is in ENGLISH mode. "
        "Reply entirely in clear, warm English. No Hindi mixing."
        if language == "english"
        else "\n\nIMPORTANT: Student is in HINGLISH mode. "
        "Mix Hindi and English naturally like an older sibling texting. "
        "Roman script only, no Devanagari. Keep it warm and casual."
    )

    output_rule = (
        "\n\nOUTPUT FORMAT: Plain conversational text only. "
        "No bullet points, no markdown, no XML tags of any kind. "
        "You are texting a teenager, not writing a report."
    )

    # Inject image anomalies as system context so Aawaz can reference the artifact
    # in follow-up questions. Only active for the first 6 exchanges to stay fresh.
    image_context = ""
    if image_anomalies:
        user_turn_count = sum(1 for m in history if m.get("role") == "user")
        if user_turn_count < 6:
            image_context = (
                f"\n\nIMAGE CONTEXT (from student's earlier upload): {image_anomalies}\n"
                "Reference these specific observations naturally if relevant, "
                "like you've been thinking about what they showed you. "
                "Do not announce that you're referencing the image. "
                "Do not analyse it. Let a specific detail inform one question."
            )

    system_prompt = base_prompt + lang_instruction + output_rule + image_context

    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()

    # Build conversation history in Gemini multi-turn format
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
            return _strip_speak_tags(response.text.strip())
        except Exception as e:
            print(f"[AAWAZ/CLOUD] Failed: {e} - falling back to Ollama")

    # Ollama fallback
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
        return _strip_speak_tags(response["message"]["content"].strip())
    except Exception as e:
        raise RuntimeError(f"Aawaz chat failed (cloud + Ollama both down): {e}")


# Darpan readiness - signal accumulator, not a message count gate

_EMOTIONAL_SIGNAL_RE = re.compile(
    r"papa|mummy|parents|ghar|family|chahte|chahti|force|pressure|banna"
    r"|doctor|engineer|artist|teacher|career|future|dream|sapna"
    r"|love|hate|scared|dar|nervous|excited|proud|ashamed|guilty"
    r"|want|don't want|nahi chahta|nahi chahti|mujhe lagna|main sochta|main sochti",
    re.IGNORECASE,
)

_DESIRE_RE = re.compile(
    r"want|wish|dream|chahta|chahti|banna chahta|banna chahti"
    r"|interest|hobby|passion|enjoy|love doing|mujhe pasand|acha lagta",
    re.IGNORECASE,
)

_SPECIFICITY_RE = re.compile(
    r"drawing|coding|music|cricket|dance|writing|gaming|cooking|design"
    r"|math|science|history|art|sport|youtube|content|video|photo"
    r"|banaya|banai|project|made|built|created|tried|experiment"
    r"|certificate|won|competition|rank|score|marks",
    re.IGNORECASE,
)

_FAMILY_PRESSURE_RE = re.compile(
    r"papa|mummy|mom|dad|parents|ghar|family|bolte|bolti|force|pressure"
    r"|chahte hain|chahti hain|expect|they want|unhe chahiye",
    re.IGNORECASE,
)


def _score_message(content: str) -> int:
    """Score a single message for identity signal richness. Max 5 points."""
    score = 0
    if _EMOTIONAL_SIGNAL_RE.search(content):
        score += 1
    if _DESIRE_RE.search(content):
        score += 1
    if _SPECIFICITY_RE.search(content):
        score += 1
    if _FAMILY_PRESSURE_RE.search(content):
        score += 1
    if len(content) > 120:
        score += 1
    return score


def is_ready_for_darpan(history: list) -> bool:
    """
    Signal-based readiness gate. Fires earlier for rich inputs, later for sparse ones.
    Minimum: 3 user messages with cumulative signal score >= 5.
    Hard fallback: 5+ substantive user messages is always enough regardless of score.
    """
    user_msgs = [m for m in history if m["role"] == "user"]
    if len(user_msgs) < 3:
        return False

    total_score = sum(_score_message(m["content"]) for m in user_msgs)
    if total_score >= 5:
        return True

    if len(user_msgs) >= 5:
        substantive = sum(1 for m in user_msgs if len(m["content"]) > 40)
        return substantive >= 4

    return False


# Micro-observation extractor - deterministic behavioral signal detection, zero model cost

_HEDGE_RE = re.compile(
    r"\bbut\b|\bactually\b|\bi mean\b|\bi don'?t know\b|\bmaybe\b|\bsort of\b"
    r"|\bkind of\b|\bnot sure\b|\bpata nahi\b|\bshayad\b|\blagta hai\b",
    re.IGNORECASE,
)

_ENTHUSIASM_RE = re.compile(
    r"!|\byaar\b|\bomg\b|\bwow\b|\bhaha\b|\blol\b|\bso cool\b|\blovee\b"
    r"|\bbahut acha\b|\bbohot acha\b|\bkya baat\b",
    re.IGNORECASE,
)

_CONFIDENCE_MEDIUM = "medium"
_CONFIDENCE_HIGH = "high"


def _obs_confidence(signal_count: int, msg_count: int, recurrences: int) -> str:
    if recurrences >= 3 and msg_count >= 5:
        return _CONFIDENCE_HIGH
    if recurrences >= 2 or (signal_count >= 2 and msg_count >= 4):
        return _CONFIDENCE_MEDIUM
    return "low"


def extract_micro_observations(history: list) -> list[str]:
    """
    Detect behavioral patterns in conversation history without any model call.
    Returns medium/high confidence observations only, in priority order:
    topic recurrence, pacing change, hedging, enthusiasm shift, family pressure.
    Only medium/high confidence observations are returned to avoid noise.
    """
    user_msgs = [m for m in history if m["role"] == "user"]
    n = len(user_msgs)
    if n < 3:
        return []

    observations = []
    recent = user_msgs[-5:]

    # Topic recurrence: a non-stop word appearing 3+ times is almost never accidental
    if n >= 4:
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "it",
            "i",
            "my",
            "and",
            "or",
            "to",
            "of",
            "in",
            "that",
            "this",
            "for",
            "on",
            "with",
            "are",
            "was",
            "be",
            "but",
            "just",
            "hoon",
            "hai",
            "hain",
            "aur",
            "toh",
            "par",
            "bhi",
            "yeh",
            "woh",
            "main",
            "kya",
            "nahi",
            "mujhe",
            "iska",
            "uska",
            "kuch",
            "koyi",
            "waise",
            "like",
            "dont",
            "can",
            "want",
            "know",
            "think",
            "really",
        }
        word_counts: dict[str, int] = {}
        for m in user_msgs:
            for w in m["content"].lower().split():
                clean = w.strip(".,!?\"'")
                if len(clean) > 3 and clean not in stop_words:
                    word_counts[clean] = word_counts.get(clean, 0) + 1

        recurring = sorted(
            [(w, c) for w, c in word_counts.items() if c >= 3],
            key=lambda x: x[1],
            reverse=True,
        )
        if recurring:
            top_word, top_count = recurring[0]
            conf = _obs_confidence(1, n, top_count)
            if conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
                text = (
                    f"Actually - you've brought up '{top_word}' a few times now. "
                    "Not sure if you noticed that."
                    if n >= 6
                    else f"'{top_word}' keeps coming up. You haven't been asked about it directly."
                )
                observations.append((text, conf))

    # Pacing change: message length growing = opening up, shrinking = pulling back
    lengths = [len(m["content"]) for m in recent]
    if len(lengths) >= 3:
        if lengths[-1] > lengths[0] * 1.6:
            conf = _obs_confidence(1, n, 1)
            if n >= 5 and conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
                observations.append(
                    (
                        "You started short. You're saying a lot more now.",
                        _CONFIDENCE_MEDIUM,
                    )
                )
        elif lengths[-1] < lengths[0] * 0.5 and n >= 5:
            observations.append(
                (
                    "You were saying more a little while ago. Something shifted.",
                    _CONFIDENCE_MEDIUM,
                )
            )

    # Hedging: pulling back before committing to a statement
    hedge_count = sum(1 for m in recent if _HEDGE_RE.search(m["content"]))
    if hedge_count >= 2:
        conf = _obs_confidence(hedge_count, n, hedge_count)
        if conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
            observations.append(
                ("You keep almost saying something, then pulling back a little.", conf)
            )

    # Enthusiasm shift: energy changes on specific topics
    enthusiasm_count = sum(1 for m in recent if _ENTHUSIASM_RE.search(m["content"]))
    if enthusiasm_count >= 2:
        conf = _obs_confidence(enthusiasm_count, n, enthusiasm_count)
        if conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
            observations.append(
                (
                    "The way you write changes on certain topics. That's hard to fake.",
                    conf,
                )
            )

    # Family pressure recurrence: they keep bringing it back unprompted
    family_count = sum(1 for m in user_msgs if _FAMILY_PRESSURE_RE.search(m["content"]))
    if family_count >= 3:
        conf = _obs_confidence(family_count, n, family_count)
        if conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
            observations.append(
                (
                    "Your family keeps coming into it even when you're talking about other things.",
                    conf,
                )
            )

    return [text for text, _ in observations]
