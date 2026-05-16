const CACHE_KEY = "bhavishya_auth";

export function getCached() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const d = JSON.parse(raw);
    return d.username && d.uid ? d : null;
  } catch (e) {
    console.error("Error reading cache:", e);
    return null;
  }
}

// Returns true on success, false if localStorage is blocked (incognito, quota, CSP)
export function setCache(data) {
  try {
    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({
        username: data.username,
        uid: data.uid,
        name: data.name,
        grade: data.grade,
        session_count: data.session_count ?? 0,
        has_identity: data.has_identity ?? false,
        language_preference: data.language_preference ?? "hinglish",
      }),
    );
    return true;
  } catch (e) {
    // Incognito or storage quota exceeded — login still works, just no persistence
    console.warn("[CACHE] Could not write to localStorage:", e);
    return false;
  }
}

// Quick check: is localStorage writable right now?
export function isCacheAvailable() {
  try {
    localStorage.setItem("__bhavishya_test__", "1");
    localStorage.removeItem("__bhavishya_test__");
    return true;
  } catch {
    return false;
  }
}

export function clearCache() {
  localStorage.removeItem(CACHE_KEY);
  localStorage.removeItem("bhavishya_uid");
  localStorage.removeItem("bhavishya_student");
}
