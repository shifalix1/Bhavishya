import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import Session from "./Session";
import Futures from "./Futures";
import Margdarshak from "./Margdarshak";
import Aawaz from "../components/Aawaz";
import { api } from "../lib/api";
import { applyTheme, getStoredTheme } from "../lib/theme";
import styles from "./Dashboard.module.css";

// Shows delta between current identity and last session snapshot.
// Only renders if there's something meaningful to surface.
function InsightBanner({ student, onDismiss }) {
  const delta = student.identity_delta;
  const lastSession = student.last_session_summary;
  if (!delta && !lastSession) return null;

  const prev = delta?.previous_confidence;
  const curr = delta?.current_confidence;
  const resolvedFear = delta?.resolved_fears?.[0];
  const newStrength = delta?.new_strengths?.[0];
  const margdarshakHint = lastSession?.has_new_move;

  const lines = [];
  if (prev != null && curr != null && curr > prev) {
    lines.push(`Confidence ${prev} → ${curr} since your last session.`);
  }
  if (resolvedFear) {
    lines.push(`"${resolvedFear}" — looks resolved.`);
  }
  if (newStrength) {
    lines.push(`New strength surfaced: ${newStrength}.`);
  }
  if (margdarshakHint) {
    lines.push(`Margdarshak has a new move for you.`);
  }

  if (!lines.length) return null;

  return (
    <div className={styles.insightBanner}>
      <div className={styles.insightLines}>
        {lines.map((l, i) => (
          <span key={i} className={styles.insightLine}>
            {l}
          </span>
        ))}
      </div>
      <button
        className={styles.insightDismiss}
        onClick={onDismiss}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

export default function Dashboard({ student: initialStudent, onLogout }) {
  const [student, setStudent] = useState(initialStudent);
  const [tab, setTab] = useState("session");
  const [shouldSimulate, setShouldSimulate] = useState(
    !!initialStudent.has_identity,
  );
  const [futures, setFutures] = useState(null);
  const [aawazDarpanLoading, setAawazDarpanLoading] = useState(false);
  const [aawazError, setAawazError] = useState("");
  const [margdarshakPrefill, setMargdarshakPrefill] = useState(null);
  const [showInsightBanner, setShowInsightBanner] = useState(
    // Only show if the login response carried delta data
    !!(initialStudent.identity_delta || initialStudent.last_session_summary),
  );

  useEffect(() => {
    applyTheme(getStoredTheme());
  }, []);

  const handleIdentityReady = (res) => {
    setStudent((s) => ({
      ...s,
      session_count: res.session_count,
      has_identity: true,
      identity_current: res.identity,
    }));
    setShouldSimulate(res.should_simulate ?? true);
  };

  const handleAawazReadyForDarpan = async (combinedInput) => {
    if (!combinedInput?.trim()) return;
    setAawazDarpanLoading(true);
    setAawazError("");
    try {
      const res = await api.session(
        student.name,
        student.grade,
        combinedInput,
        student.uid,
      );
      handleIdentityReady(res);
      setTab("session");
    } catch (e) {
      setAawazError(e.message || "Something went wrong. Try again.");
    } finally {
      setAawazDarpanLoading(false);
    }
  };

  const handleGoToMargdarshak = () => {
    try {
      const prefill = sessionStorage.getItem("margdarshak_prefill");
      if (prefill) {
        setMargdarshakPrefill(prefill);
        sessionStorage.removeItem("margdarshak_prefill");
      }
    } catch (e) {
      console.warn(
        "Could not retrieve margdarshak_prefill from sessionStorage",
        e,
      );
    }
    setTab("margdarshak");
  };

  return (
    <div className={styles.layout}>
      <Sidebar student={student} tab={tab} onTab={setTab} onLogout={onLogout} />

      <main className={styles.main}>
        {showInsightBanner && (
          <InsightBanner
            student={student}
            onDismiss={() => setShowInsightBanner(false)}
          />
        )}

        {/* Aawaz: always mounted, shown/hidden via CSS so state is never lost */}
        <div
          className={styles.aawazPane}
          style={{ display: tab === "aawaz" ? "flex" : "none" }}
          aria-hidden={tab !== "aawaz"}
        >
          {aawazError && <div className={styles.errorBanner}>{aawazError}</div>}
          <Aawaz
            student={student}
            loading={aawazDarpanLoading}
            onReadyForDarpan={handleAawazReadyForDarpan}
          />
        </div>

        {/* Session tab */}
        <div
          className={styles.contentPane}
          style={{ display: tab === "session" ? "flex" : "none" }}
          aria-hidden={tab !== "session"}
        >
          <div className={styles.content}>
            <Session
              student={student}
              onIdentityReady={handleIdentityReady}
              onGoToAawaz={() => setTab("aawaz")}
              onGoToMargdarshak={handleGoToMargdarshak}
            />
          </div>
        </div>

        {/* Margdarshak tab */}
        <div
          className={styles.contentPane}
          style={{ display: tab === "margdarshak" ? "flex" : "none" }}
          aria-hidden={tab !== "margdarshak"}
        >
          <div className={styles.content}>
            <Margdarshak
              key={student.uid}
              student={student}
              onGoToSession={() => setTab("session")}
              prefillQuestion={margdarshakPrefill}
              onPrefillUsed={() => setMargdarshakPrefill(null)}
            />
          </div>
        </div>

        {/* Futures tab */}
        <div
          className={styles.contentPane}
          style={{ display: tab === "futures" ? "flex" : "none" }}
          aria-hidden={tab !== "futures"}
        >
          <div className={styles.content}>
            <Futures
              student={student}
              shouldSimulate={shouldSimulate}
              futures={futures}
              onFuturesReady={setFutures}
              onGoToSession={() => setTab("session")}
              onGoToMargdarshak={handleGoToMargdarshak}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
