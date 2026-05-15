export default function Loader({ label = "Processing" }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        color: "var(--text-muted)",
        fontSize: "0.875rem",
      }}
    >
      <span className="dots">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </span>
      {label}
    </span>
  );
}
