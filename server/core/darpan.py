import os
import re
import json
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Hardcoded demo-safe fallback identity. Used when both cloud and Ollama fail.
# Prevents the demo from showing a raw error state.
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


def run_darpan(student_input: str, grade: int, previous_session: dict = None) -> dict:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(BASE_DIR, "prompts", "darpan_prompt.txt")

    with open(prompt_path, encoding="utf-8") as f:
        base_prompt = f.read()

    system_prompt = base_prompt

    user_msg = f"Grade: {grade}\nStudent says: {student_input}"
    if previous_session:
        # Exclude the _fallback flag from previous session context
        clean_prev = {k: v for k, v in previous_session.items() if k != "_fallback"}
        user_msg += f"\nPrevious identity snapshot: {json.dumps(clean_prev, ensure_ascii=False)}"

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
            raise ValueError("No JSON object found in darpan response.")

        result = json.loads(raw)

        # Validate required keys exist
        required = [
            "thinking_style",
            "core_values",
            "hidden_strengths",
            "active_fears",
            "energy_signature",
            "identity_confidence",
        ]
        for key in required:
            if key not in result:
                raise ValueError(f"Missing required key: {key}")

        return result

    except json.JSONDecodeError as e:
        print(f"[{mode.upper()} MODE] Darpan JSON parse failed: {e}\nRaw: {raw[:300]}")
        return _FALLBACK_IDENTITY
    except ValueError as e:
        print(f"[{mode.upper()} MODE] Darpan schema validation failed: {e}")
        return _FALLBACK_IDENTITY
    except Exception as e:
        print(f"[{mode.upper()} MODE] Darpan error: {e}")
        return _FALLBACK_IDENTITY
