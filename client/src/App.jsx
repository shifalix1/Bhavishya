import { useState } from "react";
import Onboard from "./pages/Onboard";
import Dashboard from "./pages/Dashboard";
import ErrorBoundary from "./ErrorBoundary";
import { isCacheAvailable } from "./lib/cache";

const CACHE_KEY = "bhavishya_auth";

function getCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const d = JSON.parse(raw);
    return d.username && d.uid ? d : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [student, setStudent] = useState(() => getCache());
  // Warn once if storage is unavailable (incognito / CSP) — session still works
  const [storageWarning] = useState(() => !isCacheAvailable());

  return student ? (
    <ErrorBoundary>
      {storageWarning && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            zIndex: 9999,
            background: "rgba(180,120,10,0.95)",
            color: "#fff",
            fontSize: "0.8rem",
            textAlign: "center",
            padding: "8px 16px",
            fontFamily: "inherit",
          }}
        >
          Private/Incognito mode detected — your session won&apos;t be saved
          when you close this tab.
        </div>
      )}
      <Dashboard student={student} onLogout={() => setStudent(null)} />
    </ErrorBoundary>
  ) : (
    <ErrorBoundary>
      {storageWarning && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            zIndex: 9999,
            background: "rgba(180,120,10,0.95)",
            color: "#fff",
            fontSize: "0.8rem",
            textAlign: "center",
            padding: "8px 16px",
            fontFamily: "inherit",
          }}
        >
          Private/Incognito mode — you can still use Bhavishya, but your session
          won&apos;t be remembered.
        </div>
      )}
      <Onboard onDone={setStudent} />
    </ErrorBoundary>
  );
}
