# Bhavishya — Demo Guide

## Live Demo

**URL:** https://bhavishya.shifalisingh.in

If the app takes 30-60 seconds to load on first visit, that's the free backend waking up. Refresh once and it will be instant after that.

---

## Demo Accounts

Two pre-seeded accounts with 3 sessions of history each. No signup needed.

| Username     | PIN    | Profile                                                                              |
| ------------ | ------ | ------------------------------------------------------------------------------------ |
| `demo_aryan` | `1234` | Class 11. Hardware builder. Father wants JEE. Fear of competence-without-meaning.    |
| `demo_priya` | `1234` | Class 10. Systems thinker. Family wants NEET. Fear of choosing for the wrong reason. |

**Start with Aryan.** The hardware-vs-engineering tension is faster to explain in under 3 minutes.

---

## What You See Immediately on Login

Both accounts land on the Dashboard with full longitudinal history pre-loaded:

- **InsightBanner** — confidence delta from last session (e.g. 8 → 9), resolved fears listed
- **Margdarshak** — new move flagged, ready to open
- **Sidebar** — 3 sessions of history, identity evolution visible per session
- **Futures** — 3 parallel life paths already generated, no wait time

---

## Aryan's Arc (3 sessions)

| Session | What Changed                                                                                                        |
| ------- | ------------------------------------------------------------------------------------------------------------------- |
| 1       | Identity established. Fear: "choosing engineering because everyone expects it." Hardware interest signals detected. |
| 2       | Fear sharpens: "ending up competent but bored." Futures generated. Embedded systems surfaced.                       |
| 3       | Fear of wrong career resolved. Family conversation shifted from resistance to negotiation. Confidence: 9/10.        |

The Unseen Door future: **Hardware Failure Analyst at a defense electronics firm** — a role Aryan has never heard of that matches his diagnostic instinct exactly.

---

## Priya's Arc (3 sessions)

| Session | What Changed                                                                                                  |
| ------- | ------------------------------------------------------------------------------------------------------------- |
| 1       | Identity established. Curiosity pattern: asks "why does this work" not "what is this." NEET pressure visible. |
| 2       | Fear sharpens: "choosing for the wrong reason and being unable to admit it later." IISER surfaced.            |
| 3       | Both active fears resolved. Family conversation reframed. No remaining active fears. Confidence: 9/10.        |

The Unseen Door future: **Outbreak Intelligence Analyst** — disease surveillance, national-scale pattern recognition, a role that didn't have this name when she was in Class 10.

---

## Things Worth Clicking

1. **Sidebar (history drawer)** — shows per-session identity snapshots and what changed. This is the longitudinal tracking story.
2. **Margdarshak** — open the guidance panel on either account. The `next_move` is typed as `do/watch/ask/reflect`, not generic advice.
3. **IdentityPanel** — the confidence bar and resolved fears. On Aryan, `active_fears` went from 2 items to 1 across sessions.
4. **FutureCard — Unseen Door** — this is the product's thesis. A career the student has never imagined, matched to two specific identity signals.

---

## Running the Demo Locally

```bash
# Backend
cd server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # add your GOOGLE_API_KEY
python seed_demo.py          # creates demo_aryan and demo_priya
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd client
npm install
cp .env.example .env.local   # set VITE_API_URL=http://localhost:8000
npm run dev
```

Then open `http://localhost:5173` and log in with either demo account.

---

## Offline Mode (No API Key Needed)

```bash
# Install Ollama: https://ollama.com
ollama pull gemma4:e4b

# In server/.env set:
BHAVISHYA_MODE=ollama

# Run backend — no GOOGLE_API_KEY required
uvicorn main:app --reload --port 8000
```

Full functionality. No internet. No cloud account.
