from server.core.memory import load_student, add_message, save_student
from server.core.language import detect_language
from server.core.margdarshak import run_margdarshak

# Load Aryan's profile
profile = load_student("Aryan", 9)

# A classic Indian student question in Hinglish
question = "Mere papa keh rahe hain ki gaming se ghar nahi chalta, mujhe JEE ki tayari shuru karni chahiye. Main kya karu?"

print(f"Aryan asks: {question}")

# 1. Detect Language
lang = detect_language(question)
print(f"Detected Language: {lang}")

# 2. Get recent history
history = profile.get("conversation_history", [])[-5:]

# 3. Call Margdarshak
print("\nThinking...")
response = run_margdarshak(question, profile["identity_current"], history, lang)

print("\n--- MARGDARSHAK REPLIES ---")
print(response)

# 4. Save to memory
profile = add_message(profile, "user", question)
profile = add_message(profile, "bhavishya", response)
save_student(profile)
