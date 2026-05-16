const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY || "";

const STATUS_MESSAGES = {
  400: "Something wasn't quite right with that request. Try again.",
  401: "Session expired. Please log in again.",
  403: "You don't have access to this.",
  404: "We couldn't find what you were looking for.",
  409: "There's a conflict with existing data.",
  422: "Something in your response wasn't quite right. Try again.",
  429: "Too many requests. Give it a moment, then try again.",
  500: "Our servers are thinking hard. Give it 10 seconds.",
  502: "Service is temporarily unreachable. Give it 10 seconds.",
  503: "Service is temporarily unavailable. Give it 10 seconds.",
};

async function request(method, path, body, retries = 1) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(`${BASE}${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(API_KEY && { "X-API-Key": API_KEY }),
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const status = res.status;
        if (
          status === 401 ||
          status === 404 ||
          status === 400 ||
          status === 409
        ) {
          throw new Error(
            err.detail || STATUS_MESSAGES[status] || `HTTP ${status}`,
          );
        }
        if (attempt === retries)
          throw new Error(
            err.detail || STATUS_MESSAGES[status] || `HTTP ${status}`,
          );
        await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
        continue;
      }
      return res.json();
    } catch (e) {
      if (attempt === retries || e.message?.includes("401")) throw e;
      await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
    }
  }
}

export const api = {
  // Auth
  register: (username, pin, name, grade) =>
    request("POST", "/register", { username, pin, name, grade }),

  login: (username, pin) => request("POST", "/login", { username, pin }),

  // Legacy onboard
  onboard: (name, grade, uid) =>
    request("POST", "/onboard", { name, grade, uid }),

  session: (name, grade, student_input, uid) =>
    request("POST", "/session", { name, grade, student_input, uid }, 2),

  simulate: (name, grade, uid) =>
    request("POST", "/simulate", { name, grade, uid }, 2),

  chat: (name, grade, question, uid) =>
    request("POST", "/chat", { name, grade, question, uid }, 1),

  aawazChat: (name, grade, uid, message, language = "hinglish") =>
    request("POST", "/aawaz/chat", { name, grade, uid, message, language }, 1),

  aawazTranscribe: (
    name,
    grade,
    uid,
    { audio_b64, image_b64, image_mime, text_fallback },
  ) =>
    request(
      "POST",
      "/aawaz/transcribe",
      {
        name,
        grade,
        uid,
        audio_b64: audio_b64 || null,
        image_b64: image_b64 || null,
        image_mime: image_mime || "image/jpeg",
        text_fallback: text_fallback || null,
      },
      1,
    ),

  margdarshakGuidance: (uid, name, grade, language = "english") =>
    request("POST", "/margdarshak/guidance", { uid, name, grade, language }, 1),

  margdarshakQuestion: (
    uid,
    name,
    grade,
    question,
    guidance,
    language = "english",
  ) =>
    request(
      "POST",
      "/margdarshak/question",
      {
        uid,
        name,
        grade,
        question,
        language,
        guidance: guidance || null,
      },
      0,
    ),

  // Session history for sidebar
  getHistory: (uid) => request("GET", `/history/${uid}`, null, 0),

  // Language preference
  setPreference: (uid, language) =>
    request("POST", "/preference", { uid, language }, 0),
};
