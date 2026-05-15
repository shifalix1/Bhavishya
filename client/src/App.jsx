import { useState } from "react";
import Onboard from "./pages/Onboard";
import Dashboard from "./pages/Dashboard";

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

  return student ? (
    <Dashboard student={student} onLogout={() => setStudent(null)} />
  ) : (
    <Onboard onDone={setStudent} />
  );
}
