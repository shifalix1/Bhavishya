import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../lib/api";
import Loader from "../components/Loader";
import styles from "./Margdarshak.module.css";

const MOVE_META = {
  do: {
    label: "Do this",
    color: "var(--accent)",
    dimColor: "var(--accent-dim)",
  },
  watch: {
    label: "Watch this",
    color: "var(--gold)",
    dimColor: "var(--gold-dim)",
  },
  ask: {
    label: "Ask this",
    color: "var(--success)",
    dimColor: "var(--success-dim)",
  },
  reflect: {
    label: "Reflect",
    color: "var(--text-sub)",
    dimColor: "var(--surface-alt)",
  },
};

function GuidanceSkeleton() {
  return (
    <div className={styles.skeletonWrap} aria-hidden="true">
      {/* Opening line skeleton */}
      <div className={styles.skeletonOpeningBlock}>
        <div className={styles.skeletonLine} style={{ width: "90%" }} />
        <div className={styles.skeletonLine} style={{ width: "70%" }} />
      </div>

      {/* Section: current read */}
      <div className={styles.skeletonSection}>
        <div className={styles.skeletonSectionLabel} style={{ width: 140 }} />
        <div className={styles.skeletonLine} style={{ width: "95%" }} />
        <div className={styles.skeletonLine} style={{ width: "80%" }} />
        <div className={styles.skeletonLine} style={{ width: "60%" }} />
      </div>

      <div className={styles.skeletonRule} />

      {/* Section: next move */}
      <div className={styles.skeletonSection}>
        <div className={styles.skeletonSectionLabel} style={{ width: 100 }} />
        <div className={styles.skeletonMoveCard}>
          <div className={styles.skeletonBadge} style={{ width: 72 }} />
          <div
            className={styles.skeletonLine}
            style={{ width: "85%", marginTop: 10 }}
          />
          <div className={styles.skeletonLine} style={{ width: "65%" }} />
        </div>
      </div>

      <div className={styles.skeletonRule} />

      {/* Section: question */}
      <div className={styles.skeletonSection}>
        <div className={styles.skeletonSectionLabel} style={{ width: 90 }} />
        <div className={styles.skeletonInputBox} />
        <div className={styles.skeletonBtn} style={{ width: 140 }} />
      </div>
    </div>
  );
}

function GateView({ onGoToSession }) {
  return (
    <div className={`page-enter ${styles.gateWrap}`}>
      <div className={styles.gateIcon}>
        <CompassSvg />
      </div>
      <span className="badge badge-neutral" style={{ marginBottom: 12 }}>
        Not yet
      </span>
      <h1 className="section-heading">Margdarshak hasn&apos;t met you yet.</h1>
      <p className="body-large" style={{ marginTop: 8, maxWidth: 460 }}>
        One Darpan session is all it takes. Margdarshak reads your identity
        fingerprint before saying anything — and it only says things it can
        actually stand behind.
      </p>
      <div className={styles.gateNote}>
        <div className="caption" style={{ marginBottom: 6 }}>
          Why the wait?
        </div>
        <p className="body-sm" style={{ color: "var(--text-sub)" }}>
          Generic guidance is worse than no guidance. Margdarshak needs your
          Darpan fingerprint to give you something specific — not a list of
          things that are true of everyone.
        </p>
      </div>
      <button
        className="btn btn-accent"
        style={{ marginTop: 8, borderRadius: "var(--r-sm)" }}
        onClick={onGoToSession}
      >
        Go to Darpan &rarr;
      </button>
    </div>
  );
}

export default function Margdarshak({
  student,
  onGoToSession,
  prefillQuestion,
  onPrefillUsed,
}) {
  const [guidance, setGuidance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [questionText, setQuestionText] = useState("");
  const [answer, setAnswer] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [questionLoading, setQuestionLoading] = useState(false);
  const [questionUsed, setQuestionUsed] = useState(false);
  const [questionError, setQuestionError] = useState("");
  const hasFetched = useRef(false);

  const fetchGuidance = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      // BUG 4 NOTE: language_preference must be written to cache during login
      // in Onboard.jsx (on the /login or /aawaz/chat response). If it's missing
      // here, it defaults to "english" correctly — but fix the cache write upstream.
      const res = await api.margdarshakGuidance(
        student.uid,
        student.name,
        student.grade,
        student.language_preference || "english",
      );
      setGuidance(res.guidance);
      setQuestionUsed(res.question_used ?? false);
      setAnswer("");
      setSubmittedQuestion("");
    } catch (e) {
      setError(e.message || "Could not load guidance. Try again.");
    } finally {
      setLoading(false);
    }
  }, [student.uid, student.name, student.grade, student.language_preference]);

  useEffect(() => {
    if (student.has_identity && !hasFetched.current) {
      hasFetched.current = true;
      fetchGuidance();
    }
  }, [student.has_identity, fetchGuidance]);

  // Auto-populate question if prefill comes from Futures bridge
  useEffect(() => {
    if (prefillQuestion && guidance && !questionUsed) {
      const t = setTimeout(() => {
        setQuestionText(prefillQuestion);
      }, 0);
      onPrefillUsed?.();
      return () => clearTimeout(t);
    }
  }, [prefillQuestion, guidance, questionUsed, onPrefillUsed]);

  const submitQuestion = async () => {
    const q = questionText.trim();
    if (!q || questionLoading) return;
    setSubmittedQuestion(q);
    setQuestionLoading(true);
    setQuestionError("");
    try {
      const res = await api.margdarshakQuestion(
        student.uid,
        student.name,
        student.grade,
        q,
        guidance,
        student.language_preference || "english",
      );
      setAnswer(res.answer);
      setQuestionUsed(true);
    } catch (e) {
      if (
        e.message?.includes("One question") ||
        e.message?.includes("429") ||
        e.message?.includes("session")
      ) {
        setQuestionUsed(true);
      } else {
        setQuestionError(e.message || "Something went wrong. Try again.");
      }
    } finally {
      setQuestionLoading(false);
    }
  };

  const handleQuestionKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitQuestion();
    }
  };

  if (!student.has_identity) return <GateView onGoToSession={onGoToSession} />;

  if (loading) {
    return (
      <div className={`page-enter ${styles.wrap}`}>
        <div className={styles.pageHeader}>
          <span className={styles.pageTag}>Margdarshak</span>
          <p className={styles.pageTagSub}>
            {student.name}, Class {student.grade}
          </p>
        </div>
        <p className={styles.skeletonReadingHint}>
          Reading your fingerprint&hellip;
        </p>
        <GuidanceSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`page-enter ${styles.errorState}`}>
        <p
          className="body-sm"
          style={{ color: "var(--error)", marginBottom: 12 }}
        >
          {error}
        </p>
        <button
          className="btn btn-surface btn-sm"
          style={{ borderRadius: "var(--r-sm)" }}
          onClick={fetchGuidance}
        >
          Try again
        </button>
      </div>
    );
  }

  if (!guidance) return null;

  const move = guidance.next_move || {};
  const moveMeta = MOVE_META[move.type] || MOVE_META.do;

  return (
    <div className={`page-enter ${styles.wrap}`}>
      <div className={styles.pageHeader}>
        <span className={styles.pageTag}>Margdarshak</span>
        <p className={styles.pageTagSub}>
          {student.name}, Class {student.grade}
        </p>
      </div>

      {guidance.opening_line && (
        <div className={styles.openingBlock}>
          <p className={styles.openingLine}>{guidance.opening_line}</p>
        </div>
      )}

      <section className={styles.section}>
        <div className={styles.sectionLabel}>Where you are right now</div>
        <p className={styles.currentRead}>{guidance.current_read}</p>
      </section>

      <div className={styles.rule} />

      <section className={styles.section}>
        <div className={styles.sectionLabel}>Your next move</div>
        <div
          className={styles.moveCard}
          style={{
            "--move-color": moveMeta.color,
            "--move-dim": moveMeta.dimColor,
          }}
        >
          <span
            className={styles.moveBadge}
            style={{ color: moveMeta.color, borderColor: moveMeta.color }}
          >
            {moveMeta.label}
          </span>
          <p className={styles.moveAction}>{move.action}</p>
          {move.why && <p className={styles.moveWhy}>{move.why}</p>}
          {guidance.watch_for && (
            <div className={styles.watchRow}>
              <span className={styles.watchLabel}>The signal</span>
              <span className={styles.watchText}>{guidance.watch_for}</span>
            </div>
          )}
        </div>
      </section>

      <div className={styles.rule} />

      <section className={styles.section}>
        <div className={styles.questionHead}>
          <div className={styles.sectionLabel}>One question</div>
          <p className={styles.questionSub}>
            Ask why. Ask what if. Ask what happens next. You get one per
            session.
          </p>
        </div>

        {questionUsed && !answer ? (
          <div className={styles.usedState}>
            <p className="body-sm" style={{ color: "var(--text-muted)" }}>
              Question used this session. Come back after your next Darpan.
            </p>
          </div>
        ) : answer ? (
          <div className={styles.answerBlock}>
            {submittedQuestion && (
              <p className={styles.echoQuestion}>{submittedQuestion}</p>
            )}
            <p className={styles.answerText}>{answer}</p>
            <p className={styles.answerNote}>
              That is your question for this session. Come back after your next
              Darpan.
            </p>
          </div>
        ) : (
          <div className={styles.questionInputArea}>
            <textarea
              className={`field-input ${styles.questionInput}`}
              placeholder="What do you actually want to know?"
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              onKeyDown={handleQuestionKey}
              rows={3}
            />
            {questionError && (
              <p className={styles.questionError}>{questionError}</p>
            )}
            <button
              className={`btn btn-primary ${styles.questionBtn}`}
              onClick={submitQuestion}
              disabled={questionLoading || !questionText.trim()}
            >
              {questionLoading ? (
                <Loader label="Thinking..." />
              ) : (
                "Ask Margdarshak"
              )}
            </button>
          </div>
        )}
      </section>

      <div className={styles.pageFooter}>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => {
            hasFetched.current = false;
            fetchGuidance();
          }}
          disabled={loading}
        >
          {loading ? <Loader label="" /> : "↺ Regenerate guidance"}
        </button>
        {guidance.generated_at && (
          <span className="caption">
            {new Date(guidance.generated_at).toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
            })}
          </span>
        )}
      </div>
    </div>
  );
}

function CompassSvg() {
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
      <circle
        cx="24"
        cy="24"
        r="23"
        stroke="var(--border-warm)"
        strokeWidth="1.5"
      />
      <circle cx="24" cy="24" r="2.5" fill="var(--text-muted)" />
      <polygon
        points="24,8 26.5,22 24,25.5 21.5,22"
        fill="var(--text-muted)"
        opacity="0.5"
      />
      <polygon
        points="24,40 21.5,26 24,22.5 26.5,26"
        fill="var(--text-muted)"
        opacity="0.25"
      />
    </svg>
  );
}
