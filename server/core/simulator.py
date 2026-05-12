import os
import re
import json
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Hardcoded demo-safe fallback futures. Used when both cloud and Ollama fail.
# These are generic but structurally correct - they will never show a raw error in the demo.
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
                "for two months. Your team lead mentioned it in the standup. That felt good, "
                "genuinely good. You take the 8:30 office bus with your earphones in. "
                "The project is not exciting but you are good at it, and being good at something "
                "has its own quiet satisfaction. Lunch is with two colleagues you genuinely like. "
                "You pay your parents' home loan EMI every month without having to think about it. "
                "That matters more than you expected it would. "
                "Your cousin got placed at a Hyderabad startup and your chachi mentions the stock options "
                "at every family dinner. Some evenings you open a side project and close it an hour later. "
                "You are not unhappy. The question of whether you made the right choice "
                "comes up less often than it used to."
            ),
            "career_trajectory": "B.Tech -> TCS/Infosys -> Mid-level engineer -> Team lead",
            "key_decision_point": "Joining coaching in Class 11 because every WhatsApp group in the family treated JEE rank as the only number that mattered.",
            "what_you_gain": "Financial stability, family approval, and the quiet pride of being reliably good at something.",
            "what_you_sacrifice": "By 28, changing direction means explaining it to everyone again. That cost is real.",
            "ai_disruption_risk": "high",
            "annual_salary_2031_inr": 900000,
            "salary_context": "9L pre-tax in Pune is roughly 62-65k take-home after deductions, which covers rent and EMI comfortably with some left over.",
        },
        {
            "type": "inner_call",
            "title": "The Thing You Keep Coming Back To",
            "narrative_2031": (
                "You wake up at 9 AM in a shared studio in Bangalore. "
                "No alarm set. You feel it before you open your eyes: something to finish today. "
                "On your desk is a sketchbook, three browser tabs with half-finished references, "
                "and a coffee going cold. You are a UX designer at a startup that builds tools "
                "for vernacular-language learners. The product matters to you in a way you can feel. "
                "You pitched two concepts to the team yesterday and one of them is going into sprint. "
                "Your mother still asks when you are getting a government job. "
                "You have stopped trying to explain and started sending her your work instead. "
                "Last month a user wrote in saying the app helped their daughter prepare for exams "
                "in her own language. You screenshotted it. It is your lockscreen. "
                "Some months are tight. You have learned to live with uncertainty as a texture, "
                "not a crisis. The work feels like yours in a way nothing else has."
            ),
            "career_trajectory": "Design diploma / self-taught -> junior designer -> product designer at impact startup",
            "key_decision_point": "Taking a 6-month design course instead of JEE drop year, against advice.",
            "what_you_gain": "Work that feels meaningful, creative ownership, a craft that keeps growing.",
            "what_you_sacrifice": "Income stability in your early 20s, family reassurance, a clear conventional path.",
            "ai_disruption_risk": "medium",
            "annual_salary_2031_inr": 780000,
            "salary_context": "7.8L at a startup often comes with ESOP grants that could be worth significantly more if the company grows, though that is not guaranteed.",
        },
        {
            "type": "unseen_door",
            "title": "The Version No One Suggested",
            "narrative_2031": (
                "You wake up at 6 AM in a room that doubles as an edit suite. "
                "The fan hums. You lie there for a moment, aware of exactly what you need to finish today. "
                "You are in the third week of a documentary shoot for a national education NGO. "
                "Your job title is Learning Experience Designer: a role that did not have a name "
                "when you were in Class 11. You build the curriculum structure, write the narrative arc, "
                "and work with animators and educators to make content that actually lands. "
                "It uses everything: your sense of story, your instinct for what confuses people, "
                "your need to make things that feel real. "
                "You got here sideways: through a content internship, then a chance project with a "
                "teacher-training organisation, then a recommendation from someone who noticed you "
                "saw things differently. "
                "There was a day, about two years in, when you stopped prefacing your work with apologies. "
                "You just started explaining what you did. That shift happened quietly and it changed everything. "
                "No one you went to school with is doing what you do. "
                "Your parents do not fully understand your job title but they have seen the work. "
                "That is enough for now."
            ),
            "career_trajectory": "Content creation -> instructional design -> learning experience at EdTech NGO",
            "key_decision_point": "Treating a college content internship seriously instead of waiting for a conventional offer.",
            "what_you_gain": "A career built from genuine strengths, work that solves real problems, a rare skill profile.",
            "what_you_sacrifice": "A clear answer to what do you do for the first five years. Family reassurance comes late, not early.",
            "ai_disruption_risk": "low",
            "annual_salary_2031_inr": 720000,
            "salary_context": "7.2L at an NGO is lower than market, but many such roles include accommodation, travel, and strong non-monetary benefits that are hard to price.",
        },
    ],
    "_fallback": True,
}


def _get_fallback_futures(identity_json: dict) -> dict:
    """
    Returns fallback futures. Attempts minimal personalization from identity
    so demo doesn't feel completely generic even on model failure.
    """
    # Check if identity suggests non-engineering path - avoid generic "software job" fallback
    thinking = identity_json.get("thinking_style", "").lower()
    energy = identity_json.get("energy_signature", "").lower()
    non_tech_signals = any(
        w in thinking + energy
        for w in [
            "creative",
            "visual",
            "writing",
            "story",
            "helping",
            "social",
            "art",
            "music",
            "teach",
        ]
    )
    if non_tech_signals:
        # Swap expected path to something non-IT
        import copy

        fallback = copy.deepcopy(_FALLBACK_FUTURES)
        fallback["futures"][0]["title"] = "The Conventional Path"
        fallback["futures"][0][
            "career_trajectory"
        ] = "B.Com / BA -> entry-level corporate role -> mid-level manager"
        fallback["futures"][0]["narrative_2031"] = (
            "You wake up at 8 AM in a two-bedroom flat you share with a colleague. "
            "Your commute is 45 minutes. The job pays reliably and your parents have stopped asking "
            "when you will get settled. You manage a small team now. The work is not what you imagined "
            "when you were seventeen, but it is also not terrible. You are good at it. "
            "Some evenings you open something you made a long time ago and close it before it asks too much. "
            "The weekend is yours, mostly. You are not unhappy. You are also not sure this is the right question."
        )
        return fallback
    return _FALLBACK_FUTURES


def _validate_and_fix_narrative_length(futures: list) -> list:
    """
    Validates narrative word count is in 150-250 range.
    Trims at sentence boundary if too long. Does not pad if too short.
    """
    for future in futures:
        narrative = future.get("narrative_2031", "")
        if not narrative:
            continue
        words = narrative.split()
        if len(words) > 250:
            trimmed = " ".join(words[:230])
            last_period = trimmed.rfind(".")
            if last_period > 150:
                future["narrative_2031"] = trimmed[: last_period + 1]
            else:
                future["narrative_2031"] = trimmed + "."
    return futures


def run_simulator(
    identity_json: dict, grade: int, session_count: int, career_data: list
) -> dict:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(BASE_DIR, "prompts", "simulator_prompt.txt")

    with open(prompt_path, encoding="utf-8") as f:
        system_prompt = f.read()

    # Build identity bridge for unseen_door - surface the two most specific signals
    # so the model has explicit anchors and doesn't invent a generic surprising career
    bridge_signals = []
    if identity_json.get("thinking_style"):
        bridge_signals.append(f"thinking: {identity_json['thinking_style']}")
    if identity_json.get("energy_signature"):
        bridge_signals.append(f"energy: {identity_json['energy_signature']}")
    if identity_json.get("hidden_strengths"):
        bridge_signals.append(
            f"hidden strength: {identity_json['hidden_strengths'][0]}"
        )

    identity_bridge = (
        f"\n\nFor the unseen_door future, ground it specifically in these identity signals: "
        + " | ".join(bridge_signals)
        if bridge_signals
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
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=user_msg,
                config={"system_instruction": system_prompt},
            )
            raw = response.text.strip()
        else:
            response = ollama.chat(
                model="gemma4:e4b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = response["message"]["content"].strip()

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        else:
            raise ValueError("No JSON object found in simulator response.")

        result = json.loads(raw)

        if "error" in result:
            print(f"[{mode.upper()} MODE] Simulator returned error: {result['error']}")
            return _get_fallback_futures(identity_json)

        if "futures" not in result or len(result["futures"]) != 3:
            print(f"[{mode.upper()} MODE] Simulator wrong future count, using fallback")
            return _get_fallback_futures(identity_json)

        # Validate and fix narrative lengths in-place
        result["futures"] = _validate_and_fix_narrative_length(result["futures"])

        # Ensure all required fields exist in each future
        required_fields = [
            "type",
            "title",
            "narrative_2031",
            "career_trajectory",
            "key_decision_point",
            "what_you_gain",
            "what_you_sacrifice",
            "ai_disruption_risk",
            "annual_salary_2031_inr",
        ]
        for future in result["futures"]:
            for field in required_fields:
                if field not in future:
                    future[field] = "Information unavailable."

        return result

    except json.JSONDecodeError as e:
        print(
            f"[{mode.upper()} MODE] Simulator JSON parse failed: {e}\nRaw: {raw[:300]}"
        )
        return _get_fallback_futures(identity_json)
    except Exception as e:
        print(f"[{mode.upper()} MODE] Simulator error: {e}")
        return _get_fallback_futures(identity_json)
