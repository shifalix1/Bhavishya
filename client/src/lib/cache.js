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

export function setCache(data) {
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
}

export function clearCache() {
  localStorage.removeItem(CACHE_KEY);
  localStorage.removeItem("bhavishya_uid");
  localStorage.removeItem("bhavishya_student");
}
