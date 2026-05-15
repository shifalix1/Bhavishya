import { useState, useCallback } from "react";
import ThemeToggle from "./ThemeToggle";
import { api } from "../lib/api";
import styles from "./Sidebar.module.css";

const NAV = [
  { id: "aawaz", label: "Aawaz", sub: "Listen and speak" },
  { id: "session", label: "Darpan", sub: "Identity mirror" },
  { id: "margdarshak", label: "Margdarshak", sub: "Your guide" },
  { id: "futures", label: "Bhavishya Core", sub: "Your futures" },
];

function SessionDrawer({ session, onClose }) {
  const identity = session.identity;
  const futures = session.futures;
  const marg = session.margdarshak || [];

  return (
    <div className={styles.drawer}>
      <div className={styles.drawerHeader}>
        <span className={styles.drawerTitle}>Session {session.session}</span>
        <button className={styles.drawerClose} onClick={onClose}>
          ✕
        </button>
      </div>

      <div className={styles.drawerBody}>
        {identity && (
          <div className={styles.drawerSection}>
            <div className={styles.drawerSectionLabel}>Darpan Reveal</div>
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
            {identity.identity_confidence !== undefined && (
              <span className={styles.drawerConf}>
                Confidence: {identity.identity_confidence}/10
              </span>
            )}
          </div>
        )}

        {marg.length > 0 && (
          <div className={styles.drawerSection}>
            <div className={styles.drawerSectionLabel}>Margdarshak</div>
            {marg.map((m, i) => (
              <div key={i} className={styles.drawerQA}>
                <p className={styles.drawerQ}>"{m.question}"</p>
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
                  {f.type?.replace("_", " ")}
                </span>
                <span className={styles.drawerFutureTitle}>{f.title}</span>
              </div>
            ))}
          </div>
        )}

        {!identity && marg.length === 0 && !futures && (
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

  const loadHistory = useCallback(async () => {
    if (history || historyLoading) return;
    setHistoryLoading(true);
    try {
      const res = await api.getHistory(student.uid);
      setHistory(res);
    } catch (e) {
      console.warn("Could not load history", e);
    } finally {
      setHistoryLoading(false);
    }
  }, [student.uid, history, historyLoading]);

  const handleSessionClick = async (sessionNum) => {
    await loadHistory();
    setOpenSession(sessionNum);
  };

  const openSessionData = history?.sessions?.find(
    (s) => s.session === openSession,
  );

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
          {historyLoading && (
            <p className={styles.historyLoading}>Loading...</p>
          )}
          <div className={styles.sessionList}>
            {Array.from({ length: sessionCount }, (_, i) => {
              const num = i + 1;
              const snap = history?.sessions?.find((s) => s.session === num);
              const hasDarpan = !!snap?.identity;
              const hasFutures = snap?.futures?.length > 0;
              const hasMarg = snap?.margdarshak?.length > 0;
              return (
                <button
                  key={num}
                  className={`${styles.sessionItem} ${openSession === num ? styles.sessionItemActive : ""}`}
                  onClick={() => handleSessionClick(num)}
                >
                  <div className={styles.sessionDot} />
                  <div className={styles.sessionMeta}>
                    <span className={styles.sessionLabel}>Session {num}</span>
                    <span className={styles.sessionPills}>
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

      {openSession && openSessionData && (
        <SessionDrawer
          session={openSessionData}
          onClose={() => setOpenSession(null)}
        />
      )}

      <div className={styles.footer}>
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
