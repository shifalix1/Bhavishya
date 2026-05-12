from server.core.darpan import run_darpan
from server.core.memory import load_student, save_student, create_new_profile
import json

from dotenv import load_dotenv

load_dotenv()

name, grade = "Aryan", 9
profile = load_student(name, grade) or create_new_profile(name, grade)

student_input = """I play games 4 hours a day. My dad wants me to be an engineer. 
I don't actually know what engineering is. I made a game in Scratch and showed my class. 
I hate studying at night but I can stay up till 2am gaming."""

prev = profile.get("identity_current") or None
print("Running Darpan...")
identity = run_darpan(student_input, grade, prev)
print(json.dumps(identity, indent=2, ensure_ascii=False))

if "error" not in identity:
    profile["identity_current"] = identity
    profile["identity_history"].append(
        {"session": profile["session_count"] + 1, "snapshot": identity}
    )
    profile["session_count"] += 1
    save_student(profile)
    print(f"\nSaved to students/{profile['student_id']}.json")
    print("\nDay 1 complete if output above has non-generic insights about Aryan.")
else:
    print("\nDarpan failed — check prompt or ollama connection.")
