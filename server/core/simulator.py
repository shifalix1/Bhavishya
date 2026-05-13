import os
import re
import json
import copy
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()

_CLOUD_MODEL = "gemma-4-26b-a4b-it"
_OLLAMA_MODEL = "gemma4:e4b"

_PROMPT_CACHE: str | None = None
_GEMINI_CLIENT: genai.Client | None = None

_EXPECTED_TYPES = {"expected", "inner_call", "unseen_door"}

_REQUIRED_FUTURE_FIELDS = [
    "type",
    "title",
    "narrative_2031",
    "career_trajectory",
    "key_decision_point",
    "what_you_gain",
    "what_you_sacrifice",
    "ai_disruption_risk",
    "annual_salary_2031_inr",
    "salary_context",
]

_NON_TECH_SIGNALS = {
    "creative",
    "visual",
    "writing",
    "story",
    "helping",
    "social",
    "art",
    "music",
    "teach",
}

# Generic fallback - fires only when both cloud and Ollama fail.
# Structurally complete so frontend never crashes on a missing field.
_FALLBACK_FUTURES = {
    "futures": [
        {
            "type": "expected",
            "title": "The Safe Road",
            "narrative_2031": (
                "You wake up at 7:15 AM in a one-bedroom flat in Pune. "
                "The alarm cuts through a half-dream. Your body takes a moment to agree to be awake. "
                "Phone screen too bright. You have a deployment review at 10 AM. "
                "You are three years into a software role at a mid-sized IT services company. "
                "Last week you caught a subtle concurrency bug that had been causing random failures "
                "for two months. Your team lead mentioned it in the standup. That felt good, genuinely good. "
                "You take the 8:30 office bus with your earphones in. "
                "The project is not exciting but you are good at it, and being good at something "
                "has its own quiet satisfaction. Lunch is with two colleagues you genuinely like. "
                "You pay your parents home loan EMI every month without having to think about it. "
                "That matters more than you expected it would. "
                "Your cousin got placed at a Hyderabad startup and your chachi mentions the stock options "
                "at every family dinner. Some evenings you open a side project and close it an hour later. "
                "You are not unhappy. The question of whether you made the right choice "
                "comes up less often than it used to."
            ),
            "career_trajectory": "B.Tech -> TCS/Infosys -> mid-level engineer -> team lead",
            "key_decision_point": "Joining coaching in Class 11 because every WhatsApp group in the family treated JEE rank as the only number that mattered.",
            "what_you_gain": "Financial stability, family approval, and the quiet pride of being reliably good at something.",
            "what_you_sacrifice": "By 28, changing direction means explaining it to everyone again. That cost is real.",
            "ai_disruption_risk": "high",
            "annual_salary_2031_inr": 900000,
            "salary_context": "9L pre-tax in Pune is roughly 62-65k take-home, which covers rent and EMI comfortably with some left over.",
        },
        {
            "type": "inner_call",
            "title": "The Thing You Keep Coming Back To",
            "narrative_2031": (
                "You wake up at 9 AM in a shared studio in Bangalore. "
                "No alarm. You feel it before you open your eyes: something to finish today. "
                "On your desk: a sketchbook, three browser tabs with half-finished references, a coffee going cold. "
                "You are a UX designer at a startup building tools for vernacular-language learners. "
                "The product matters to you in a way you can feel. "
                "You pitched two concepts yesterday and one is going into sprint. "
                "Your mother still asks when you are getting a government job. "
                "You have stopped trying to explain and started sending her your work instead. "
                "Last month a user wrote in saying the app helped their daughter prepare for exams in her own language. "
                "You screenshotted it. It is your lockscreen. "
                "Some months are tight. You have learned to live with uncertainty as a texture, not a crisis. "
                "The work feels like yours in a way nothing else has."
            ),
            "career_trajectory": "Design diploma / self-taught -> junior designer -> product designer at impact startup",
            "key_decision_point": "Taking a 6-month design course instead of a JEE drop year, against advice.",
            "what_you_gain": "Work that feels meaningful, creative ownership, a craft that keeps growing.",
            "what_you_sacrifice": "Income stability in your early 20s, family reassurance, a clear conventional path.",
            "ai_disruption_risk": "medium",
            "annual_salary_2031_inr": 780000,
            "salary_context": "7.8L at a startup often comes with ESOP grants that could be worth more if the company grows, though that is not guaranteed.",
        },
        {
            "type": "unseen_door",
            "title": "The Version No One Suggested",
            "narrative_2031": (
                "You wake up at 6 AM in a room that doubles as an edit suite. "
                "The fan hums. You lie there for a moment, aware of what you need to finish today. "
                "You are in the third week of a documentary shoot for a national education NGO. "
                "Your job title is Learning Experience Designer, a role that did not have a name when you were in Class 11. "
                "You build the curriculum structure, write the narrative arc, "
                "and work with animators and educators to make content that actually lands. "
                "It uses everything: your sense of story, your instinct for what confuses people, "
                "your need to make things that feel real. "
                "You got here sideways, through a content internship, then a chance project with a "
                "teacher-training organisation, then a recommendation from someone who noticed you saw things differently. "
                "There was a day, about two years in, when you stopped prefacing your work with apologies. "
                "You just started explaining what you did. That shift happened quietly and changed everything. "
                "No one you went to school with is doing what you do. "
                "Your parents do not fully understand your job title but they have seen the work. "
                "That is enough for now."
            ),
            "career_trajectory": "Content creation -> instructional design -> learning experience at EdTech NGO",
            "key_decision_point": "Treating a college content internship seriously instead of waiting for a conventional offer.",
            "what_you_gain": "A career built from genuine strengths, work that solves real problems, a rare skill profile.",
            "what_you_sacrifice": "A clear answer to what do you do for the first five years. Family reassurance comes late.",
            "ai_disruption_risk": "low",
            "annual_salary_2031_inr": 720000,
            "salary_context": "7.2L at an NGO is below market but many such roles include accommodation, travel, and non-monetary benefits that are hard to price.",
        },
    ],
    "_fallback": True,
}


def _get_fallback_futures(identity_json: dict) -> dict:
    thinking = identity_json.get("thinking_style", "").lower()
    energy = identity_json.get("energy_signature", "").lower()
    if any(w in thinking + energy for w in _NON_TECH_SIGNALS):
        fallback = copy.deepcopy(_FALLBACK_FUTURES)
        fallback["futures"][0]["title"] = "The Conventional Path"
        fallback["futures"][0][
            "career_trajectory"
        ] = "B.Com / BA -> entry-level corporate -> mid-level manager"
        fallback["futures"][0]["narrative_2031"] = (
            "You wake up at 8 AM in a two-bedroom flat you share with a colleague. "
            "Commute is 45 minutes. The job pays reliably and your parents have stopped asking "
            "when you will get settled. You manage a small team now. "
            "The work is not what you imagined when you were seventeen, but it is also not terrible. "
            "You are good at it. Some evenings you open something you made a long time ago "
            "and close it before it asks too much. "
            "The weekend is yours, mostly. You are not unhappy. "
            "You are also not sure this is the right question."
        )
        return fallback
    return _FALLBACK_FUTURES


def _load_prompt() -> str:
    global _PROMPT_CACHE
    if _PROMPT_CACHE is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "prompts", "simulator_prompt.txt")
        with open(path, encoding="utf-8") as f:
            _PROMPT_CACHE = f.read()
    return _PROMPT_CACHE


def _get_client() -> genai.Client:
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _GEMINI_CLIENT


def _fix_narrative_length(futures: list) -> list:
    # Trim narratives over 250 words at the nearest sentence boundary.
    for future in futures:
        narrative = future.get("narrative_2031", "")
        if not narrative:
            continue
        words = narrative.split()
        if len(words) > 250:
            trimmed = " ".join(words[:230])
            cut = trimmed.rfind(".")
            future["narrative_2031"] = (
                trimmed[: cut + 1] if cut > 150 else trimmed + "."
            )
    return futures


def _fill_missing_fields(futures: list) -> list:
    # Guarantee every field exists so frontend never crashes on a missing key.
    for future in futures:
        for field in _REQUIRED_FUTURE_FIELDS:
            if field not in future:
                future[field] = "Information unavailable."
    return futures


def run_simulator(
    identity_json: dict, grade: int, session_count: int, career_data: list
) -> dict:
    system_prompt = _load_prompt()

    # Surface the sharpest identity signals explicitly for the unseen_door anchor.
    bridge_parts = []
    if identity_json.get("thinking_style"):
        bridge_parts.append(f"thinking: {identity_json['thinking_style']}")
    if identity_json.get("energy_signature"):
        bridge_parts.append(f"energy: {identity_json['energy_signature']}")
    if identity_json.get("hidden_strengths"):
        bridge_parts.append(f"hidden strength: {identity_json['hidden_strengths'][0]}")

    identity_bridge = (
        "\n\nFor the unseen_door future, ground it specifically in these identity signals: "
        + " | ".join(bridge_parts)
        if bridge_parts
        else ""
    )

    user_msg = (
        f"Student identity: {json.dumps(identity_json, ensure_ascii=False)}\n"
        f"Current grade: {grade}\n"
        f"Session count: {session_count}\n"
        f"Relevant career data: {json.dumps(career_data, ensure_ascii=False)}"
        f"{identity_bridge}"
    )

    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()
    raw = ""

    try:
        if mode == "cloud":
            response = _get_client().models.generate_content(
                model=_CLOUD_MODEL,
                contents=user_msg,
                config={
                    "system_instruction": system_prompt,
                    "http_options": {"timeout": 45000},
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
            raise ValueError("No JSON object found in simulator response.")
        result = json.loads(match.group(0))

        if "error" in result:
            print(f"[SIMULATOR/{mode.upper()}] Model returned error: {result['error']}")
            return _get_fallback_futures(identity_json)

        futures = result.get("futures", [])
        if len(futures) != 3:
            print(f"[SIMULATOR/{mode.upper()}] Expected 3 futures, got {len(futures)}")
            return _get_fallback_futures(identity_json)

        # Validate all three types are present - count check alone is not enough.
        types_present = {f.get("type") for f in futures}
        if types_present != _EXPECTED_TYPES:
            print(f"[SIMULATOR/{mode.upper()}] Wrong types: {types_present}")
            return _get_fallback_futures(identity_json)

        result["futures"] = _fill_missing_fields(_fix_narrative_length(futures))
        return result

    except json.JSONDecodeError as e:
        print(f"[SIMULATOR/{mode.upper()}] JSON parse failed: {e} | raw: {raw[:200]}")
        return _get_fallback_futures(identity_json)
    except Exception as e:
        print(f"[SIMULATOR/{mode.upper()}] Error: {e}")
        return _get_fallback_futures(identity_json)
