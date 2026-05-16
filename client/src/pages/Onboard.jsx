import { useState, useEffect } from "react";
import { api } from "../lib/api";
import { applyTheme, getStoredTheme } from "../lib/theme";
import Loader from "../components/Loader";
import ThemeToggle from "../components/ThemeToggle";
import styles from "./Onboard.module.css";
import { getCached, setCache, clearCache } from "../lib/cache";

const GRADES = [9, 10, 11, 12];
//const CACHE_KEY = "bhavishya_auth";

export default function Onboard({ onDone }) {
  const [cached, setCached] = useState(() => getCached());
  const [pin, setPin] = useState("");
  const [name, setName] = useState("");
  const [grade, setGrade] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [username, setUsername] = useState(() => getCached()?.username || "");
  const [tab, setTab] = useState("login");

  useEffect(() => {
    applyTheme(getStoredTheme());
  }, []);

  const handleLogin = async () => {
    const u = username.trim().toLowerCase();
    const p = pin.trim();
    if (!u || p.length !== 4) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.login(u, p);
      setCache(res);
      onDone(res);
    } catch (e) {
      setError(e.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    const u = username.trim().toLowerCase();
    const p = pin.trim();
    const n = name.trim();
    if (!u || p.length !== 4 || !n || !grade) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.register(u, p, n, grade);
      setCache(res);
      onDone(res);
    } catch (e) {
      setError(e.message || "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key !== "Enter") return;
    tab === "login" ? handleLogin() : handleRegister();
  };

  const switchTab = (t) => {
    setTab(t);
    setError("");
    setPin("");
  };

  const loginReady =
    username.trim().length >= 3 && pin.length === 4 && !loading;
  const regReady =
    username.trim().length >= 3 &&
    pin.length === 4 &&
    name.trim().length > 0 &&
    !!grade &&
    !loading;

  return (
    <div className={styles.wrap}>
      <header className={styles.topbar}>
        <span className={styles.brandName}>Bhavishya</span>
        <div className={styles.topRight}>
          <span className="caption">Gemma 4 Good Hackathon</span>
          <ThemeToggle />
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.hero}>
          <div className={styles.heroTag}>
            AI Career Companion for Indian Students
          </div>
          <h1 className={styles.headline}>
            At 14, you should not have to figure out your future alone.
          </h1>
          <p className={styles.subhead}>
            Bhavishya listens to who you are, tracks how you grow, and shows you
            three honest futures ~ specific to you, grounded in real data. Free.
            Bilingual. Always there.
          </p>
          <div className={styles.crossDevice}>
            <DevicesIcon />
            <span>One username and PIN. Works on any device.</span>
          </div>
        </div>

        <div className={styles.card}>
          <div className={styles.tabs}>
            <button
              className={`${styles.tab} ${tab === "login" ? styles.tabActive : ""}`}
              onClick={() => switchTab("login")}
            >
              Log in
            </button>
            <button
              className={`${styles.tab} ${tab === "register" ? styles.tabActive : ""}`}
              onClick={() => switchTab("register")}
            >
              Create account
            </button>
          </div>

          <div className={styles.fields}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="username">
                Username
              </label>
              <input
                id="username"
                className={styles.input}
                placeholder="aryan9, priya_singh..."
                value={username}
                onChange={(e) =>
                  setUsername(
                    e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""),
                  )
                }
                onKeyDown={handleKey}
                autoFocus
                autoCapitalize="none"
                autoCorrect="off"
              />
              {tab === "register" && (
                <span className={styles.hint}>
                  3-20 chars. Letters, numbers, underscore only.
                </span>
              )}
            </div>

            {tab === "register" && (
              <>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="displayname">
                    Your name
                  </label>
                  <input
                    id="displayname"
                    className={styles.input}
                    placeholder="Aryan, Priya, Riya..."
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onKeyDown={handleKey}
                  />
                </div>

                <div className={styles.field}>
                  <div className={styles.label}>Your class</div>
                  <div className={styles.gradeRow}>
                    {GRADES.map((g) => (
                      <button
                        key={g}
                        className={`${styles.gradeBtn} ${grade === g ? styles.gradeBtnActive : ""}`}
                        onClick={() => setGrade(g)}
                        type="button"
                      >
                        Class {g}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            <div className={styles.field}>
              <label className={styles.label} htmlFor="pin">
                4-digit PIN
              </label>
              <input
                id="pin"
                className={`${styles.input} ${styles.pinInput}`}
                placeholder="----"
                value={pin}
                onChange={(e) =>
                  setPin(e.target.value.replace(/\D/g, "").slice(0, 4))
                }
                onKeyDown={handleKey}
                inputMode="numeric"
                type="password"
                maxLength={4}
              />
              {tab === "register" && (
                <span className={styles.hint}>
                  Remember this. It is the only way to log in on other devices.
                </span>
              )}
            </div>

            {error && <div className={styles.error}>{error}</div>}

            <button
              className={`${styles.submit} ${(tab === "login" ? loginReady : regReady) ? styles.submitReady : ""}`}
              onClick={tab === "login" ? handleLogin : handleRegister}
              disabled={tab === "login" ? !loginReady : !regReady}
            >
              {loading ? (
                <Loader
                  label={
                    tab === "login" ? "Logging in..." : "Creating account..."
                  }
                />
              ) : tab === "login" ? (
                "Log in"
              ) : (
                "Create account"
              )}
            </button>

            {cached && tab === "login" && (
              <button
                className={styles.clearBtn}
                onClick={() => {
                  clearCache();
                  setCached(null);
                  setUsername("");
                }}
              >
                Not {cached.name}? Clear saved account
              </button>
            )}
          </div>

          <div className={styles.cardFooter}>
            No email. No tracking. Data linked only to your username.
          </div>
        </div>
      </main>

      <div className={styles.statsRow}>
        {[
          ["15M", "Students face stream selection annually"],
          ["Less than 10%", "Have access to career guidance"],
          ["60%", "Regret their stream choice"],
        ].map(([n, l]) => (
          <div key={n} className={styles.stat}>
            <div className={styles.statNum}>{n}</div>
            <div className={styles.statLabel}>{l}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DevicesIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  );
}
