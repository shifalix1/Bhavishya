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
) -> str:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(BASE_DIR, "prompts", "margdarshak_prompt.txt")

    with open(prompt_path, encoding="utf-8") as f:
        base_prompt = f.read()

    # Strip the numbered structure labels from the prompt - behavior-driven only.
    # This prevents the model from outputting "VALIDATE FIRST:" as literal text.
    behavior_addendum = (
        "\n\nIMPORTANT TONE NOTE: Do NOT use structural headers or numbered labels "
        "like 'VALIDATE FIRST' or 'GAME PLAN' in your actual response. "
        "Those describe your internal process, not your output format. "
        "Write as a single flowing conversation - warm, direct, one idea at a time."
    )

    system_prompt = base_prompt + behavior_addendum

    # Build the user message with optional behavioral context
    context_lines = [
        f"Student question: {question}",
        f"Detected language: {language}",
        f"Student identity: {json.dumps(identity_json, ensure_ascii=False)}",
        f"Last 5 messages: {json.dumps(history, ensure_ascii=False)}",
    ]

    # Tell Margdarshak how confident Darpan was - low confidence = don't overclaim
    confidence = identity_json.get("identity_confidence", 5)
    if confidence <= 4:
        context_lines.append(
            f"\nIdentity confidence is LOW ({confidence}/10): Darpan had limited signal from this student. "
            "Do not make strong claims about who they are. Ask questions instead of stating conclusions. "
            "Treat the identity JSON as a working hypothesis, not a diagnosis."
        )
    elif confidence >= 8:
        context_lines.append(
            f"\nIdentity confidence is HIGH ({confidence}/10): Darpan had rich, specific signal. "
            "You can reference identity traits with confidence. This is a solid picture."
        )

    # Detect if the last Bhavishya message was a heavy observation (contradiction,
    # family pressure surfacing, fear naming). If so, instruct a lighter response.
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
            "\nTONE NOTE: Your last response went deep - contradiction, pressure, or fear was named. "
            "This response should be warmer and lighter. One idea, gently. Intelligence needs breathing room."
        )

    # Enforce restraint: inject at most one of (micro_observation, identity_callback)
    # Stacking both makes Bhavishya feel like it's showing off instead of actually listening.
    # Prefer callback for returning students with a clear pattern; observation otherwise.
    if identity_callback and micro_observation:
        # Use callback if this is a returning student (more powerful illusion of memory)
        micro_observation = None

    # Inject micro-observation if available - the "how does it know that?" moment
    if micro_observation:
        context_lines.append(
            f"\nBehavioral observation from this session: {micro_observation}\n"
            "Reference this observation only if it fits naturally into your response. "
            "Do not announce that you observed it - just let it inform what you say."
        )

    # Inject longitudinal callback if this is a returning student
    if identity_callback:
        context_lines.append(
            f"\nMemory callback (returning student): {identity_callback}\n"
            "You may weave this naturally into your response once - "
            "like an older sibling who genuinely remembers. Do not make it feel like a data readout."
        )

    # Inject career dataset moat fields - this is what makes specific answers feel grounded
    # Only include what's actually useful: what_they_dont_tell_you, parent_frame, ai_disruption
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
            "Use this data only when it's directly relevant to the student's question. "
            "When you cite a reality check or parent frame, use the actual language from this data - "
            "not invented generalizations. Never list all careers. One at a time, only if it fits."
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
            return response.text.strip()
        else:
            response = ollama.chat(
                model="gemma4:e4b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            return response["message"]["content"].strip()

    except Exception as e:
        print(f"[{mode.upper()} MODE] Margdarshak error: {e}")
        # Soft fallback - does not expose internal error to student
        if language == "english":
            return "Give me a second to think about that. What you're asking matters - let's go slow."
        return "Ek second, yeh sochna chahta hoon. Tumhara sawaal important hai - dhire dhire baat karte hain."
