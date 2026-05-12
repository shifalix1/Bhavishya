import json
from server.core.memory import load_student, save_student
from server.core.careers import get_careers_for_identity
from server.core.simulator import run_simulator

print("Loading Aryan's profile...")
# Make sure the grade matches what you saved yesterday
profile = load_student("Aryan", 9)

if not profile or not profile.get("identity_current"):
    print("Could not find Aryan's identity! Did you run test_day1.py successfully?")
else:
    identity = profile["identity_current"]
    print("\nFinding matching careers based on Identity Fingerprint...")

    # Grab the top 3 careers for Aryan
    career_data = get_careers_for_identity(identity, n=3)

    # Print what it found so we can verify the matching logic works
    matched_names = [c.get("name") for c in career_data]
    print(f"Matched Careers: {matched_names}")

    print("\nSimulating Futures in 2031 (Using gemma-4-26b-a4b-it via API)...")
    futures = run_simulator(
        identity_json=identity,
        grade=profile["grade"],
        session_count=profile["session_count"] + 1,  # Simulating session 2
        career_data=career_data,
    )

    print("\n--- SIMULATION RESULTS ---")
    print(json.dumps(futures, indent=2, ensure_ascii=False))

    # Save the futures to the student's profile if successful
    if "error" not in futures:
        if "futures_generated" not in profile:
            profile["futures_generated"] = []

        profile["futures_generated"].append(
            {
                "session": profile["session_count"] + 1,
                "futures": futures.get("futures", []),
            }
        )
        save_student(profile)
        print(f"\nSaved futures to students/{profile['student_id']}.json")
        print("Day 2 complete!")
    else:
        print("\nSimulator failed — check error above.")
