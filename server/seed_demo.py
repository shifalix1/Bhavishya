"""
seed_demo.py

Run once before the hackathon demo to create pre-seeded accounts.
Place this file in the project root and run: python seed_demo.py

Creates two accounts:
  demo_aryan  PIN: 1234  Class 11, engineering pressure, hardware builder identity
  demo_priya  PIN: 1234  Class 10, doctor pressure, systems thinker identity

Both have 2 sessions of history so on first login:
  - identity_callback fires immediately (longitudinal memory is visible to judges)
  - identity_delta is populated (change detection is demonstrable)
  - futures_generated is non-empty (simulator output is available without waiting)
  - micro_observations are seeded (behavioral pattern detection is visible)

Demo order: start with demo_aryan. The hardware-vs-engineering tension
is faster to explain to a judge in under 3 minutes.
"""

import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.memory import (
    create_new_profile,
    save_student,
    add_micro_observation,
    _path_by_username,
)


def _delete_if_exists(username: str) -> None:
    """Remove stale demo JSON so re-runs always produce fresh bcrypt hashes."""
    path = _path_by_username(username)
    if os.path.exists(path):
        os.remove(path)
        print(f"  Removed stale file: {path}")


def _now() -> str:
    return str(datetime.now())


def seed_aryan():
    _delete_if_exists("demo_aryan")
    profile = create_new_profile(
        name="Aryan",
        grade=11,
        uid="demo_aryan",
        username="demo_aryan",
        pin="1234",
    )

    session1 = {
        "thinking_style": "Learns by assembling things rather than reading instructions: needs to see how the parts connect before the purpose makes sense.",
        "core_values": ["independence", "making", "honesty"],
        "hidden_strengths": [
            "Unusually good at noticing when a system has a flaw before it breaks.",
            "Works much harder on self-chosen problems than on assigned ones.",
        ],
        "active_fears": [
            "Choosing engineering because everyone expects it, not because he wants it.",
            "Being stuck in a job that feels like homework forever.",
        ],
        "family_pressure_map": "Father expects JEE. The word 'engineer' appears in the family like a given, not a question.",
        "energy_signature": "Comes alive when given a broken thing to fix or an open-ended build challenge with no single right answer.",
        "identity_confidence": 6,
        "changed_since_last": False,
        "change_summary": "",
    }

    session2 = {
        "thinking_style": "Learns by assembling things rather than reading instructions: needs to see how the parts connect before the purpose makes sense.",
        "core_values": ["independence", "making", "creative_control"],
        "hidden_strengths": [
            "Unusually good at noticing when a system has a flaw before it breaks.",
            "Works much harder on self-chosen problems than on assigned ones.",
        ],
        "active_fears": [
            "Choosing engineering because everyone expects it, not because he wants it.",
            "Ending up competent but bored.",
        ],
        "family_pressure_map": "Father expects JEE. JEE rank is treated as the only number that matters in family WhatsApp groups.",
        "energy_signature": "Comes alive when given a broken thing to fix or an open-ended build challenge with no single right answer.",
        "identity_confidence": 8,
        "changed_since_last": True,
        "change_summary": "Fear is more specific now: not 'wrong career' but 'ending up competent but bored'.",
    }


    # Session 3 — fear resolved, confidence peak, family conversation shifted
    session3 = {
        "thinking_style": "Learns by assembling things rather than reading instructions: needs to see how the parts connect before the purpose makes sense. Now explicitly aware of this pattern in himself.",
        "core_values": ["independence", "making", "creative_control"],
        "hidden_strengths": [
            "Unusually good at noticing when a system has a flaw before it breaks.",
            "Works much harder on self-chosen problems than on assigned ones.",
            "Can hold a complex physical system in his head and reason about failure modes before touching it.",
        ],
        "active_fears": [
            "Ending up competent but bored.",
        ],
        "family_pressure_map": "Father expects JEE. The conversation has shifted — Aryan has started framing ECE as 'engineering with hardware focus' rather than 'not JEE'. Father is now listening.",
        "energy_signature": "Comes alive when given a broken thing to fix or an open-ended build challenge with no single right answer.",
        "identity_confidence": 9,
        "changed_since_last": True,
        "change_summary": "Fear of 'choosing the wrong career' is resolved. Remaining fear is more specific: competence without meaning. Family conversation has moved from resistance to negotiation.",
    }

    profile["session_count"] = 3
    profile["identity_current"] = session3
    profile["identity_history"] = [
        {"session": 1, "snapshot": session1},
        {"session": 2, "snapshot": session2},
        {"session": 3, "snapshot": session3},
    ]
    profile["last_session"] = str(date.today())

    # InsightBanner reads these two fields — populated at login time
    profile["identity_delta"] = {
        "previous_confidence": 8,
        "current_confidence": 9,
        "resolved_fears": ["Choosing engineering because everyone expects it, not because he wants it."],
        "new_strengths": ["Can hold a complex physical system in his head and reason about failure modes before touching it."],
    }
    profile["last_session_summary"] = {
        "has_new_move": True,
        "session_index": 3,
        "one_line": "Fear of wrong career resolved. Margdarshak has a new move for you.",
    }

    profile["aawaz_history"] = [
        {
            "role": "aawaz",
            "content": "Family hamesha safe option chahti hai, I get it. Par sach bata - jab koi nahi dekh raha hota, toh tu kya karta hai?",
        },
        {
            "role": "user",
            "content": "main usually kuch banata hoon. arduino pe projects ya phir phone repair karta hoon dosto ke liye. kal ek speaker fix kiya",
        },
        {
            "role": "aawaz",
            "content": "Speaker fix kiya - that's not random tinkering. Woh specific diagnosis tha. Tune kya dekha tha jo baki ne miss kiya?",
        },
        {
            "role": "user",
            "content": "dust tha woofer mein, obvious tha par nobody checked. mujhe ye cheezein dikhti hain jaldi",
        },
        {
            "role": "aawaz",
            "content": "Aur engineering mein kya lagta hai tujhe? Woh feeling jo speaker fix karte waqt aayi, woh wahan bhi aayegi?",
        },
        {
            "role": "user",
            "content": "pata nahi yaar. coding bhi try ki hai, thoda boring lagi theory mein. hardware zyada interesting hai",
        },
        {
            "role": "aawaz",
            "content": "Hardware interesting hai - that's already more specific than most people your age know about themselves. Kab se hai yeh?",
        },
    ]

    profile["conversation_history"] = [
        {
            "role": "user",
            "content": "main hardware mein jaana chahta hoon but papa bol rahe hain software hi karo, zyada scope hai",
            "timestamp": _now(),
        },
        {
            "role": "bhavishya",
            "content": "Jo cheez tune speaker mein dekhi - woh diagnostic instinct hai. Hardware aur software dono mein lagti hai. Embedded systems engineers exactly yahi karte hain: hardware aur software ka intersection. Scope waali baat pe papa galat nahi hain, but scope sirf ek cheez mein nahi hoti.",
            "timestamp": _now(),
        },
        {
            "role": "user",
            "content": "embedded systems kya hota hai exactly",
            "timestamp": _now(),
        },
        {
            "role": "bhavishya",
            "content": "Woh speaker jo tune fix kiya? Ek embedded system tha. Car brake sensors, medical devices, satellite components - sab embedded. Tere haath ka kaam already is space mein hai. Ek kaam kar: 'Embedded Systems Essentials' YouTube pe dekh, ek raat mein clear ho jaayega.",
            "timestamp": _now(),
        },
    ]

    profile["micro_observations"] = [
        {
            "text": "Hardware keeps coming up even when talking about software careers.",
            "timestamp": _now(),
            "session": 1,
        },
        {
            "text": "'pata nahi' appears multiple times but energy clearly changes when he talks about fixing things.",
            "timestamp": _now(),
            "session": 2,
        },
    ]

    profile["futures_generated"] = [
        {
            "session": 2,
            "futures": [
                {
                    "type": "expected",
                    "title": "The JEE Road",
                    "narrative_2031": "You wake up at 7:20 in a Pune flat you share with two colleagues. The commute bus leaves at 8:30. Three years into a software services job, the work is stable and you are good at it - you catch bugs others miss, your team lead mentioned it last week. The project is not exciting. You pay your father's home loan EMI every month without having to think about it, which matters more than you expected. Your cousin got into a Hyderabad startup with stock options and your chachi mentions it at every family dinner. Some evenings you open an Arduino IDE and close it an hour later.",
                    "career_trajectory": "JEE coaching -> B.Tech CS -> TCS/Infosys -> mid-level software engineer",
                    "key_decision_point": "Joining JEE coaching in Class 11 because the family WhatsApp group treated rank as the only number that mattered.",
                    "what_you_gain": "Financial stability, family approval, the quiet satisfaction of being reliably good at something.",
                    "what_you_sacrifice": "By 28, explaining a direction change means reopening every family conversation you thought was settled.",
                    "ai_disruption_risk": "high",
                    "annual_salary_2031_inr": 900000,
                    "salary_context": "9L in Pune is roughly 62k take-home per month - covers rent and EMI with some left over.",
                },
                {
                    "type": "inner_call",
                    "title": "The Build Path",
                    "narrative_2031": "You wake up at 8 AM in a Bengaluru studio, fan running. On your desk: a PCB half-assembled, a multimeter, three browser tabs. You design the hardware layer for an agri-IoT startup - soil sensors, water monitors, devices that survive monsoons. The diagnostic instinct that caught dust in a woofer now catches signal noise in field sensors. Last month you found a latency issue in the firmware no one else had flagged. Your manager sent that note to the CTO. The salary is lower than your JEE-track batchmates. The work feels like yours in a way nothing else has.",
                    "career_trajectory": "B.Tech ECE with electronics focus -> embedded systems internship -> hardware engineer at IoT startup",
                    "key_decision_point": "Choosing ECE over pure CS against family advice.",
                    "what_you_gain": "Work that uses the actual diagnostic ability you have. Creative ownership over physical systems.",
                    "what_you_sacrifice": "Lower starting salary, fewer on-campus placement options, five years of explaining what you do.",
                    "ai_disruption_risk": "low",
                    "annual_salary_2031_inr": 780000,
                    "salary_context": "7.8L at an IoT startup often includes ESOP with strong upside if the company scales - hardware roles are less commoditised than software.",
                },
                {
                    "type": "unseen_door",
                    "title": "Hardware Failure Analyst",
                    "narrative_2031": "You wake up at 6:30, fan humming. You are a hardware failure analyst at a defense electronics firm. Your job is to understand why systems break before they break in the field. You receive failed components from aircraft and satellites and reverse-diagnose what went wrong. The role did not have this name when you were in Class 11. It found you through an internship where your supervisor noticed you were the only intern who looked at failed components with curiosity instead of frustration. You stopped explaining your job title two years ago. You just started showing people the work.",
                    "career_trajectory": "B.Tech ECE -> DRDO/ISRO internship -> defense electronics hardware analyst",
                    "key_decision_point": "Taking a DRDO internship application seriously in third year instead of chasing software placement prep.",
                    "what_you_gain": "A rare skill profile, work that directly uses your diagnostic instinct, national-scale impact.",
                    "what_you_sacrifice": "Lower salary than private sector peers for the first five years. Family reassurance comes late.",
                    "ai_disruption_risk": "low",
                    "annual_salary_2031_inr": 720000,
                    "salary_context": "Government CTC of 7.2L comes with housing allowance and pension that private sector rarely matches at this level.",
                },
            ],
        }
    ]

    save_student(profile)
    print("Seeded: demo_aryan (PIN: 1234) - Class 11, 2 sessions, futures generated")


def seed_priya():
    _delete_if_exists("demo_priya")
    profile = create_new_profile(
        name="Priya",
        grade=10,
        uid="demo_priya",
        username="demo_priya",
        pin="1234",
    )

    session1 = {
        "thinking_style": "Processes information by connecting patterns across different domains - notices the structure underneath things, not just the surface.",
        "core_values": ["understanding", "service", "independence"],
        "hidden_strengths": [
            "Asks the question underneath the question - gets to root causes others skip.",
            "Comfortable with ambiguity in a way that is rare for her age.",
        ],
        "active_fears": [
            "Becoming a doctor because everyone around her is, not because she actually wants it.",
            "Being good at something she doesn't care about.",
        ],
        "family_pressure_map": "Strong family pressure toward NEET. Multiple relatives are doctors. The path is treated as already decided.",
        "energy_signature": "Comes alive when she finds the pattern that explains why something works - the mechanism, not the fact.",
        "identity_confidence": 7,
        "changed_since_last": False,
        "change_summary": "",
    }

    session2 = {
        "thinking_style": "Processes information by connecting patterns across different domains - notices the structure underneath things, not just the surface.",
        "core_values": ["understanding", "systemic_impact", "independence"],
        "hidden_strengths": [
            "Asks the question underneath the question - gets to root causes others skip.",
            "Comfortable with ambiguity in a way that is rare for her age.",
        ],
        "active_fears": [
            "Choosing medicine because it is the path of least resistance, not a deliberate choice.",
            "Finding out at 25 that she chose the wrong thing and being unable to admit it.",
        ],
        "family_pressure_map": "Strong family pressure toward NEET. The word 'doctor' is used as a proxy for 'settled and respected.'",
        "energy_signature": "Comes alive when she finds the pattern that explains why something works - the mechanism, not just the symptom.",
        "identity_confidence": 8,
        "changed_since_last": True,
        "change_summary": "Fear is now more specific: not 'wrong career' but 'choosing for the wrong reason and being unable to admit it later'.",
    }

    # Session 3 — second fear resolved, active decision made, confidence peak
    session3 = {
        "thinking_style": "Processes information by connecting patterns across different domains - notices the structure underneath things, not just the surface. Now applies this deliberately rather than accidentally.",
        "core_values": ["understanding", "systemic_impact", "deliberate_choice"],
        "hidden_strengths": [
            "Asks the question underneath the question - gets to root causes others skip.",
            "Comfortable with ambiguity in a way that is rare for her age.",
            "Can hold uncertainty long enough to make a real decision rather than a reactive one.",
        ],
        "active_fears": [],
        "family_pressure_map": "Family pressure remains but Priya has reframed the conversation from 'NEET vs not-NEET' to 'which kind of doctor-adjacent career.' IISER is now on the table at home.",
        "energy_signature": "Comes alive when she finds the pattern that explains why something works - the mechanism, not just the symptom.",
        "identity_confidence": 9,
        "changed_since_last": True,
        "change_summary": "Both active fears resolved. No longer afraid of choosing wrong — is now focused on choosing deliberately. Family conversation has shifted from resistance to negotiation.",
    }

    profile["session_count"] = 3
    profile["identity_current"] = session3
    profile["identity_history"] = [
        {"session": 1, "snapshot": session1},
        {"session": 2, "snapshot": session2},
        {"session": 3, "snapshot": session3},
    ]
    profile["last_session"] = str(date.today())

    # InsightBanner reads these two fields — populated at login time
    profile["identity_delta"] = {
        "previous_confidence": 8,
        "current_confidence": 9,
        "resolved_fears": [
            "Finding out at 25 that she chose the wrong thing and being unable to admit it.",
            "Choosing medicine because it is the path of least resistance.",
        ],
        "new_strengths": ["Can hold uncertainty long enough to make a real decision rather than a reactive one."],
    }
    profile["last_session_summary"] = {
        "has_new_move": True,
        "session_index": 3,
        "one_line": "Both fears resolved. Margdarshak has a move specifically for the family conversation.",
    }

    profile["aawaz_history"] = [
        {
            "role": "user",
            "content": "mummy chahti hain main doctor banun. ghar mein sab doctors hain",
        },
        {
            "role": "aawaz",
            "content": "Aur tu? Jab koi nahi sunta, toh tu kya sochti hai future ke baare mein?",
        },
        {
            "role": "user",
            "content": "actually mujhe biology interesting lagti hai but I keep wondering why things work, not just what they are",
        },
        {
            "role": "aawaz",
            "content": "That distinction matters more than it sounds. What's the last thing you looked up just because you were curious, not for exams?",
        },
        {
            "role": "user",
            "content": "how antibiotic resistance actually happens. not the definition, the actual mechanism. I watched 3 videos",
        },
        {
            "role": "aawaz",
            "content": "Three videos on mechanism, not definition. That's not studying - that's genuine curiosity about systems. What did you understand by the end that the first video didn't explain?",
        },
    ]

    profile["conversation_history"] = [
        {
            "role": "user",
            "content": "kya main NEET ke bina bhi biology mein kuch kar sakti hoon",
            "timestamp": _now(),
        },
        {
            "role": "bhavishya",
            "content": "Haan - aur yeh sawaal poochna already ek signal hai. Jo cheez tujhe antibiotic resistance ke mechanism tak le gayi - woh researcher ki curiosity hai, not a clinician's. Research, public health, epidemiology, science communication - inhe NEET nahi chahiye. BSc Research programs at IISERs specifically recruit the kind of curiosity you just described.",
            "timestamp": _now(),
        },
        {
            "role": "user",
            "content": "but ghar waale samjhenge nahi",
            "timestamp": _now(),
        },
        {
            "role": "bhavishya",
            "content": "Yeh fair concern hai. Unke liye 'doctor' ka matlab 'stable aur respected' hai - that's not wrong, that's real. The conversation to have isn't 'I don't want to be a doctor.' It's: 'What if I could have the same stability and more impact?' IISER graduates go into ISRO, WHO, top pharma research. Ek kaam kar - IISER Pune ka placement data dekh, phir yeh baat karna easier hogi.",
            "timestamp": _now(),
        },
    ]

    profile["micro_observations"] = [
        {
            "text": "Keeps distinguishing between 'what' and 'why' - this pattern appears across multiple messages.",
            "timestamp": _now(),
            "session": 1,
        },
    ]

    profile["futures_generated"] = [
        {
            "session": 2,
            "futures": [
                {
                    "type": "expected",
                    "title": "The NEET Path",
                    "narrative_2031": "You wake up at 6 AM in a hostel room shared with two other residents. First year of medical residency. The 14-hour shift starts at 7. You are genuinely good at diagnosis - your attending notices. The pattern-recognition ability that made you watch three antibiotic resistance videos at 14 now helps you catch differential diagnoses faster than your batchmates. You are also tired in a way that doesn't fully go away. Mummy video calls every Sunday. The why-does-this-work question that used to keep you up at night is still there. There is not much time for it.",
                    "career_trajectory": "NEET -> MBBS -> MD Residency -> Specialist",
                    "key_decision_point": "Entering NEET coaching because the family path had no visible fork in it.",
                    "what_you_gain": "Genuine patient impact, family pride, and the satisfaction of being very good at a hard thing.",
                    "what_you_sacrifice": "The mechanism-level curiosity that drives you goes unfed for 10+ years while you build clinical competence.",
                    "ai_disruption_risk": "medium",
                    "annual_salary_2031_inr": 600000,
                    "salary_context": "6L during residency is below most peer fields but grows sharply after: senior consultants earn 40-80L. The timeline to financial stability is longer than most careers.",
                },
                {
                    "type": "inner_call",
                    "title": "The Research Path",
                    "narrative_2031": "You wake up at 8:30 near the IISER campus. On your screen: a paper on AMR spread patterns you've been building for three months. You work in a computational biology lab - your job is to model how antibiotic resistance moves across populations. The three-video rabbit hole at 14 was the first version of what you do now. Your work has been cited by a WHO working group. Mummy asked how that compares to being a doctor and you sent her the citation link. She didn't fully understand it but she showed her friends.",
                    "career_trajectory": "IISER BS-MS -> PhD in computational biology or epidemiology -> research scientist",
                    "key_decision_point": "Choosing IISER over NEET coaching against family expectation.",
                    "what_you_gain": "Work that feeds the mechanism-level curiosity that defines how you think. Impact at population scale.",
                    "what_you_sacrifice": "Five years of your family not fully understanding what you do. The word 'doctor' never applies.",
                    "ai_disruption_risk": "low",
                    "annual_salary_2031_inr": 720000,
                    "salary_context": "7.2L for a junior research scientist at a government lab grows significantly with seniority and comes with publication-based career capital that compounds over time.",
                },
                {
                    "type": "unseen_door",
                    "title": "Outbreak Intelligence Analyst",
                    "narrative_2031": "You wake up at 7 AM. Your phone has three alerts from a disease surveillance dashboard you helped build - a cluster in Rajasthan that looks anomalous. By 9 AM you're on a call with the state health team. You work at an IDSP-linked public health intelligence unit. Your job is to spot the pattern before it becomes a crisis. You don't treat patients. You protect millions of them before they ever get sick. This role didn't have a name when you were in Class 10. You stopped apologising for not being a doctor about two years ago.",
                    "career_trajectory": "BSc Public Health or Epidemiology -> MPH -> government disease surveillance",
                    "key_decision_point": "Taking an epidemiology elective seriously instead of treating it as a fallback.",
                    "what_you_gain": "Pattern-recognition at national scale, genuine public health impact, a role that will matter more in 2031 than it did in 2024.",
                    "what_you_sacrifice": "'Outbreak analyst' takes explaining. Five years of 'but why not NEET' at family dinners.",
                    "ai_disruption_risk": "low",
                    "annual_salary_2031_inr": 750000,
                    "salary_context": "7.5L at a government public health role includes DA, HRA, and pension that private sector doesn't match - effective CTC is closer to 10L.",
                },
            ],
        }
    ]

    save_student(profile)
    print("Seeded: demo_priya (PIN: 1234) - Class 10, 2 sessions, futures generated")


if __name__ == "__main__":
    os.makedirs("students", exist_ok=True)
    print("Seeding demo accounts...")
    seed_aryan()
    seed_priya()
    print("\nReady.")
    print("  demo_aryan  PIN: 1234  Class 11 - engineering vs hardware builder")
    print("  demo_priya  PIN: 1234  Class 10 - doctor pressure vs systems thinker")
    print("\nOn first login both accounts immediately show:")
    print("  - InsightBanner with confidence delta (e.g. 8 → 9)")
    print("  - Resolved fears listed in the banner")
    print("  - Margdarshak new-move flag set")
    print("  - 3 sessions of longitudinal memory visible in history")
    print("  - Pre-generated futures (no simulator wait time)")
    print("  - Seeded micro-observations (behavioral pattern detection visible)")
    print("\nStart the demo with demo_aryan.")
    print("Aryan arc: hardware fixer → embedded systems clarity → fear resolved")
    print("Priya arc: NEET pressure → mechanism curiosity → deliberate choice made")