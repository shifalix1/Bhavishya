import { useState } from "react";
import { api } from "../lib/api";
import SessionIntro from "../components/SessionIntro";
import WhatIsDarpan from "../components/WhatIsDarpan";
import IdentityPanel from "../components/IdentityPanel";
import Loader from "../components/Loader";
import styles from "./Session.module.css";

export default function Session({
  student,
  onIdentityReady,
  onGoToAawaz,
  onGoToMargdarshak,
}) {
  const [phase, setPhase] = useState(
    student.has_identity ? "darpan_existing" : "intro",
  );
  const [identity, setIdentity] = useState(student.identity_current || null);
  const [error, setError] = useState("");

  const handleIntroChoice = (choice, pasteText) => {
    if (choice === "info") {
      setPhase("info");
    } else if (choice === "aawaz") {
      onGoToAawaz?.();
    } else if (choice === "margdarshak") {
      onGoToMargdarshak?.();
    } else if (choice === "paste" && pasteText) {
      // "write" path in SessionIntro calls onChoose("paste", text)
      handleReadyForDarpan(pasteText);
    }
    // note: "skip" branch removed — SessionIntro never emits it
  };

  const handleReadyForDarpan = async (combinedInput) => {
    if (!combinedInput?.trim()) return;
    setPhase("loading");
    setError("");
    try {
      const res = await api.session(
        student.name,
        student.grade,
        combinedInput,
        student.uid,
      );
      setIdentity(res.identity);
      onIdentityReady(res);
      setTimeout(() => setPhase("darpan"), 400);
    } catch (e) {
      setError(e.message || "Something went wrong. Try again.");
      setPhase("intro");
    }
  };

  if (phase === "loading") {
    return (
      <div className={styles.loadingPhase}>
        <div className={styles.loadingOrb} />
        <p className={styles.loadingLabel}>Reading your fingerprint...</p>
        <Loader label="" />
      </div>
    );
  }

  if (phase === "info") {
    return (
      <div className={`page-enter ${styles.innerPhase}`}>
        <WhatIsDarpan onBack={() => setPhase("intro")} />
      </div>
    );
  }

  if ((phase === "darpan" || phase === "darpan_existing") && identity) {
    return (
      <div className={`page-enter ${styles.darpanPhase}`}>
        <div className={styles.darpanHeader}>
          <div className={styles.darpanBadge}>
            {phase === "darpan_existing" ? "Your Darpan" : "Darpan"}
          </div>
          <h1 className={styles.darpanHeading}>
            {phase === "darpan_existing"
              ? `${student.name}, this is your fingerprint.`
              : `${student.name}, this is you.`}
          </h1>
          <p className={styles.darpanSub}>
            {phase === "darpan_existing"
              ? "From your last session. Start a new one to update it."
              : "This is what I heard. What you probably have not said out loud yet."}
          </p>
        </div>
        {error && <div className={styles.errorBanner}>{error}</div>}
        <IdentityPanel identity={identity} />
        <button className={styles.redoBtn} onClick={() => setPhase("intro")}>
          Start a new session
        </button>
      </div>
    );
  }

  return (
    <div className={`page-enter ${styles.innerPhase}`}>
      {error && <div className={styles.errorBanner}>{error}</div>}
      <SessionIntro student={student} onChoose={handleIntroChoice} />
    </div>
  );
}
