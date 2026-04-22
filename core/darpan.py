import ollama, json


def run_darpan(student_input: str, grade: int, previous_session: dict = None) -> dict:
    with open("prompts/darpan_prompt.txt", encoding="utf-8") as f:
        system_prompt = f.read()

    user_msg = f"Grade: {grade}\nStudent says: {student_input}"
    if previous_session:
        user_msg += f"\nPrevious identity snapshot: {json.dumps(previous_session, ensure_ascii=False)}"

    try:
        response = ollama.chat(
            model="gemma4:4b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = response["message"]["content"].strip()
        # Strip markdown if model wraps it anyway
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"JSON parse failed: {e}\nRaw output: {raw}")
        return {"error": "generation_failed"}
    except Exception as e:
        print(f"Darpan error: {e}")
        return {"error": str(e)}
