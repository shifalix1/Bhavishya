import os
import json
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()


def run_margdarshak(
    question: str, identity_json: dict, history: list, language: str
) -> str:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(BASE_DIR, "prompts", "margdarshak_prompt.txt")

    with open(prompt_path, encoding="utf-8") as f:
        system_prompt = f.read()

    # Build the prompt dynamically
    user_msg = f"""Student question: {question}
Detected language: {language}
Student identity: {json.dumps(identity_json, ensure_ascii=False)}
Last 5 messages: {json.dumps(history, ensure_ascii=False)}"""

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
            # Using gemma2:2b for offline safety
            response = ollama.chat(
                model="gemma2:2b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
            )
            return response["message"]["content"].strip()

    except Exception as e:
        print(f"[{mode.upper()} MODE] Margdarshak error: {e}")
        return "Main abhi process kar raha hoon. Thoda wait karo."
