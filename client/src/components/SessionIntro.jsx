import { useState } from "react";
import styles from "./SessionIntro.module.css";

export default function SessionIntro({ student, onChoose }) {
  const [skipText, setSkipText] = useState("");
  const [showSkipInput, setShowSkipInput] = useState(false);

  const cards = [
    {
      id: "aawaz",
      icon: <MicIcon />,
      label: "Talk to Aawaz",
      sub: "Have a conversation. Aawaz listens and asks questions.",
      accent: true,
    },
    {
      id: "type",
      icon: <TypeIcon />,
      label: "Type your story",
      sub: "Write about yourself. No conversation needed.",
    },
    {
      id: "skip",
      icon: <ZapIcon />,
      label: student.has_identity ? "View my Darpan" : "Paste and skip",
      sub: student.has_identity
        ? "You already have a fingerprint. View it now."
        : "Paste your own text and skip the interview.",
    },
    {
      id: "info",
      icon: <InfoIcon />,
      label: "What is Bhavishya?",
      sub: "Understand what the tool does and what these Hindi words mean.",
    },
  ];

  if (showSkipInput) {
    return (
      <div className={styles.skipWrap}>
        <button
          className={styles.backBtn}
          onClick={() => setShowSkipInput(false)}
        >
          Back
        </button>
        <h2 className={styles.skipHeading}>Paste your story</h2>
        <p className={styles.skipSub}>
          Write anything about yourself. Your interests, your confusion, what
          your parents expect, what you actually want. The more honest, the more
          accurate Darpan will be.
        </p>
        <textarea
          className={styles.skipTextarea}
          placeholder="I am in Class 9 and I honestly have no idea what I want to do. Math feels pointless but I love drawing..."
          value={skipText}
          onChange={(e) => setSkipText(e.target.value)}
          rows={8}
          autoFocus
        />
        <div className={styles.skipActions}>
          <span className={styles.charCount}>{skipText.length} characters</span>
          <button
            className={styles.skipSubmit}
            disabled={skipText.trim().length < 100}
            onClick={() => onChoose("paste", skipText.trim())}
          >
            Reveal my Darpan
          </button>
        </div>
        {skipText.trim().length > 0 && skipText.trim().length < 100 && (
          <p className={styles.skipHint}>
            Write at least 100 characters for an accurate fingerprint.
          </p>
        )}
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <div className={styles.greeting}>Hey {student.name}.</div>
        <p className={styles.sub}>
          {student.has_identity
            ? "You have been here before. What do you want to do today?"
            : "How do you want to start?"}
        </p>
      </div>

      <div className={styles.grid}>
        {cards.map((card) => (
          <button
            key={card.id}
            className={`${styles.card} ${card.accent ? styles.cardAccent : ""}`}
            onClick={() => {
              if (card.id === "skip" && !student.has_identity) {
                setShowSkipInput(true);
              } else {
                onChoose(card.id);
              }
            }}
          >
            <div
              className={`${styles.cardIcon} ${card.accent ? styles.cardIconAccent : ""}`}
            >
              {card.icon}
            </div>
            <div className={styles.cardText}>
              <span className={styles.cardLabel}>{card.label}</span>
              <span className={styles.cardSub}>{card.sub}</span>
            </div>
            <ArrowIcon />
          </button>
        ))}
      </div>

      {student.session_count > 0 && (
        <div className={styles.sessionBadge}>
          Session {student.session_count} completed
        </div>
      )}
    </div>
  );
}

function MicIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>
  );
}
function TypeIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  );
}
function ZapIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}
function InfoIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}
function ArrowIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0, opacity: 0.4 }}
    >
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}
