# Bhavishya — AI Career Companion for Indian Students

> **Gemma 4 Good Hackathon Submission**

Bhavishya (Hindi: _future_) is an AI career guidance system built for Indian high school students in Class 9–12. It listens to who a student actually is, builds a psychological identity fingerprint, simulates three parallel futures grounded in real Indian career data, and provides ongoing personalised guidance — in Hindi, English, or Hinglish — across multiple sessions.

**The problem:** 15 million Indian students face stream selection every year. Fewer than 10% have access to any career guidance. 60% report regretting their stream choice. The current system optimises for JEE rank, not for the person.

---

## Why Gemma

Bhavishya is built specifically around Gemma 4's capabilities, not as a wrapper around any generic LLM:

**Multimodal intake.** Aawaz uses Gemma 4's native multimodal API to process voice audio, student-uploaded images (sketchbooks, Minecraft builds, project photos, marksheets), and text in a single call. A student can share a photo of something they made and Aawaz will ask one curious question about the _person_ behind it — not describe what it sees.

**Hinglish natively.** Most Indian students aged 13–17 think and speak in a mix of Hindi and English. Gemma 4's multilingual tokenization handles Roman-script Hinglish without a separate translation step. The entire Aawaz conversation layer, Darpan fingerprinting, and Margdarshak guidance can run in Hinglish without degradation.

**Local deployment via Ollama.** Bhavishya ships with a `BHAVISHYA_MODE=ollama` path that runs `gemma4:e4b` entirely offline via Ollama. A school in a Tier-3 city with no cloud budget and a single GPU workstation can run the full system locally. This is the "Good" in Gemma 4 Good — the model's efficiency makes genuine equity possible.

**JSON-mode structural reliability.** Darpan and the Simulator use `response_mime_type: application/json` to structurally constrain Gemma 4's output. This eliminates regex extraction entirely and makes the identity fingerprint and future simulation pipelines robust at scale.

---

## Architecture

```
Student
  │
  ▼
Aawaz (conversational layer)
  │  Gemma 4 multimodal: voice + image + text
  │  Hinglish/English conversation
  │  Micro-observation engine (deterministic, zero model cost)
  │
  ▼
Darpan (identity mirror)
  │  Gemma 4 JSON-mode structured output
  │  Extracts: thinking_style, core_values, hidden_strengths,
  │            active_fears, energy_signature, family_pressure_map
  │  Evidence-anchored — every field traced to what the student said
  │
  ├──▶ Simulator (future engine)
  │      Gemma 4 JSON-mode
  │      3 parallel futures: Expected / Inner Call / Unseen Door
  │      Grounded in careers.json (real Indian salary + AI risk data)
  │      City-specific narratives, second-person present tense
  │
  └──▶ Margdarshak (guide layer)
         One concrete next move
         One question per session
         Longitudinal: reads identity delta across sessions
```

**Memory system** persists across sessions. Each session snapshots the identity fingerprint, Aawaz transcript, futures generated, and Margdarshak Q&A. A rolling summarizer (Gemma 4) compresses long conversation histories to stay within context limits.

**Language detection** (`language.py`) uses Devanagari Unicode range check → Hinglish word list → langdetect fallback, in that order. Handles the Roman-script Hindi that `langdetect` cannot identify correctly.

---

## Modules

| Module          | Hindi meaning | Function                                                                  |
| --------------- | ------------- | ------------------------------------------------------------------------- |
| **Aawaz**       | Voice         | Conversational intake. Talks to the student. Asks one question at a time. |
| **Darpan**      | Mirror        | Psychological identity fingerprinting from conversation.                  |
| **Simulator**   | —             | Generates 3 parallel life futures specific to this student.               |
| **Margdarshak** | Guide         | Ongoing guidance layer. One concrete move. One question per session.      |

---

## Stack

**Backend**

- Python 3.11+
- FastAPI with async throughout (`asyncio.to_thread` for all blocking model calls)
- `google-genai` SDK — Gemma 4 26B via Google AI Studio (cloud mode)
- Ollama — Gemma 4 E4B (local mode)
- slowapi for rate limiting
- JSON file-based persistence (no database dependency for hackathon)

**Frontend**

- React 18 + Vite
- CSS Modules, no UI library
- DM Sans + Instrument Serif typefaces
- Light/dark theme system with CSS custom properties
- Skeleton loading states throughout
- Mobile-responsive with bottom nav on small screens

---

## Project Structure

```
bhavishya/
├── main.py                      # FastAPI app, all routes
├── core/
│   ├── aawaz.py                 # Multimodal intake + conversation engine
│   ├── darpan.py                # Identity fingerprinting (Gemma 4 JSON mode)
│   ├── simulator.py             # Future simulation (Gemma 4 JSON mode)
│   ├── margdarshak.py           # Guidance + Q&A layer
│   ├── memory.py                # Session persistence, compression, history
│   ├── language.py              # Hinglish/Hindi/English detection
│   └── careers.py               # Career data loader + identity matcher
├── prompts/
│   ├── aawaz_prompt.txt
│   ├── darpan_prompt.txt
│   ├── margdarshak_prompt.txt
│   ├── margdarshak_question_prompt.txt
│   └── simulator_prompt.txt
├── careers.json                 # Indian career database with salary + AI risk data
├── frontend/
│   └── src/
│       ├── pages/               # Dashboard, Session, Futures, Margdarshak, Onboard
│       ├── components/          # Aawaz, Sidebar, FutureCard, IdentityPanel, ...
│       └── lib/                 # api.js, cache.js, theme.js
└── .env.example
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google AI Studio API key — [get one free](https://aistudio.google.com/app/apikey)
- (Optional, for local mode) Ollama with `gemma4:e4b` pulled

### Backend

```bash
# Clone and enter the repo
cd bhavishya

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY

# Run
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure
cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000

# Run
npm run dev
```

### Local (Ollama) Mode

```bash
# Pull the model (requires ~8GB VRAM or unified RAM)
ollama pull gemma4:e4b

# Set in .env
BHAVISHYA_MODE=ollama

# Run backend normally — no Google API key required
uvicorn main:app --reload --port 8000
```

---

## Environment Variables

| Variable            | Required        | Default                 | Description                           |
| ------------------- | --------------- | ----------------------- | ------------------------------------- |
| `GOOGLE_API_KEY`    | Cloud mode only | —                       | Google AI Studio key                  |
| `BHAVISHYA_MODE`    | No              | `cloud`                 | `cloud` or `ollama`                   |
| `CORS_ORIGINS`      | No              | `http://localhost:5173` | Comma-separated allowed origins       |
| `BHAVISHYA_API_KEY` | No              | —                       | Optional API key guard for all routes |

---

## API Reference

| Method | Path                    | Description                                                 |
| ------ | ----------------------- | ----------------------------------------------------------- |
| `POST` | `/register`             | Create student account (username + 4-digit PIN)             |
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

## Requirements

### Server (`requirements.txt`)

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
python-dotenv>=1.0.0
google-genai>=0.8.0
ollama>=0.2.1
slowapi>=0.1.9
pydantic>=2.0.0
langdetect>=1.0.9
bcrypt>=4.1.0
```

### Client (`frontend/package.json` key deps)

```
react ^18.3.0
react-dom ^18.3.0
vite ^5.0.0
```

No UI library. No component framework. Pure React + CSS Modules.

---

## Key Design Decisions

**Evidence anchoring in Darpan.** Every field in the identity fingerprint must be traceable to something the student actually said. The prompt explicitly instructs the model: "If you cannot point to a specific behaviour, word choice, or pattern they showed — lower identity_confidence instead of writing a generic truth." Generic output is treated as a failure mode, not an acceptable default.

**The Unseen Door.** The third future is always a career the student has never imagined but that fits who they actually are — and it must be connected to at least two specific signals from their identity fingerprint. A banned list of 20+ obvious careers (Data Scientist, Content Creator, UX Designer, etc.) prevents the model from defaulting to the first ten results on any career website.

**One question per session in Margdarshak.** Scarcity is intentional. It forces the student to ask what they actually want to know, not what they think they should ask. The answer is 5–8 sentences — dense and considered, matching the weight of the question.

**Micro-observation engine.** `aawaz.py` contains a deterministic (zero model cost) pattern-matching system that tracks recurring words, message length changes, hedging behaviour, and enthusiasm signals across a conversation. These observations are injected into the Darpan fingerprint as behavioural evidence, improving specificity without additional model calls.

**Rolling memory compression.** When conversation history exceeds a threshold, a Gemma 4 call summarises the earlier turns into a dense 3–5 sentence block. This keeps context windows manageable for students who return across many sessions without losing the longitudinal signal.

---

## Prompt Architecture

All five prompts contain structural constraints designed to prevent generic output:

- `aawaz_prompt.txt` — 8 directives including image analysis iron-clad rules, one-question-only enforcement, and a proactive multimedia ask trigger at exchange 3.
- `darpan_prompt.txt` — Evidence anchoring requirement, banned generic phrases, identity_confidence as an honest signal of how much the model actually knows.
- `simulator_prompt.txt` — Word count constraints per narrative (180–220 words), city-matching rules, salary validation rules with three specific fallback values flagged as hard failures, banned unseen door careers list.
- `margdarshak_prompt.txt` — Next move must be a named, specific, actionable thing. "Research career options" is explicitly given as a bad example.
- `margdarshak_question_prompt.txt` — Answer must go one level deeper than the guidance already went. No reassurance. A real answer.

---

## What Bhavishya Does Not Do

- It does not tell students what career to choose.
- It does not say "follow your passion."
- It does not give a list of options. That is the Simulator's job, after it knows who you are.
- It does not store email addresses, phone numbers, or any identifying information beyond a username and hashed PIN.
- Aawaz does not label student artifacts diagnostically. It asks one question about the person behind the artifact, not about the artifact itself.

---

## Longitudinal Tracking

Each login for a returning student computes an `identity_delta`: confidence change direction, resolved fears, new strengths surfaced. This is shown as an InsightBanner on the Dashboard. Over multiple sessions, Bhavishya tracks not just who a student is, but how they are changing — and Margdarshak's guidance updates accordingly.

---

## Hackathon Context

Built for the **Gemma 4 Good Hackathon**. The "Good" is specific: Bhavishya's local deployment mode means it can run in schools with no cloud infrastructure, no subscription cost, and no data leaving the premises. A school with a single workstation and 8GB of unified RAM can run the full system on `gemma4:e4b` via Ollama.

The target user is a 14-year-old in Class 9 who is about to be told to pick Science or Commerce, has never spoken to a career counsellor, and whose only guidance comes from a WhatsApp group where JEE rank is the only number that matters.

---

## License

MIT
