import { useState } from "react";
import styles from "./FutureCard.module.css";

const TYPE_META = {
  expected: {
    label: "Expected Path",
    accent: "var(--text-muted)",
    bg: "var(--surface-alt)",
    border: "var(--border)",
  },
  inner_call: {
    label: "Inner Call",
    accent: "var(--gold)",
    bg: "rgba(201, 162, 39, 0.05)",
    border: "rgba(201, 162, 39, 0.25)",
  },
  unseen_door: {
    label: "Unseen Door",
    accent: "var(--accent)",
    bg: "rgba(245, 78, 0, 0.05)",
    border: "rgba(245, 78, 0, 0.22)",
  },
};

function yearsFromNow(grade) {
  return { 9: 9, 10: 8, 11: 7, 12: 6 }[grade] || 7;
}

export default function FutureCard({
  future,
  index,
  student,
  onAskMargdarshak,
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = TYPE_META[future.type] || {
    label: future.type,
    accent: "var(--text-muted)",
    bg: "var(--surface-alt)",
    border: "var(--border)",
  };

  const yearsAhead = yearsFromNow(student?.grade);

  // Support both old (annual_salary_2031_inr) and new (annual_salary_inr) field names
  const salaryRaw = future.annual_salary_inr || future.annual_salary_2031_inr;
  const salary = salaryRaw ? `${(salaryRaw / 100000).toFixed(1)}L / yr` : null;

  const riskColor =
    {
      low: "var(--success)",
      medium: "var(--warning)",
      high: "var(--error)",
    }[future.ai_disruption_risk] || "var(--text-muted)";

  // Support both old (narrative_2031) and new (narrative) field names
  const narrative = future.narrative || future.narrative_2031;

  const isUnseenDoor = future.type === "unseen_door";

  return (
    <div
      className={styles.card}
      style={{
        "--card-accent": meta.accent,
        "--card-bg": meta.bg,
        "--card-border": meta.border,
        animationDelay: `${index * 0.1}s`,
      }}
    >
      {/* Header strip */}
      <div className={styles.strip}>
        <div className={styles.stripLeft}>
          <span className={styles.typeLabel}>{meta.label}</span>
          <span className={styles.year}>~{yearsAhead} years from now</span>
        </div>
        <div className={styles.stripRight}>
          {salary && <span className={styles.salaryBig}>{salary}</span>}
          <span className={styles.riskBadge} style={{ color: riskColor }}>
            AI risk: {future.ai_disruption_risk?.toUpperCase() || "?"}
          </span>
        </div>
      </div>

      {/* Title + trajectory */}
      <div className={styles.titleBlock}>
        <h3 className={styles.title}>{future.title}</h3>
        <p className={styles.trajectory}>{future.career_trajectory}</p>
      </div>

      {/* Narrative */}
      {narrative && <p className={styles.narrative}>{narrative}</p>}

      {/* Stats row */}
      <div className={styles.statsGrid}>
        <div className={styles.statCell}>
          <div className={styles.statLabel}>What you gain</div>
          <div className={styles.statValue} style={{ color: "var(--success)" }}>
            {future.what_you_gain}
          </div>
        </div>
        <div className={styles.statCell}>
          <div className={styles.statLabel}>What you sacrifice</div>
          <div className={styles.statValue} style={{ color: "var(--error)" }}>
            {future.what_you_sacrifice}
          </div>
        </div>
      </div>

      {/* Salary context */}
      {future.salary_context && (
        <div className={styles.salaryNote}>{future.salary_context}</div>
      )}

      {/* Decision point */}
      {future.key_decision_point && (
        <div className={styles.decision}>
          <span className={styles.decisionLabel}>The turning point</span>
          <p className={styles.decisionText}>{future.key_decision_point}</p>
        </div>
      )}

      {/* How to start — unseen door only */}
      {isUnseenDoor && future.how_to_start && (
        <div className={styles.howToStart}>
          <button
            className={styles.howToStartToggle}
            onClick={() => setExpanded((e) => !e)}
          >
            <span className={styles.howToStartLabel}>
              {expanded ? "Hide steps" : "How do I get here?"}
            </span>
            <span className={styles.howToStartChevron}>
              {expanded ? "↑" : "↓"}
            </span>
          </button>
          {expanded && (
            <div className={styles.howToStartBody}>
              {future.how_to_start
                .split(/\d+\.\s/)
                .filter(Boolean)
                .map((step, i) => (
                  <div key={i} className={styles.howToStartStep}>
                    <span className={styles.stepNum}>{i + 1}</span>
                    <span className={styles.stepText}>{step.trim()}</span>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Ask Margdarshak bridge — unseen door only */}
      {isUnseenDoor && onAskMargdarshak && (
        <div className={styles.margBridge}>
          <button
            className={styles.margBridgeBtn}
            onClick={() =>
              onAskMargdarshak(
                `The simulator showed me an unseen door: "${future.title}" (${future.career_trajectory}). How do I actually get there from where I am now?`,
              )
            }
          >
            <CompassIcon />
            Ask Margdarshak how to get here
          </button>
        </div>
      )}
    </div>
  );
}

function CompassIcon() {
  return (
    <svg
      width="13"
      height="13"
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
