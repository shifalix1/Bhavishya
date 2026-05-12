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

# Cached at module load - no disk I/O per request
_SYSTEM_PROMPT_CACHE: str | None = None


def _load_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        with open(AAWAZ_PROMPT_PATH, encoding="utf-8") as f:
            raw = f.read()
        # Strip the <speak> block instructions from the prompt entirely.
        # The backend never outputs TTS tags - the frontend layer handles that.
        # Remove the entire TTS RULE section to avoid conflicting instructions.
        raw = re.sub(
            r"1\. THE TTS RULE.*?(?=2\.|\Z)",
            "",
            raw,
            flags=re.DOTALL,
        )
        _SYSTEM_PROMPT_CACHE = raw
    return _SYSTEM_PROMPT_CACHE


def _strip_speak_tags(text: str) -> str:
    """
    Safety net: remove any <speak>...</speak> tags the model still outputs.
    Also strip any stray XML tags that slip through.
    """
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
    Multimodal intake: audio + optional image -> transcript + marksheet_data + image_description.
    Returns image_description for ALL image uploads (not just marksheets).
    Gracefully falls back and never crashes caller.
    Note: transcription is cloud-only (multimodal). Ollama cannot do this.
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
            "2. Regardless of what the image is: do NOT write a general description. "
            "Instead, find 2-3 specific anomalies, unfinished elements, or unexpected choices "
            "in this image - things that are unusual, incomplete, or hard to explain at first glance. "
            "These become conversation hooks, not a summary of what the image is. "
            "Examples of the kind of thing to notice: erased lines left visible, a section that is "
            "more detailed than everything around it, something repeated three times in different ways, "
            "a face left undrawn, a margin note that contradicts the main content, "
            "a process that looks abandoned halfway. "
            "Each anomaly should be one concrete specific observation. "
            "Output under the label: IMAGE_DESCRIPTION: (format: one observation per line, "
            "no analysis, just what you literally see that is unusual)"
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
        print(f"[AAWAZ/TRANSCRIBE] Cloud failed ({e}) - returning text fallback")
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
        next_labels = []
        for label in ("MARKSHEET:", "IMAGE_DESCRIPTION:"):
            if label in raw:
                next_labels.append(raw.index(label))
        t_end = min(next_labels) if next_labels else len(raw)
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
) -> str:
    """
    Conversational intake. Cloud first, Ollama fallback.
    language: "hinglish" | "english"
    """
    base_prompt = _load_system_prompt()
    lang_instruction = (
        "\n\nIMPORTANT: The student has chosen ENGLISH mode. "
        "Reply entirely in clear, warm English. No Hindi mixing."
        if language == "english"
        else "\n\nIMPORTANT: The student has chosen HINGLISH mode. "
        "Mix Hindi and English naturally - like an older sibling texting. "
        "Write in Roman script (no Devanagari), keep it warm and conversational."
    )
    output_rule = (
        "\n\nOUTPUT FORMAT: Plain conversational text only. "
        "No bullet points, no markdown, no XML tags of any kind. "
        "You are texting a teenager, not writing a report."
    )
    system_prompt = base_prompt + lang_instruction + output_rule

    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()

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
            print(f"[AAWAZ/CLOUD] Failed ({e}) - falling back to Ollama")

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
    except Exception as e2:
        raise RuntimeError(f"Aawaz chat failed (cloud + ollama both down): {e2}")


# Darpan readiness - signal-based accumulator replacing the old regex gate

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
    """Score a single message for identity signal richness. Max ~4."""
    score = 0
    if _EMOTIONAL_SIGNAL_RE.search(content):
        score += 1
    if _DESIRE_RE.search(content):
        score += 1
    if _SPECIFICITY_RE.search(content):
        score += 1
    if _FAMILY_PRESSURE_RE.search(content):
        score += 1
    # Bonus for longer messages - detail = openness
    if len(content) > 120:
        score += 1
    return score


def is_ready_for_darpan(history: list) -> bool:
    """
    Signal-based readiness check. Fires earlier for rich inputs, later for sparse ones.
    Minimum: 3 user messages with cumulative signal score >= 5.
    This means a student who says 'papa ne force kiya engineer banne ke liye aur mujhe
    drawing pasand hai' in 3 messages will trigger Darpan correctly.
    """
    user_msgs = [m for m in history if m["role"] == "user"]
    if len(user_msgs) < 3:
        return False

    total_score = sum(_score_message(m["content"]) for m in user_msgs)
    if total_score >= 5:
        return True

    # Fallback: 5+ messages with at least minimal substance is always enough
    if len(user_msgs) >= 5:
        substance = sum(1 for m in user_msgs if len(m["content"]) > 40)
        return substance >= 4

    return False


# Micro-observation extractor - deterministic, zero model cost

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

# Observation confidence levels. Only medium+ surfaces to Margdarshak.
# low = interesting but unconfirmed; medium = seen twice; high = persistent pattern
_CONFIDENCE_LOW = "low"
_CONFIDENCE_MEDIUM = "medium"
_CONFIDENCE_HIGH = "high"


def _observation_confidence(signal_count: int, msg_count: int, recurrences: int) -> str:
    """
    Score an observation's confidence based on how many times the signal appeared,
    across how many messages, and whether it persisted.
    Only medium+ observations should surface to the student.
    """
    if recurrences >= 3 and msg_count >= 5:
        return _CONFIDENCE_HIGH
    if recurrences >= 2 or (signal_count >= 2 and msg_count >= 4):
        return _CONFIDENCE_MEDIUM
    return _CONFIDENCE_LOW


def extract_micro_observations(history: list) -> list[str]:
    """
    Deterministic extraction of behavioral signals from conversation history.
    Returns (text, confidence) tuples internally; only medium/high surfaces.

    Priority order (light to heavy - the light ones land hardest):
    1. Topic recurrence (magical - they didn't know we'd notice)
    2. Pacing change (opening up or pulling back)
    3. Hedging pattern (testing safety)
    4. Enthusiasm shift (energy tells)
    5. Family pressure recurrence (important but expected - goes last)

    Delayed recognition: observations are only generated after enough messages
    to confirm the pattern. Early firing = accidental fake profundity.
    """
    user_msgs = [m for m in history if m["role"] == "user"]
    n = len(user_msgs)
    if n < 3:
        return []

    observations = []  # (text, confidence)
    recent = user_msgs[-5:]

    # 1. TOPIC RECURRENCE - lightest, most magical observation
    # Only fires after 4+ messages so pattern is real, not coincidence
    if n >= 4:
        all_words: dict[str, int] = {}
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
        for m in user_msgs:
            words = m["content"].lower().split()
            for w in words:
                clean = w.strip(".,!?\"'")
                if len(clean) > 3 and clean not in stop_words:
                    all_words[clean] = all_words.get(clean, 0) + 1

        # Sort by count descending; pick most recurrent
        recurring = sorted(
            [(w, c) for w, c in all_words.items() if c >= 3],
            key=lambda x: x[1],
            reverse=True,
        )
        if recurring:
            top_word, top_count = recurring[0]
            conf = _observation_confidence(1, n, top_count)
            if conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
                # Delayed phrasing: sounds like we just noticed, not like we were tracking
                if n >= 6:
                    text = (
                        f"Actually - you've brought up '{top_word}' a few times now. "
                        "Not sure if you noticed that."
                    )
                else:
                    text = f"'{top_word}' keeps coming up. You haven't been asked about it directly."
                observations.append((text, conf))

    # 2. PACING CHANGE - message length trend
    lengths = [len(m["content"]) for m in recent]
    if len(lengths) >= 3:
        if lengths[-1] > lengths[0] * 1.6:
            conf = _observation_confidence(1, n, 1)
            # Only fires at medium+ i.e. after enough messages to be sure
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

    # 3. HEDGING PATTERN - softening before committing
    hedge_msgs = [m for m in recent if _HEDGE_RE.search(m["content"])]
    hedge_count = len(hedge_msgs)
    if hedge_count >= 2:
        conf = _observation_confidence(hedge_count, n, hedge_count)
        if conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
            observations.append(
                ("You keep almost saying something, then pulling back a little.", conf)
            )

    # 4. ENTHUSIASM SHIFT - where energy actually is
    enthusiasm_msgs = [m for m in recent if _ENTHUSIASM_RE.search(m["content"])]
    enthusiasm_count = len(enthusiasm_msgs)
    if enthusiasm_count >= 2:
        conf = _observation_confidence(enthusiasm_count, n, enthusiasm_count)
        if conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
            observations.append(
                (
                    "The way you write changes on certain topics. That's hard to fake.",
                    conf,
                )
            )

    # 5. FAMILY PRESSURE - last, because it's the one they already know about
    family_mentions = sum(
        1 for m in user_msgs if _FAMILY_PRESSURE_RE.search(m["content"])
    )
    if family_mentions >= 3:
        conf = _observation_confidence(family_mentions, n, family_mentions)
        if conf in (_CONFIDENCE_MEDIUM, _CONFIDENCE_HIGH):
            observations.append(
                (
                    "Your family keeps coming into it even when you're talking about other things.",
                    conf,
                )
            )

    # Return only text of medium/high confidence observations (already filtered above)
    # Strip confidence tuples for backward compat with caller
    return [text for text, _ in observations]


# Family pressure regex reused from scoring
_FAMILY_PRESSURE_RE_OBS = re.compile(
    r"papa|mummy|mom|dad|parents|ghar|family|bolte|bolti|force|pressure"
    r"|chahte hain|chahti hain|expect|they want|unhe chahiye",
    re.IGNORECASE,
)
