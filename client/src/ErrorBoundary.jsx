import { Component } from "react";

/**
 * ErrorBoundary — catches any React render error and shows a recovery UI
 * instead of a blank screen. Wrap Dashboard and Onboard in App.jsx.
 *
 * Usage in App.jsx:
 *   import ErrorBoundary from "./ErrorBoundary";
 *   <ErrorBoundary><Dashboard ... /></ErrorBoundary>
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // In production you'd send this to a logging service
    console.error("[Bhavishya ErrorBoundary]", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ error: null, errorInfo: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            minHeight: "100dvh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 20,
            padding: "40px 24px",
            textAlign: "center",
            background: "var(--bg)",
            color: "var(--text)",
            fontFamily: "var(--sans)",
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              background: "var(--error-dim)",
              border: "1.5px solid var(--error)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 24,
            }}
          >
            ⚠
          </div>
          <div>
            <p
              style={{
                fontFamily: "var(--serif)",
                fontSize: "clamp(1.1rem, 3vw, 1.5rem)",
                color: "var(--text)",
                margin: "0 0 8px",
              }}
            >
              Something went wrong.
            </p>
            <p
              style={{
                fontSize: "0.9rem",
                color: "var(--text-muted)",
                margin: 0,
                maxWidth: 360,
                lineHeight: 1.6,
              }}
            >
              Bhavishya hit an unexpected error. Your session data is safe.
              Refresh the page to continue.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: "10px 22px",
                borderRadius: "var(--r-md, 10px)",
                background: "var(--text)",
                color: "var(--bg)",
                border: "none",
                fontSize: "0.875rem",
                fontWeight: 600,
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Refresh page
            </button>
            <button
              onClick={this.handleReset}
              style={{
                padding: "10px 22px",
                borderRadius: "var(--r-md, 10px)",
                background: "transparent",
                color: "var(--text-muted)",
                border: "1px solid var(--border)",
                fontSize: "0.875rem",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Try again
            </button>
          </div>
          {import.meta.env.DEV && this.state.error && (
            <pre
              style={{
                fontSize: "0.7rem",
                color: "var(--error)",
                background: "var(--error-dim)",
                padding: "12px 16px",
                borderRadius: 8,
                maxWidth: 560,
                overflow: "auto",
                textAlign: "left",
                margin: 0,
              }}
            >
              {this.state.error.toString()}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
