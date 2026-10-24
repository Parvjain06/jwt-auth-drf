import { useEffect, useRef, useState } from "react";
import { api } from "./lib/api.js";
import { AUTO_REFRESH_SECONDS, DEMO_USER } from "./lib/demo.js";
import { formatDuration, secondsLeft } from "./lib/jwt.js";
import { useNow } from "./lib/useNow.js";
import LoginCard from "./components/LoginCard.jsx";
import TokenInspector from "./components/TokenInspector.jsx";
import DogGallery from "./components/DogGallery.jsx";
import AttackLab from "./components/AttackLab.jsx";
import StorageDemo from "./components/StorageDemo.jsx";
import LogoutComparison from "./components/LogoutComparison.jsx";
import ResearchAnswers from "./components/ResearchAnswers.jsx";
import RequestLog from "./components/RequestLog.jsx";
import Step from "./components/Step.jsx";

export default function App() {
  const now = useNow();
  const [creds, setCreds] = useState(DEMO_USER);
  // Tokens live only in this component's memory, never in localStorage:
  // a malicious script could read localStorage, and a page reload simply logs you out.
  const [tokens, setTokens] = useState(null); // { access, refresh }
  const [user, setUser] = useState(null);
  const [previousRefresh, setPreviousRefresh] = useState(null); // rotated-out refresh token
  const [loggedOut, setLoggedOut] = useState(null); // tokens kept after logout, for the demo
  const [notice, setNotice] = useState(null); // { tone: "good" | "bad" | "warn", text }
  const [busy, setBusy] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [autoCount, setAutoCount] = useState(0);
  const refreshing = useRef(false);
  const lastAutoRefresh = useRef(0);

  async function login() {
    setBusy(true);
    const res = await api("/api/auth/login/", { method: "POST", body: creds, label: "Log in" });
    setBusy(false);
    if (res.status === 200) {
      setTokens({ access: res.data.access, refresh: res.data.refresh });
      setPreviousRefresh(null);
      setLoggedOut(null);
      setAutoCount(0);
      const me = await api("/api/auth/me/", { token: res.data.access, label: "Who am I?" });
      setUser(me.ok ? me.data : null);
      setNotice({ tone: "good", text: "Logged in. The server returned an access token and a refresh token." });
    } else if (res.status === 429) {
      setNotice({
        tone: "warn",
        text: `Too many login attempts (429). Try again in ${res.retryAfter || "a few"} seconds.`,
      });
    } else if (res.status === 401) {
      setNotice({ tone: "bad", text: `Login refused (401): ${res.data?.detail}` });
    } else {
      setNotice({ tone: "bad", text: res.data?.detail || `Login failed (${res.status}).` });
    }
  }

  async function refresh({ automatic = false } = {}) {
    if (refreshing.current || !tokens) return;
    refreshing.current = true;
    setBusy(true);
    const res = await api("/api/auth/refresh/", {
      method: "POST",
      body: { refresh: tokens.refresh },
      label: automatic ? "Auto-refresh before expiry" : "Refresh tokens",
    });
    setBusy(false);
    refreshing.current = false;
    if (res.status === 200) {
      setPreviousRefresh(tokens.refresh);
      setTokens({ access: res.data.access, refresh: res.data.refresh });
      if (automatic) setAutoCount((n) => n + 1);
      setNotice({
        tone: "good",
        text: automatic
          ? "Auto-refreshed just before expiry. You were never interrupted; the old refresh token is now blacklisted."
          : "Refreshed. You have a new access token and a new refresh token; the old refresh token is now blacklisted.",
      });
    } else {
      setAutoRefresh(false);
      setNotice({ tone: "bad", text: `Refresh refused (${res.status}): ${res.data?.detail}. Log in again.` });
    }
  }

  async function logout() {
    setBusy(true);
    const res = await api("/api/auth/logout/", {
      method: "POST",
      token: tokens.access,
      body: { refresh: tokens.refresh },
      label: "Log out",
    });
    setBusy(false);
    if (res.status === 200) {
      setLoggedOut({ ...tokens });
      setTokens(null);
      setUser(null);
      setAutoRefresh(false);
      setNotice({
        tone: "good",
        text: "Logged out. The refresh token is blacklisted. Step 6 shows what the old tokens can still do.",
      });
    } else if (res.status === 401) {
      setNotice({
        tone: "bad",
        text: "Logout needs a valid access token and yours has expired. Refresh tokens first, then log out.",
      });
    } else {
      setNotice({ tone: "bad", text: res.data?.detail || `Logout failed (${res.status}).` });
    }
  }

  const left = tokens ? secondsLeft(tokens.access, now) : null;

  // Silent refresh: what real apps do so users never see the 5-minute limit.
  useEffect(() => {
    // At most once a minute, so a wrong computer clock cannot cause a refresh loop.
    if (autoRefresh && tokens && left !== null && left <= AUTO_REFRESH_SECONDS && now - lastAutoRefresh.current > 60000) {
      lastAutoRefresh.current = now;
      refresh({ automatic: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, tokens, left]);

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">
              <i className="seg seg-h" />
              <i className="seg seg-p" />
              <i className="seg seg-s" />
            </span>
            <div>
              <h1>JWT Lab</h1>
              <p className="tagline">
                Login, tokens and attacks on a Django REST Framework API that guards The Dog API.
              </p>
            </div>
          </div>
          <div className="masthead-side">
            <p className={`session-chip ${tokens ? (left > 0 ? "on" : "stale") : "off"}`} role="status">
              {tokens
                ? left > 0
                  ? `${user?.username ?? "You"} signed in. Access token expires in ${formatDuration(left)}.`
                  : "Access token expired. Refresh it in step 1."
                : "Not signed in"}
            </p>
            <a className="masthead-link" href="#research">
              Research questions answered
            </a>
          </div>
        </div>
      </header>

      <div className="layout">
        <main className="steps">
          <Step n={1} title="Log in" lead="Send a username and password once; get back two signed tokens.">
            <LoginCard
              creds={creds}
              setCreds={setCreds}
              user={user}
              tokens={tokens}
              busy={busy}
              notice={notice}
              onLogin={login}
              onRefresh={() => refresh()}
              onLogout={logout}
              autoRefresh={autoRefresh}
              setAutoRefresh={setAutoRefresh}
              autoCount={autoCount}
            />
          </Step>

          <Step
            n={2}
            title="Look inside the token"
            lead="A JWT is three parts. Anyone can read the first two; only the server can make the third."
          >
            <TokenInspector tokens={tokens} now={now} />
          </Step>

          <Step
            n={3}
            title="Fetch protected data"
            lead="The dog breeds below come through our API, which only answers requests that carry a valid access token."
          >
            <DogGallery access={tokens?.access} />
          </Step>

          <Step
            n={4}
            title="Attack the API"
            lead="Each attack changes your real token the way an attacker could, then calls a protected endpoint."
          >
            <AttackLab tokens={tokens} previousRefresh={previousRefresh} />
          </Step>

          <Step
            n={5}
            title="Where should the browser keep the token?"
            lead="If an attacker gets a script into the page (XSS), what can it steal from each storage place?"
          >
            <StorageDemo tokens={tokens} creds={creds} />
          </Step>

          <Step
            n={6}
            title="Log out: JWT compared with sessions"
            lead="What can a copied credential still do after the user logs out?"
          >
            <LogoutComparison loggedOut={loggedOut} creds={creds} now={now} />
          </Step>

          <ResearchAnswers />
        </main>

        <aside className="log-column">
          <RequestLog />
        </aside>
      </div>

    </div>
  );
}
