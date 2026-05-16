import { useState, useCallback, useRef, useEffect } from "react";
import ThemeToggle from "./ThemeToggle";
import { api } from "../lib/api";
import styles from "./Sidebar.module.css";

const NAV = [
  { id: "aawaz", label: "Aawaz", sub: "Listen and speak" },
  { id: "session", label: "Darpan", sub: "Identity mirror" },
  { id: "margdarshak", label: "Margdarshak", sub: "Your guide" },
  { id: "futures", label: "Bhavishya Core", sub: "Your futures" },
];

// ── Hoisted above all consumers ───────────────────────────────────────────────
function CloseIcon() {
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
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function diffIdentity(prev, curr) {
  if (!prev || !curr) return null;
  const changes = [];

  const prevConf = prev.identity_confidence ?? 0;
  const currConf = curr.identity_confidence ?? 0;
  if (Math.abs(prevConf - currConf) >= 1) {
    changes.push(
      `Confidence ${prevConf < currConf ? "up" : "down"} from ${prevConf} to ${currConf}/10`,
    );
  }

  const prevVals = new Set(
    (prev.core_values || []).map((v) => v.toLowerCase()),
  );
  const currVals = new Set(
    (curr.core_values || []).map((v) => v.toLowerCase()),
  );
  const addedVals = [...currVals].filter((v) => !prevVals.has(v));
  const removedVals = [...prevVals].filter((v) => !currVals.has(v));
  if (addedVals.length) changes.push(`New values: ${addedVals.join(", ")}`);
  if (removedVals.length)
    changes.push(`Values dropped: ${removedVals.join(", ")}`);

  const prevFears = new Set(
    (prev.active_fears || []).map((v) => v.toLowerCase()),
  );
  const currFears = new Set(
    (curr.active_fears || []).map((v) => v.toLowerCase()),
  );
  const resolvedFears = [...prevFears].filter((v) => !currFears.has(v));
  const newFears = [...currFears].filter((v) => !prevFears.has(v));
  if (resolvedFears.length) changes.push(`Fear resolved: ${resolvedFears[0]}`);
  if (newFears.length) changes.push(`New fear: ${newFears[0]}`);

  return changes.length ? changes : null;
}

function AawazTranscript({ turns }) {
  const [expanded, setExpanded] = useState(false);
  if (!turns || turns.length === 0) return null;
  const preview = turns.slice(0, 4);
  const rest = turns.slice(4);

  return (
    <div className={styles.aawazTranscript}>
      <div className={styles.drawerSectionLabel}>Aawaz conversation</div>
      <div className={styles.transcriptList}>
        {(expanded ? turns : preview).map((m, i) => (
          <div
            key={i}
            className={`${styles.transcriptMsg} ${
              m.role === "user" ? styles.transcriptUser : styles.transcriptAawaz
            }`}
          >
            <span className={styles.transcriptRole}>
              {m.role === "user" ? "You" : "Aawaz"}
            </span>
            <span className={styles.transcriptText}>{m.content}</span>
          </div>
        ))}
      </div>
      {rest.length > 0 && (
        <button
          className={styles.expandBtn}
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? "Show less" : `+${rest.length} more`}
        </button>
      )}
    </div>
  );
}

function SessionCycle({ hasAawaz, hasDarpan, hasMarg, hasFutures }) {
  const steps = [
    { key: "aawaz", label: "Aawaz", done: hasAawaz },
    { key: "darpan", label: "Darpan", done: hasDarpan },
    { key: "marg", label: "Margdarshak", done: hasMarg },
    { key: "futures", label: "Futures", done: hasFutures },
  ];
  return (
    <div className={styles.cycleRow}>
      {steps.map((s, i) => (
        <div key={s.key} className={styles.cycleStep}>
          <div
            className={`${styles.cycleDot} ${s.done ? styles.cycleDotDone : ""}`}
          />
          <span
            className={`${styles.cycleLabel} ${s.done ? styles.cycleLabelDone : ""}`}
          >
            {s.label}
          </span>
          {i < steps.length - 1 && (
            <div
              className={`${styles.cycleLine} ${s.done ? styles.cycleLineDone : ""}`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// FIX: SessionDrawer now accepts isLoading and sessionNum so it can render
// a skeleton immediately on first click instead of silently not mounting.
// Previously: drawer only rendered when openSessionData was truthy, which was
// never the case on the first click because history hadn't loaded yet.
function SessionDrawer({
  sessionData,
  prevSessionData,
  onClose,
  isLoading,
  sessionNum,
}) {
  if (isLoading) {
    return (
      <div className={styles.drawer}>
        <div className={styles.drawerHeader}>
          <div className={styles.drawerTitleRow}>
            <span className={styles.drawerTitle}>Session {sessionNum}</span>
          </div>
          <button className={styles.drawerClose} onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <div className={styles.drawerBody}>
          {/* Skeleton blocks matching the shape of real content */}
          <div className={styles.cycleRow} style={{ opacity: 0.35 }}>
            {["Aawaz", "Darpan", "Margdarshak", "Futures"].map(
              (label, i, arr) => (
                <div key={label} className={styles.cycleStep}>
                  <div className={styles.cycleDot} />
                  <span className={styles.cycleLabel}>{label}</span>
                  {i < arr.length - 1 && <div className={styles.cycleLine} />}
                </div>
              ),
            )}
          </div>
          <p className={styles.drawerMuted}>Loading session data…</p>
        </div>
      </div>
    );
  }

  if (!sessionData) {
    return (
      <div className={styles.drawer}>
        <div className={styles.drawerHeader}>
          <span className={styles.drawerTitle}>Session {sessionNum}</span>
          <button className={styles.drawerClose} onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <div className={styles.drawerBody}>
          <p className={styles.drawerMuted}>
            No data recorded for this session yet.
          </p>
        </div>
      </div>
    );
  }

  const identity = sessionData.identity;
  const futures = sessionData.futures;
  const marg = sessionData.margdarshak || [];
  const aawazTurns = sessionData.aawaz_turns || [];

  const changes = prevSessionData
    ? diffIdentity(prevSessionData.identity, identity)
    : null;

  const hasAawaz = aawazTurns.length > 0;
  const hasDarpan = !!identity;
  const hasMarg = marg.length > 0;
  const hasFutures = !!(futures && futures.length > 0);

  return (
    <div className={styles.drawer}>
      <div className={styles.drawerHeader}>
        <div className={styles.drawerTitleRow}>
          <span className={styles.drawerTitle}>
            Session {sessionData.session}
          </span>
          {sessionData.session > 1 && changes && (
            <span className={styles.changesBadge}>
              {changes.length} change{changes.length > 1 ? "s" : ""}
            </span>
          )}
        </div>
        <button className={styles.drawerClose} onClick={onClose}>
          <CloseIcon />
        </button>
      </div>

      <div className={styles.drawerBody}>
        <SessionCycle
          hasAawaz={hasAawaz}
          hasDarpan={hasDarpan}
          hasMarg={hasMarg}
          hasFutures={hasFutures}
        />

        {changes && changes.length > 0 && (
          <div className={styles.changesBlock}>
            <div className={styles.drawerSectionLabel}>
              What changed since last session
            </div>
            {changes.map((c, i) => (
              <div key={i} className={styles.changeItem}>
                <span className={styles.changeDot} />
                <span className={styles.changeText}>{c}</span>
              </div>
            ))}
          </div>
        )}

        {sessionData.session > 1 && sessionData.context_summary && (
          <div className={styles.contextBlock}>
            <div className={styles.drawerSectionLabel}>
              Context carried forward
            </div>
            <p className={styles.contextText}>{sessionData.context_summary}</p>
          </div>
        )}

        {aawazTurns.length > 0 && <AawazTranscript turns={aawazTurns} />}

        {identity && (
          <div className={styles.drawerSection}>
            <div className={styles.drawerSectionLabel}>Darpan fingerprint</div>
            <p className={styles.drawerText}>{identity.thinking_style}</p>
            {identity.energy_signature && (
              <p className={styles.drawerMuted}>{identity.energy_signature}</p>
            )}
            <div className={styles.drawerTags}>
              {(identity.core_values || []).map((v, i) => (
                <span key={i} className={styles.drawerTag}>
                  {v}
                </span>
              ))}
            </div>
            {identity.active_fears?.length > 0 && (
              <div className={styles.fearRow}>
                {identity.active_fears.slice(0, 2).map((f, i) => (
                  <span
                    key={i}
                    className={`${styles.drawerTag} ${styles.fearTag}`}
                  >
                    {f}
                  </span>
                ))}
              </div>
            )}
            {identity.identity_confidence !== undefined && (
              <div className={styles.confRow}>
                <span className={styles.drawerConf}>
                  Confidence: {identity.identity_confidence}/10
                </span>
                <div className={styles.confBarMini}>
                  <div
                    className={styles.confBarMiniFill}
                    style={{
                      width: `${(identity.identity_confidence / 10) * 100}%`,
                      background:
                        identity.identity_confidence >= 7
                          ? "var(--success)"
                          : identity.identity_confidence >= 4
                            ? "var(--gold)"
                            : "var(--error)",
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {marg.length > 0 && (
          <div className={styles.drawerSection}>
            <div className={styles.drawerSectionLabel}>
              Margdarshak guidance
            </div>
            {marg.map((m, i) => (
              <div key={i} className={styles.drawerQA}>
                {m.question && <p className={styles.drawerQ}>"{m.question}"</p>}
                <p className={styles.drawerA}>{m.answer}</p>
              </div>
            ))}
          </div>
        )}

        {futures && futures.length > 0 && (
          <div className={styles.drawerSection}>
            <div className={styles.drawerSectionLabel}>Futures simulated</div>
            {futures.map((f, i) => (
              <div key={i} className={styles.drawerFuture}>
                <span className={styles.drawerFutureType}>
                  {f.type?.replace(/_/g, " ")}
                </span>
                <span className={styles.drawerFutureTitle}>{f.title}</span>
              </div>
            ))}
          </div>
        )}

        {!hasDarpan && !hasMarg && !hasFutures && aawazTurns.length === 0 && (
          <p className={styles.drawerMuted}>
            No data recorded for this session yet.
          </p>
        )}
      </div>
    </div>
  );
}

export default function Sidebar({ student, tab, onTab, onLogout }) {
  const sessionCount = student.session_count || 0;
  const [history, setHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [openSession, setOpenSession] = useState(null);
  const [language, setLanguage] = useState(
    student.language_preference || "english",
  );

  // fetchingRef: guards against duplicate in-flight fetches.
  const fetchingRef = useRef(false);
  const historyRef = useRef(null);

  // CRITICAL FIX: fetch history from backend on mount so Chrome and VS Code
  // browser share the same session history. Never rely on localStorage alone.
  useEffect(() => {
    if (sessionCount > 0 && !historyRef.current && !fetchingRef.current) {
      fetchingRef.current = true;
      setHistoryLoading(true);
      api
        .getHistory(student.uid)
        .then((res) => {
          historyRef.current = res;
          setHistory(res);
        })
        .catch((e) => console.warn("Could not load history on mount", e))
        .finally(() => {
          setHistoryLoading(false);
          fetchingRef.current = false;
        });
    }
  }, [student.uid, sessionCount]);

  const handleLogout = () => {
    try {
      localStorage.removeItem("bhavishya_auth");
      localStorage.removeItem("bhavishya_uid");
      localStorage.removeItem("bhavishya_student");
    } catch (e) {
      console.error("Error clearing cache:", e);
    }
    onLogout?.();
  };

  const handleLanguageChange = useCallback(
    async (lang) => {
      setLanguage(lang);
      try {
        await api.setPreference(student.uid, lang);
      } catch (e) {
        console.warn("Could not save language preference", e);
      }
    },
    [student.uid],
  );

  const loadHistory = useCallback(async () => {
    // Read from ref — stable across renders, no stale-closure risk
    if (historyRef.current) return historyRef.current;
    if (fetchingRef.current) return null;
    fetchingRef.current = true;
    setHistoryLoading(true);
    try {
      const res = await api.getHistory(student.uid);
      historyRef.current = res;
      setHistory(res);
      return res;
    } catch (e) {
      console.warn("Could not load history", e);
      return null;
    } finally {
      setHistoryLoading(false);
      fetchingRef.current = false;
    }
  }, [student.uid]); // history removed — read via historyRef instead

  // FIX: open drawer immediately so SessionDrawer mounts with its loading
  // skeleton. Old code awaited loadHistory() before setOpenSession, so
  // openSessionData was always null during the fetch — drawer never rendered.
  const handleSessionClick = useCallback(
    async (sessionNum) => {
      if (openSession === sessionNum) {
        setOpenSession(null);
        return;
      }
      // Mount drawer right away — it will show loading skeleton if data isn't ready
      setOpenSession(sessionNum);
      if (!historyRef.current && !fetchingRef.current) {
        await loadHistory();
        // State update from loadHistory triggers re-render with real data
      }
    },
    [openSession, loadHistory], // history removed — read via historyRef instead
  );

  const openSessionData = history?.sessions?.find(
    (s) => s.session === openSession,
  );
  const prevSessionData =
    openSession > 1
      ? history?.sessions?.find((s) => s.session === openSession - 1)
      : null;

  const drawerIsLoading =
    openSession !== null && historyLoading && !openSessionData;

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <span className={styles.brandName}>Bhavishya</span>
        <span className={styles.brandSub}>AI Career Companion</span>
      </div>

      <div className={styles.studentCard}>
        <div className={styles.avatar}>{student.name[0].toUpperCase()}</div>
        <div>
          <div className={styles.studentName}>{student.name}</div>
          <div className={styles.studentMeta}>
            Class {student.grade}
            {sessionCount > 0 &&
              ` · ${sessionCount} session${sessionCount > 1 ? "s" : ""}`}
          </div>
        </div>
      </div>

      <nav className={styles.nav}>
        <div className={styles.navHeading}>Navigation</div>
        {NAV.map((n) => (
          <button
            key={n.id}
            className={`${styles.navItem} ${tab === n.id ? styles.active : ""}`}
            onClick={() => onTab(n.id)}
          >
            <span className={styles.navLabel}>{n.label}</span>
            <span className={styles.navSub}>{n.sub}</span>
          </button>
        ))}
      </nav>

      {sessionCount > 0 && (
        <div className={styles.sessions}>
          <div className={styles.navHeading}>Session history</div>
          {historyLoading && <p className={styles.historyLoading}>Loading…</p>}
          <div className={styles.sessionList}>
            {Array.from({ length: sessionCount }, (_, i) => {
              const num = i + 1;
              const snap = history?.sessions?.find((s) => s.session === num);
              // FIX: removed history?.aawaz_history fallback — new API returns
              // aawaz_turns per session inside each session object, not flat.
              const hasDarpan = !!snap?.identity;
              const hasFutures = !!(snap?.futures?.length > 0);
              const hasMarg = !!(snap?.margdarshak?.length > 0);
              const hasAawaz = !!(snap?.aawaz_turns?.length > 0);
              return (
                <button
                  key={num}
                  className={`${styles.sessionItem} ${
                    openSession === num ? styles.sessionItemActive : ""
                  }`}
                  onClick={() => handleSessionClick(num)}
                >
                  <div className={styles.sessionDot} />
                  <div className={styles.sessionMeta}>
                    <span className={styles.sessionLabel}>Session {num}</span>
                    <span className={styles.sessionPills}>
                      {hasAawaz && (
                        <span className={styles.pill} title="Aawaz">
                          A
                        </span>
                      )}
                      {hasDarpan && (
                        <span className={styles.pill} title="Darpan done">
                          D
                        </span>
                      )}
                      {hasMarg && (
                        <span className={styles.pill} title="Margdarshak">
                          M
                        </span>
                      )}
                      {hasFutures && (
                        <span className={styles.pill} title="Futures">
                          F
                        </span>
                      )}
                    </span>
                    {num === sessionCount && (
                      <span className={styles.sessionCurrent}>current</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* FIX: render whenever openSession is set — not gated on openSessionData */}
      {openSession !== null && (
        <SessionDrawer
          sessionData={openSessionData}
          prevSessionData={prevSessionData}
          onClose={() => setOpenSession(null)}
          isLoading={drawerIsLoading}
          sessionNum={openSession}
        />
      )}

      <div className={styles.footer}>
        <div className={styles.langPill}>
          {[
            { value: "english", label: "EN" },
            { value: "hinglish", label: "HI/EN" },
            { value: "hindi", label: "हिंदी" },
          ].map((opt) => (
            <button
              key={opt.value}
              className={`${styles.langPillBtn} ${language === opt.value ? styles.langPillActive : ""}`}
              onClick={() => handleLanguageChange(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className={styles.footerRow}>
          <ThemeToggle />
          {onLogout && (
            <button className={styles.logoutBtn} onClick={handleLogout}>
              Log out
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
