// Theme utility — call applyTheme on app init, toggleTheme on button press

export function getStoredTheme() {
  try {
    return localStorage.getItem("bhavishya_theme") || "light";
  } catch {
    return "light";
  }
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem("bhavishya_theme", theme);
  } catch {
    // ignore
  }
}

export function toggleTheme() {
  const current =
    document.documentElement.getAttribute("data-theme") || "light";
  const next = current === "light" ? "dark" : "light";
  applyTheme(next);
  return next;
}
