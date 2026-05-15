import styles from "./IdentityPanel.module.css";

function TagList({ items = [], variant = "neutral" }) {
  return (
    <div className={styles.tagList}>
      {items.map((item, i) => (
        <span key={i} className={`badge badge-${variant}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function ConfidenceBar({ value = 5 }) {
  const pct = (value / 10) * 100;
  const color =
    value >= 7 ? "var(--success)" : value >= 4 ? "var(--gold)" : "var(--error)";
  return (
    <div className={styles.confBar}>
      <div
        className={styles.confFill}
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  );
}

export default function IdentityPanel({ identity }) {
  if (!identity || Object.keys(identity).length === 0) return null;

  return (
    <div className={`card ${styles.panel}`}>
      <div className={styles.header}>
        <div>
          <div className="caption">Your Identity Fingerprint</div>
          <div className={`card-heading ${styles.thinking}`}>
            {identity.thinking_style}
          </div>
        </div>
        <div className={styles.confidence}>
          <div className="caption">Identity Confidence</div>
          <div className={styles.confScore}>
            {identity.identity_confidence}
            <span>/10</span>
          </div>
          <ConfidenceBar value={identity.identity_confidence} />
        </div>
      </div>

      <div className={styles.divider} />

      <div className={styles.grid}>
        <div className={styles.cell}>
          <div className="caption" style={{ marginBottom: 8 }}>
            Core Values
          </div>
          <TagList items={identity.core_values} variant="neutral" />
        </div>

        <div className={styles.cell}>
          <div className="caption" style={{ marginBottom: 8 }}>
            Hidden Strengths
          </div>
          <TagList items={identity.hidden_strengths} variant="accent" />
        </div>

        <div className={styles.cell}>
          <div className="caption" style={{ marginBottom: 8 }}>
            Active Fears
          </div>
          <TagList items={identity.active_fears} variant="error" />
        </div>

        <div className={styles.cell}>
          <div className="caption" style={{ marginBottom: 8 }}>
            Energy Signature
          </div>
          <p className="body-sm" style={{ color: "var(--text-sub)" }}>
            {identity.energy_signature}
          </p>
        </div>
      </div>

      {identity.family_pressure_map && (
        <>
          <div className={styles.divider} />
          <div className={styles.pressureBlock}>
            <div className="caption" style={{ marginBottom: 6 }}>
              Family Pressure Map
            </div>
            <p className="body-sm" style={{ color: "var(--text-sub)" }}>
              {identity.family_pressure_map}
            </p>
          </div>
        </>
      )}

      {identity.changed_since_last && identity.change_summary && (
        <div className={styles.changeAlert}>
          <span className="badge badge-success" style={{ marginBottom: 6 }}>
            Changed since last session
          </span>
          <p className="body-sm" style={{ color: "var(--text-sub)" }}>
            {identity.change_summary}
          </p>
        </div>
      )}
    </div>
  );
}
