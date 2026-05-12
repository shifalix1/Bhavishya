import os
import re
import json
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()


def run_margdarshak(
    question: str,
    identity_json: dict,
    history: list,
    language: str,
    micro_observation: str | None = None,
    identity_callback: str | None = None,
    career_data: list | None = None,
) -> tuple[str, bool]:
    """
    Returns (response_text, is_fallback).
    is_fallback is True only when both cloud and Ollama fail and a canned string is returned.
    The caller should surface is_fallback to the frontend for demo transparency.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(BASE_DIR, "prompts", "margdarshak_prompt.txt")

    with open(prompt_path, encoding="utf-8") as f:
        base_prompt = f.read()

    # Prevent structural labels from leaking into output.
    # The prompt uses headers to describe internal process, not response format.
    behavior_addendum = (
        "\n\nIMPORTANT TONE NOTE: Do NOT use structural headers or numbered labels "
        "like 'VALIDATE FIRST' or 'GAME PLAN' in your actual response. "
        "Those describe your internal process, not your output format. "
        "Write as a single flowing conversation - warm, direct, one idea at a time."
    )

    system_prompt = base_prompt + behavior_addendum

    # Determine whether this is Margdarshak's first response in this conversation.
    # Used by the prompt's FIRST RESPONSE IDENTITY REVEAL instruction.
    is_first_response = not any(m.get("role") == "bhavishya" for m in history)

    context_lines = [
        f"IS_FIRST_RESPONSE: {'yes' if is_first_response else 'no'}",
        f"Student question: {question}",
        f"Detected language: {language}",
        f"Student identity: {json.dumps(identity_json, ensure_ascii=False)}",
        f"Last 5 messages: {json.dumps(history, ensure_ascii=False)}",
    ]

    # Pass Darpan's confidence score so Margdarshak knows how hard to lean on the identity.
    # Low confidence: ask, don't assert. High confidence: speak with conviction.
    confidence = identity_json.get("identity_confidence", 5)
    if confidence <= 4:
        context_lines.append(
            f"\nIdentity confidence is LOW ({confidence}/10): Darpan had limited signal. "
            "Do not make strong claims about who they are. Ask questions instead of stating conclusions. "
            "Treat the identity JSON as a working hypothesis, not a diagnosis."
        )
    elif confidence >= 8:
        context_lines.append(
            f"\nIdentity confidence is HIGH ({confidence}/10): Darpan had rich signal. "
            "You can reference identity traits with conviction. This is a solid picture."
        )

    # If the previous Margdarshak message was heavy (fear, pressure, sacrifice named),
    # instruct a lighter follow-up. Deep observations need breathing room after them.
    last_bhavishya = next(
        (m["content"] for m in reversed(history) if m.get("role") == "bhavishya"),
        None,
    )
    _HEAVY_SIGNAL_RE = re.compile(
        r"fear|contradict|pressure|sacrifice|cost|honest|hard truth|worry|concern"
        r"|tension|gap|conflict|struggle|difficult|painful",
        re.IGNORECASE,
    )
    if last_bhavishya and _HEAVY_SIGNAL_RE.search(last_bhavishya):
        context_lines.append(
            "\nTONE NOTE: Your last response went deep. "
            "This one should be warmer and lighter. One idea, gently. Intelligence needs breathing room."
        )

    # Inject at most one of (micro_observation, identity_callback) per response.
    # Surfacing both in one message makes Bhavishya feel like it is showing off.
    # Prefer callback for returning students where longitudinal memory is the stronger signal.
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
            "Not a data readout. Casual and imprecise, the way real memory works."
        )

    # Inject slim career data for grounding specific answers.
    # Only honest_reality, parent_frame, and ai_disruption are needed here.
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
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=user_msg,
                config={"system_instruction": system_prompt},
            )
            return response.text.strip(), False
        else:
            response = ollama.chat(
                model="gemma4:e4b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            return response["message"]["content"].strip(), False

    except Exception as e:
        print(f"[{mode.upper()} MODE] Margdarshak error: {e}")
        if language == "english":
            fallback = "Give me a second to think about that. What you're asking matters - let's go slow."
        else:
            fallback = "Ek second, yeh sochna chahta hoon. Tumhara sawaal important hai - dhire dhire baat karte hain."
        return fallback, True
