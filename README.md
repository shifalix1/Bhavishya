# Bhavishya

> _Hindi: future_

An AI career companion for students in Class 9-12. Not a quiz. Not a list of options. A system that listens to who you actually are, builds a psychological profile from real conversation, and shows you three versions of your life -- grounded in what the job market actually looks like, not what your relatives think it looks like.

**Demo:** `demo_aryan / 1234` or `demo_priya / 1234` at [bhavishya.vercel.app](https://bhavishya.vercel.app)

---

## The problem

When I was in Class 9, I didn't like maths. So I assumed I'd go for Commerce -- because Arts "isn't a real option" and Science needs maths. My dad wanted Science. I resisted. Then in Class 10 I got a good teacher and started loving maths. So I switched to Science in Class 11. Just like that. A full future career plan based on liking one subject.

Eight years later, my brother is in Class 9 and he has no clue. At least I knew the options. He doesn't even have that.

This is true for tens of millions of students across India and across the world. They are clueless -- not because something is wrong with them, but because no one is actually talking to them about who they are. A physical career counselling session in India costs 3,000 to 20,000 rupees per session. 90% of families can't afford that. So the guidance comes from a WhatsApp group where JEE rank is the only number that matters.

At 18, you get to vote for who runs your country. At 14, you have to choose your career -- with no data, no guidance, and enormous family pressure. That's the problem Bhavishya is built to fix.

---

## What it does

Bhavishya is not a career quiz. It does not ask you to rate your interest in 40 subjects and return a pie chart.

It has a conversation with you. It asks one question at a time. It listens to how you answer -- not just what you say, but how you say it, what you avoid, what you return to. After enough conversation, it builds an identity fingerprint: your thinking style, your actual values, your hidden strengths, the fears you haven't named yet, the family pressures you're navigating.

Then it generates three parallel futures specific to you:

- **The Expected Path** -- what you'd probably do if you follow the plan everyone around you has
- **The Inner Call** -- what fits who you actually are, based on what came through in conversation
- **The Unseen Door** -- a career you've never considered, matched to at least two specific signals from your identity, and banned from being anything obvious

All three are grounded in real Indian career data: actual salary ranges, AI displacement risk, city-specific narratives.

Then it guides you over multiple sessions -- tracking how your identity is changing, surfacing new strengths, resolving fears as they resolve, giving you one concrete next move at a time.

---

## India first, not India only

The dataset and narratives are built for India right now because that's where the problem is most acute and where the data is. Indian salary ranges, Indian city trajectories, Indian family pressure dynamics, Hinglish as a first-class language.

But the architecture is not India-specific. The psychological fingerprinting, the parallel future simulation, the longitudinal identity tracking -- these work anywhere a student is being pushed toward a career before they know who they are. That's not a uniquely Indian problem. It's a global one. India is where Bhavishya starts. It's not where it ends.

---

## Architecture

```

![Bhavishya system architecture](assets/architecture.png)

```

**Memory system** persists across sessions. Each session snapshots the identity fingerprint, conversation transcript, futures generated, and Margdarshak Q&A. A rolling summariser compresses long histories to stay within context limits while preserving longitudinal signal.

**Language detection** handles the Roman-script Hinglish that standard language detection libraries cannot identify -- Devanagari Unicode check, then Hinglish word list, then langdetect fallback.

---

## Modules

| Module             | Hindi meaning | Function                                                 |
| ------------------ | ------------- | -------------------------------------------------------- |
| **Aawaz**          | Voice         | Conversational intake. One question at a time.           |
| **Darpan**         | Mirror        | Psychological identity fingerprinting from conversation. |
| **Bhavishya Core** | Future        | Three parallel life futures specific to this student.    |
| **Margdarshak**    | Guide         | Ongoing guidance. One move. One question. Per session.   |

---

## Why Gemma

Built specifically for the Gemma 4 Good Hackathon. Three things Gemma 4 makes possible that matter here:

**Multimodal intake.** Aawaz processes voice audio, student-uploaded images (sketchbooks, Minecraft builds, project photos, marksheets), and text in a single call. A student can share a photo of something they made and Aawaz asks one curious question about the person behind it -- not a description of what it sees.

**Hinglish natively.** Most Indian students aged 13-17 think and speak in a mix of Hindi and English. Gemma 4's multilingual tokenisation handles Roman-script Hinglish without a separate translation step. The entire conversation layer, fingerprinting, and guidance can run in Hinglish without degradation.

**Local deployment via Ollama.** Bhavishya ships with a `BHAVISHYA_MODE=ollama` path that runs `gemma4:e4b` entirely offline. A school in a Tier-3 city with no cloud budget and a single GPU workstation can run the full system locally. No internet. No subscription. No data leaving the building.

---

## Stack

**Backend**

- Python 3.11+
- FastAPI with async throughout
- `google-genai` SDK for Gemma 4 26B via Google AI Studio (cloud mode)
- Ollama for Gemma 4 E4B (local mode)
- slowapi for rate limiting
- JSON file-based persistence (no database dependency)

**Frontend**

- React 18 + Vite
- CSS Modules, no UI library
- DM Sans + Instrument Serif
- Light/dark theme via CSS custom properties
- Skeleton loading states throughout
- Mobile-responsive with bottom nav on small screens

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google AI Studio API key -- [get one free](https://aistudio.google.com/app/apikey)
- Optional: Ollama with `gemma4:e4b` pulled for local mode

### Backend

```bash
cd bhavishya
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add GOOGLE_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local      # set VITE_API_URL=http://localhost:8000
npm run dev
```

### Seed demo accounts

```bash
python seed_demo.py
```

Creates `demo_aryan` and `demo_priya` with three sessions of pre-built history each. Run this on the server so accounts exist on the live backend.

### Local (Ollama) mode

```bash
ollama pull gemma4:e4b

# In .env:
BHAVISHYA_MODE=ollama

uvicorn main:app --reload --port 8000
```

No Google API key required. Full functionality offline.

---

## Environment variables

| Variable            | Required        | Default                 | Description                           |
| ------------------- | --------------- | ----------------------- | ------------------------------------- |
| `GOOGLE_API_KEY`    | Cloud mode only |                         | Google AI Studio key                  |
| `BHAVISHYA_MODE`    | No              | `cloud`                 | `cloud` or `ollama`                   |
| `CORS_ORIGINS`      | No              | `http://localhost:5173` | Comma-separated allowed origins       |
| `BHAVISHYA_API_KEY` | No              |                         | Optional API key guard for all routes |

---

## API reference

| Method | Path                    | Description                                                 |
| ------ | ----------------------- | ----------------------------------------------------------- |
| `POST` | `/register`             | Create account (username + 4-digit PIN)                     |
| `POST` | `/login`                | Authenticate, returns identity delta for returning students |
| `POST` | `/aawaz/chat`           | Conversational turn with Aawaz                              |
| `POST` | `/aawaz/transcribe`     | Multimodal intake: voice + image + text                     |
| `POST` | `/session`              | Run Darpan fingerprinting on conversation input             |
| `POST` | `/simulate`             | Generate 3 parallel futures                                 |
| `POST` | `/margdarshak/guidance` | Get personalised guidance for current session               |
| `POST` | `/margdarshak/question` | Ask one question (rate-limited: 1 per session)              |
| `GET`  | `/history/{uid}`        | Structured session history for Sidebar                      |
| `GET`  | `/health`               | Health check                                                |

Rate limits: 10 req/min on session-heavy routes, 5 req/min on simulate.

---

## Key design decisions

**Evidence anchoring in Darpan.** Every field in the identity fingerprint must be traceable to something the student actually said. The prompt explicitly instructs the model: if you cannot point to a specific behaviour, word choice, or pattern they showed -- lower `identity_confidence` instead of writing a generic truth. Generic output is a failure mode, not an acceptable default.

**The Unseen Door.** The third future is always a career the student has never imagined but that fits who they actually are. It must connect to at least two specific signals from their identity fingerprint. A banned list of 20+ obvious careers (Data Scientist, Content Creator, UX Designer, etc.) prevents the model from defaulting to the first ten results on any career website.

**One question per session in Margdarshak.** Scarcity is intentional. It forces the student to ask what they actually want to know. The answer is 5-8 sentences, dense and considered, matching the weight of the question.

**Micro-observation engine.** `aawaz.py` contains a deterministic pattern-matching system -- zero model cost -- that tracks recurring words, message length changes, hedging behaviour, and enthusiasm signals across a conversation. These observations are injected into the Darpan fingerprint as behavioural evidence, improving specificity without additional model calls.

**Rolling memory compression.** When conversation history exceeds a threshold, a model call summarises the earlier turns into a dense 3-5 sentence block. This keeps context windows manageable for students who return across many sessions without losing the longitudinal signal.

---

## What Bhavishya does not do

- It does not tell students what career to choose.
- It does not say "follow your passion."
- It does not return a list of options. That is the Bhavishya Core's job, after it knows who you are.
- It does not store email addresses, phone numbers, or any identifying information beyond a username and hashed PIN.
- Aawaz does not label student artifacts diagnostically. It asks one question about the person behind the artifact, not about the artifact itself.

---

## Longitudinal tracking

Each login for a returning student computes an `identity_delta`: confidence change direction, resolved fears, new strengths surfaced. This appears as an InsightBanner on the Dashboard. Over multiple sessions, Bhavishya tracks not just who a student is, but how they are changing -- and Margdarshak's guidance updates accordingly.

---

## Hackathon context

Built for the Gemma 4 Good Hackathon.

The "Good" is specific: the local deployment mode means Bhavishya can run in schools with no cloud infrastructure, no subscription cost, and no data leaving the premises. A school with a single workstation and 8GB of unified RAM can run the full system on `gemma4:e4b` via Ollama.

The target user is a 14-year-old in Class 9 who is about to be told to pick Science or Commerce, has never spoken to a career counsellor, and whose only guidance comes from a WhatsApp group where JEE rank is the only number that matters.

---

## License

MIT
