import { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import Session from "./Session";
import Futures from "./Futures";
import Margdarshak from "./Margdarshak";
import Aawaz from "../components/Aawaz";
import { api } from "../lib/api";
import { applyTheme, getStoredTheme } from "../lib/theme";
import styles from "./Dashboard.module.css";

export default function Dashboard({ student: initialStudent, onLogout }) {
  const [student, setStudent] = useState(initialStudent);
  const [tab, setTab] = useState("session");
  const [shouldSimulate, setShouldSimulate] = useState(
    !!initialStudent.has_identity,
  );
  const [aawazDarpanLoading, setAawazDarpanLoading] = useState(false);
  const [aawazError, setAawazError] = useState("");
  const [margdarshakPrefill, setMargdarshakPrefill] = useState(null);

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
              onGoToSession={() => setTab("session")}
              onGoToMargdarshak={handleGoToMargdarshak}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
