import os
import json
import ollama
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def run_darpan(student_input: str, grade: int, previous_session: dict = None) -> dict:
    # Loading the system rules
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(BASE_DIR, "prompts", "darpan_prompt.txt")

    with open(prompt_path, encoding="utf-8") as f:
        system_prompt = f.read()

    # Constructing the student's message
    user_msg = f"Grade: {grade}\nStudent says: {student_input}"
    if previous_session:
        user_msg += f"\nPrevious identity snapshot: {json.dumps(previous_session, ensure_ascii=False)}"

    # Checking our execution mode (Default to 'cloud' for fast development)
    mode = os.getenv("BHAVISHYA_MODE", "cloud").lower()

    try:
        if mode == "cloud":
            # HIGH-SPEED API MODE
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=user_msg,
                config={"system_instruction": system_prompt},
            )
            raw = response.text.strip()

        else:
            # OFFLINE EDGE (Fallback)
            response = ollama.chat(
                model="gemma4:2b",  # Using the lightweight model for offline safety (not using 4b model cause computational bottleneck)
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = response["message"]["content"].strip()

        # Clean up any Markdown formatting the LLM might add
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        return json.loads(raw.strip())

    except json.JSONDecodeError as e:
        print(f"[{mode.upper()} MODE] JSON parse failed: {e}\nRaw output: {raw}")
        return {"error": "generation_failed"}
    except Exception as e:
        print(f"[{mode.upper()} MODE] Darpan error: {e}")
        return {"error": str(e)}
