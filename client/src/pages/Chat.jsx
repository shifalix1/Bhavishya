import { useState, useEffect, useCallback } from "react";
import { margdarshakApi } from "../lib/api";
import styles from "./Chat.module.css";

// Lock gate
function LockedGate({ onGoToDarpan }) {
  return (
    <div className={styles.gate}>
      <div className={styles.gateIcon}>
        <CompassIcon size={32} />
      </div>
      <h2 className={styles.gateHeading}>Margdarshak hasn't met you yet.</h2>
      <p className={styles.gateSub}>
        One Darpan session is all it takes. Margdarshak reads your identity
        fingerprint and tells you exactly what to do next. Not generic advice.
        Your move, specific to who you are.
      </p>
      <button
        className={`btn btn-accent btn-lg ${styles.gateBtn}`}
        onClick={onGoToDarpan}
      >
        Run a Darpan session first
      </button>
    </div>
  );
}

// Move type badge
const MOVE_TYPE_META = {
  do: { label: "Do this", color: "var(--accent)", bg: "var(--accent-dim)" },
  watch: { label: "Watch this", color: "var(--gold)", bg: "var(--gold-dim)" },
  ask: { label: "Ask this", color: "var(--success)", bg: "var(--success-dim)" },
  reflect: {
    label: "Sit with this",
    color: "var(--text-sub)",
    bg: "var(--surface-alt)",
  },
};

function MoveTypeBadge({ type }) {
  const meta = MOVE_TYPE_META[type] || MOVE_TYPE_META.do;
  return (
    <span
      className={styles.moveBadge}
      style={{ color: meta.color, background: meta.bg }}
    >
      {meta.label}
    </span>
  );
}

// Identity strip
function IdentityStrip({ identity }) {
  if (!identity || !identity.thinking_style) return null;
  const conf = identity.identity_confidence ?? 0;
  const confColor =
    conf >= 7 ? "var(--success)" : conf >= 4 ? "var(--gold)" : "var(--error)";

  return (
    <div className={styles.identityStrip}>
      <div className={styles.stripLeft}>
        <span className={styles.stripLabel}>Working with your fingerprint</span>
        <p className={styles.stripThinking}>{identity.thinking_style}</p>
      </div>
      <div className={styles.stripRight}>
        {identity.hidden_strengths?.[0] && (
          <span
            className={styles.stripTag}
            style={{ color: "var(--accent)", background: "var(--accent-dim)" }}
          >
            {identity.hidden_strengths[0]}
          </span>
        )}
        {identity.active_fears?.[0] && (
          <span
            className={styles.stripTag}
            style={{ color: "var(--error)", background: "var(--error-dim)" }}
          >
            {identity.active_fears[0]}
          </span>
        )}
        <span className={styles.stripConf} style={{ color: confColor }}>
          {conf}/10 confidence
        </span>
      </div>
    </div>
  );
}

// Guidance view
function GuidanceView({ guidance, questionUsed, onAskQuestion }) {
  return (
    <div className={styles.guidanceWrap}>
      {guidance.opening_line && (
        <div className={styles.openingLine}>
          <span className={styles.openingMark}>"</span>
          {guidance.opening_line}
          <span className={styles.openingMark}>"</span>
        </div>
      )}

      <div className={styles.section}>
        <div className={styles.sectionLabel}>
          <ReadIcon /> Where you are right now
        </div>
        <p className={styles.currentRead}>{guidance.current_read}</p>
      </div>

      <div className={`${styles.section} ${styles.moveSection}`}>
        <div className={styles.sectionLabel}>
          <MoveIcon /> Your next move
        </div>
        <div className={styles.moveCard}>
          <MoveTypeBadge type={guidance.next_move?.type} />
          <p className={styles.moveAction}>{guidance.next_move?.action}</p>
          <p className={styles.moveWhy}>{guidance.next_move?.why}</p>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionLabel}>
          <WatchIcon /> What to watch for
        </div>
        <p className={styles.watchFor}>{guidance.watch_for}</p>
      </div>

      <div className={styles.questionSection}>
        {questionUsed ? (
          <div className={styles.questionUsedState}>
            <p className={styles.questionUsedText}>
              You asked your question for this session. New Darpan session
              unlocks another.
            </p>
          </div>
        ) : (
          <>
            <button className={styles.questionBtn} onClick={onAskQuestion}>
              Ask about this move <ArrowIcon />
            </button>
            <p className={styles.questionHint}>
              One question per session. Margdarshak will take its time.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

// One question view
function QuestionView({ guidance, student, onBack }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (!question.trim() || loading) return;
    setLoading(true);
    setError("");
    try {
      const res = await margdarshakApi.question(
        student.name,
        student.grade,
        student.uid,
        question.trim(),
        guidance,
        student.language_preference || "english",
      );
      setAnswer(res.answer);
      setSubmitted(true);
    } catch (e) {
      if (e.message?.includes("429") || e.message?.includes("One question")) {
        setError("You've already used your question for this session.");
      } else {
        setError("Something went wrong. Try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (submitted && answer) {
    return (
      <div className={styles.answerWrap}>
        <button className={styles.backLink} onClick={onBack}>
          Back to guidance
        </button>
        <div className={styles.questionEcho}>"{question}"</div>
        <div className={styles.answerBlock}>
          <div className={styles.answerAvatar}>
            <CompassIcon size={18} />
          </div>
          <p className={styles.answerText}>{answer}</p>
        </div>
        <p className={styles.answerNote}>
          That's your question for this session. Come back after your next
          Darpan session.
        </p>
        <button
          className={styles.backLink}
          onClick={onBack}
          style={{ marginTop: 12 }}
        >
          Back to guidance
        </button>
      </div>
    );
  }

  return (
    <div className={styles.questionWrap}>
      <button className={styles.backLink} onClick={onBack}>
        Back to guidance
      </button>
      <h2 className={styles.questionHeading}>
        What do you actually want to know?
      </h2>
      <p className={styles.questionSub}>
        One question. Ask about the move, the why behind it, or whatever is
        blocking you. Margdarshak will take its time with this one.
      </p>
      <textarea
        className={`field-input ${styles.questionInput}`}
        placeholder="Why this specific move? What if I can't do it? What happens after?"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        rows={4}
        autoFocus
        disabled={loading}
      />
      {error && <p className={styles.questionError}>{error}</p>}
      <div className={styles.questionActions}>
        <span className={styles.questionCount}>{question.length} chars</span>
        <button
          className="btn btn-accent"
          onClick={submit}
          disabled={loading || question.trim().length < 10}
        >
          {loading ? (
            <span className="dots">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </span>
          ) : (
            "Ask Margdarshak"
          )}
        </button>
      </div>
    </div>
  );
}

// Main
export default function Chat({ student, onGoToDarpan }) {
  const identity = student.identity_current;
  const hasIdentity = Boolean(identity && Object.keys(identity).length > 0);

  // Phase is derived from hasIdentity at init so no effect ever needs to set it synchronously.
  const [phase, setPhase] = useState(hasIdentity ? "loading" : "locked");
  const [guidance, setGuidance] = useState(null);
  const [questionUsed, setQuestionUsed] = useState(false);
  const [error, setError] = useState("");

  // loadGuidance contains ZERO synchronous setState calls.
  // All setState calls inside happen only after the first await, which is
  // safe to invoke from an effect body and satisfies react-hooks/set-state-in-effect.
  // Callers that need to show a loading spinner (refresh button, try-again button)
  // set phase to "loading" themselves before calling this.
  const loadGuidance = useCallback(async () => {
    try {
      const res = await margdarshakApi.guidance(
        student.name,
        student.grade,
        student.uid,
        student.language_preference || "english",
      );
      setGuidance(res.guidance);
      setQuestionUsed(res.question_used || false);
      setPhase("guidance");
    } catch (e) {
      if (e.message?.includes("400") || e.message?.includes("No identity")) {
        setPhase("locked");
      } else {
        setError(e.message || "Could not load guidance.");
        setPhase("error");
      }
    }
  }, [student.name, student.grade, student.uid, student.language_preference]);

  // Safe: loadGuidance has no sync setState so calling it here is fine.
  useEffect(() => {
    if (hasIdentity) {
      // Defer calling loadGuidance to avoid synchronous setState inside effect
      const t = setTimeout(() => {
        loadGuidance();
      }, 0);
      return () => clearTimeout(t);
    }
    return undefined;
  }, [hasIdentity, loadGuidance]);

  // Handlers used by buttons (event handlers are always allowed to call setState).
  const handleRefresh = () => {
    setPhase("loading");
    setError("");
    loadGuidance();
  };

  const handleTryAgain = () => {
    setPhase("loading");
    setError("");
    loadGuidance();
  };

  if (phase === "loading") {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingOrb}>
          <CompassIcon size={28} />
        </div>
        <p className={styles.loadingLabel}>
          Margdarshak is reading your fingerprint...
        </p>
        <span className="dots">
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
        </span>
      </div>
    );
  }

  if (phase === "locked") {
    return (
      <div className="page-enter">
        <LockedGate onGoToDarpan={onGoToDarpan} />
      </div>
    );
  }

  if (phase === "error") {
    return (
      <div className={styles.errorState}>
        <p className={styles.errorText}>{error}</p>
        <button className="btn btn-surface" onClick={handleTryAgain}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className={`page-enter ${styles.wrap}`}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.headerAvatar}>
            <CompassIcon size={20} />
          </div>
          <div>
            <h1 className={styles.headerName}>Margdarshak</h1>
            <p className={styles.headerSub}>Your guide. Walks with you.</p>
          </div>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.speakingTo}>Speaking to</div>
          <div className={styles.speakingName}>
            {student.name}, Class {student.grade}
          </div>
        </div>
      </div>

      <IdentityStrip identity={identity} />

      <div className={styles.content}>
        {phase === "guidance" && guidance && (
          <GuidanceView
            guidance={guidance}
            questionUsed={questionUsed}
            onAskQuestion={() => setPhase("question")}
          />
        )}
        {phase === "question" && guidance && (
          <QuestionView
            guidance={guidance}
            student={student}
            onBack={() => {
              setQuestionUsed(true);
              setPhase("guidance");
            }}
          />
        )}
      </div>

      {phase === "guidance" && (
        <div className={styles.footer}>
          <button className={styles.regenLink} onClick={handleRefresh}>
            Refresh guidance
          </button>
        </div>
      )}
    </div>
  );
}

// Icons
function CompassIcon({ size = 20 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
    </svg>
  );
}
function ReadIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}
function MoveIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}
function WatchIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}
function ArrowIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}
