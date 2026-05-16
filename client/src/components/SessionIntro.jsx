import { useState } from "react";
import styles from "./SessionIntro.module.css";

export default function SessionIntro({ student, onChoose }) {
  const [writeText, setWriteText] = useState("");
  const [showWriteInput, setShowWriteInput] = useState(false);

  // Card 1: Chat with Aawaz (text conversation - mic removed, STT not active)
  // Card 2: Write & paste directly (skip Aawaz, go straight to Darpan)
  // Card 3: Go to Margdarshak (only if has identity)
  // Card 4: What is Bhavishya?
  const cards = [
    {
      id: "aawaz",
      icon: <ChatIcon />,
      label: "Chat with Aawaz",
      sub: "Have a real conversation. Aawaz listens, asks questions, then builds your fingerprint.",
      accent: true,
    },
    {
      id: "write",
      icon: <TypeIcon />,
      label: "Write your story",
      sub: "No back-and-forth. Just write honestly and get your Darpan instantly.",
    },
    {
      id: "margdarshak",
      icon: <CompassIcon />,
      label: "Go to Margdarshak",
      sub: student.has_identity
        ? "Your guide is ready. Get your next move or ask a question."
        : "Complete one Darpan session first to unlock your guide.",
      disabled: !student.has_identity,
    },
    {
      id: "info",
      icon: <InfoIcon />,
      label: "What is Bhavishya?",
      sub: "Understand what each module does and what the Hindi words mean.",
    },
  ];

  if (showWriteInput) {
    return (
      <div className={styles.skipWrap}>
        <button
          className={styles.backBtn}
          onClick={() => setShowWriteInput(false)}
        >
          Back
        </button>
        <h2 className={styles.skipHeading}>Write your story</h2>
        <p className={styles.skipSub}>
          Write anything about yourself — your interests, your confusion, what
          your parents expect, what you actually want. The more honest, the more
          accurate Darpan will be.
        </p>
        <textarea
          className={styles.skipTextarea}
          placeholder="I am in Class 9 and I honestly have no idea what I want to do. Math feels pointless but I love drawing..."
          value={writeText}
          onChange={(e) => setWriteText(e.target.value)}
          rows={8}
          autoFocus
        />
        <div className={styles.skipActions}>
          <span className={styles.charCount}>
            {writeText.length} characters
          </span>
          <button
            className={styles.skipSubmit}
            disabled={writeText.trim().length < 100}
            onClick={() => onChoose("paste", writeText.trim())}
          >
            Reveal my Darpan
          </button>
        </div>
        {writeText.trim().length > 0 && writeText.trim().length < 100 && (
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
        <div className={styles.greeting}>
          {student.has_identity
            ? `Welcome back, ${student.name}.`
            : `Hey ${student.name}.`}
        </div>
        <p className={styles.sub}>
          {student.has_identity
            ? "You have been here before. What do you want to do today?"
            : "How do you want to start your first session?"}
        </p>
      </div>

      <div className={styles.grid}>
        {cards.map((card) => (
          <button
            key={card.id}
            className={`${styles.card} ${card.accent ? styles.cardAccent : ""} ${card.disabled ? styles.cardDisabled : ""}`}
            onClick={() => {
              if (card.disabled) return;
              if (card.id === "write") {
                setShowWriteInput(true);
              } else {
                onChoose(card.id);
              }
            }}
            disabled={card.disabled}
          >
            <div
              className={`${styles.cardIcon} ${card.accent ? styles.cardIconAccent : ""} ${card.id === "margdarshak" && student.has_identity ? styles.cardIconCompass : ""}`}
            >
              {card.icon}
            </div>
            <div className={styles.cardText}>
              <span className={styles.cardLabel}>{card.label}</span>
              <span className={styles.cardSub}>{card.sub}</span>
            </div>
            {!card.disabled && <ArrowIcon />}
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

function ChatIcon() {
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
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
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
function CompassIcon() {
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
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
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
