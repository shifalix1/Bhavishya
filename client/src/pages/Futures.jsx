import { useState } from "react";
import { api } from "../lib/api";
import FutureCard from "../components/FutureCard";
import Loader from "../components/Loader";
import styles from "./Futures.module.css";

function FutureSkeleton({ index }) {
  const labels = ["Expected path", "Inner call", "Unseen door"];
  const widths = [
    ["72%", "88%", "60%"],
    ["80%", "65%", "90%"],
    ["68%", "85%", "55%"],
  ];
  return (
    <div
      className={styles.skeletonCard}
      style={{ animationDelay: `${index * 0.12}s` }}
      aria-hidden="true"
    >
      <div className={styles.skeletonBadge} style={{ width: 90 }} />
      <div className={styles.skeletonTitle} style={{ width: "55%" }} />
      <div className={styles.skeletonBody}>
        {widths[index].map((w, i) => (
          <div key={i} className={styles.skeletonLine} style={{ width: w }} />
        ))}
        <div className={styles.skeletonLine} style={{ width: "40%" }} />
      </div>
      <div className={styles.skeletonMeta}>
        <div className={styles.skeletonChip} style={{ width: 64 }} />
        <div className={styles.skeletonChip} style={{ width: 80 }} />
      </div>
      <div
        className={styles.skeletonLabel}
        style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 8 }}
      >
        {labels[index]}
      </div>
    </div>
  );
}

export default function Futures({
  student,
  shouldSimulate,
  onGoToSession,
  onGoToMargdarshak,
}) {
  const [futures, setFutures] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const simulate = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.simulate(student.name, student.grade, student.uid);
      setFutures(res.futures || []);
    } catch (e) {
      setError(e.message || "Simulation failed. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleAskMargdarshak = (prefillQuestion) => {
    try {
      sessionStorage.setItem("margdarshak_prefill", prefillQuestion);
    } catch (e) {
      console.warn("Could not set margdarshak_prefill in sessionStorage", e);
    }
    onGoToMargdarshak?.();
  };

  if (!shouldSimulate) {
    return (
      <div className={`page-enter ${styles.gateWrap}`}>
        <div className={styles.gateIcon}>
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <circle
              cx="24"
              cy="24"
              r="23"
              stroke="var(--border-warm)"
              strokeWidth="1.5"
            />
            <path
              d="M24 14v10l6 4"
              stroke="var(--text-muted)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <span className="badge badge-neutral" style={{ marginBottom: 12 }}>
          Not yet
        </span>
        <h1 className="section-heading">Come back after a session.</h1>
        <p className="body-large" style={{ marginTop: 8, maxWidth: 440 }}>
          Bhavishya needs to hear your story before it can show you your
          futures. One conversation is a hello. Come back after that, and it
          becomes a mirror.
        </p>
        <div className={styles.gateNote}>
          <div className="caption" style={{ marginBottom: 6 }}>
            Why?
          </div>
          <p className="body-sm" style={{ color: "var(--text-sub)" }}>
            Your three futures are grounded in who you actually are, not a
            generic template. The identity fingerprint from Darpan is what makes
            them specific to you.
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

  return (
    <div className={`page-enter ${styles.wrap}`}>
      <div className={styles.intro}>
        <span className={styles.introLabel}>Bhavishya Core</span>
        <h1 className="section-heading" style={{ marginTop: 6 }}>
          Your futures
        </h1>
        <p
          className="body-large"
          style={{ marginTop: 8, color: "var(--text-sub)" }}
        >
          Three honest paths. All grounded in real career data. You choose.
        </p>
      </div>

      {!futures && !loading && (
        <div className={styles.cta}>
          <p className="body-sm" style={{ color: "var(--text-muted)" }}>
            Based on your identity fingerprint, Bhavishya will simulate three
            parallel futures specific to who you actually are.
          </p>
          <button
            className="btn btn-accent btn-lg"
            style={{ borderRadius: "var(--r-sm)" }}
            onClick={simulate}
            disabled={loading}
          >
            Show my futures
          </button>
          {error && (
            <p className="body-sm" style={{ color: "var(--error)" }}>
              {error}
            </p>
          )}
        </div>
      )}

      {loading && (
        <div className={styles.skeletonWrap} aria-label="Loading your futures">
          <p className={styles.skeletonHint}>Simulating your futures&hellip;</p>
          <div className={styles.cards}>
            <FutureSkeleton index={0} />
            <FutureSkeleton index={1} />
            <FutureSkeleton index={2} />
          </div>
        </div>
      )}

      {futures && futures.length > 0 && (
        <>
          <div className={styles.cards}>
            {futures.map((f, i) => (
              <FutureCard
                key={i}
                future={f}
                index={i}
                student={student}
                onAskMargdarshak={handleAskMargdarshak}
              />
            ))}
          </div>
          <div className={styles.regenRow}>
            <button
              className="btn btn-ghost btn-sm"
              onClick={simulate}
              disabled={loading}
            >
              {loading ? <Loader label="" /> : "↺ Regenerate futures"}
            </button>
            <span className="caption">
              Run a new Darpan session first for better results.
            </span>
          </div>
          {error && (
            <p className="body-sm" style={{ color: "var(--error)" }}>
              {error}
            </p>
          )}
        </>
      )}
    </div>
  );
}
