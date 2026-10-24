import { AUTO_REFRESH_SECONDS, DEMO_USER } from "../lib/demo.js";

export default function LoginCard({
  creds,
  setCreds,
  user,
  tokens,
  busy,
  notice,
  onLogin,
  onRefresh,
  onLogout,
  autoRefresh,
  setAutoRefresh,
  autoCount,
}) {
  const signedIn = Boolean(tokens);

  return (
    <div className="panel">
      {!signedIn ? (
        <form
          className="login-form"
          onSubmit={(e) => {
            e.preventDefault();
            onLogin();
          }}
        >
          <label>
            Username
            <input
              value={creds.username}
              autoComplete="username"
              onChange={(e) => setCreds({ ...creds, username: e.target.value })}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={creds.password}
              autoComplete="current-password"
              onChange={(e) => setCreds({ ...creds, password: e.target.value })}
            />
          </label>
          <div className="row">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Logging in…" : "Log in"}
            </button>
            <button
              className="btn btn-quiet"
              type="button"
              onClick={() => setCreds({ ...creds, password: "wrong-password" })}
            >
              Use a wrong password
            </button>
            {creds.password !== DEMO_USER.password && (
              <button className="btn btn-quiet" type="button" onClick={() => setCreds(DEMO_USER)}>
                Reset to demo account
              </button>
            )}
          </div>
          <p className="hint">
            Demo account: <code>{DEMO_USER.username}</code> with password <code>{DEMO_USER.password}</code>,
            already filled in. Five attempts per minute are allowed from one network.
          </p>
        </form>
      ) : (
        <div className="signed-in">
          <p>
            Signed in as <strong>{user?.username ?? "…"}</strong>
            {user?.email ? ` (${user.email})` : ""}. Your browser holds the tokens in memory only, so reloading
            the page logs you out.
          </p>
          <div className="row">
            <button className="btn btn-primary" onClick={onRefresh} disabled={busy}>
              Refresh tokens
            </button>
            <button className="btn btn-danger" onClick={onLogout} disabled={busy}>
              Log out
            </button>
          </div>
          <label className="toggle">
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            <span>
              <strong>Auto-refresh.</strong> Get a new access token {AUTO_REFRESH_SECONDS} seconds before the old
              one expires, the way real apps keep you signed in without asking for your password every 5 minutes.
              {autoRefresh && autoCount > 0 && ` Refreshed automatically ${autoCount} time${autoCount > 1 ? "s" : ""}.`}
            </span>
          </label>
        </div>
      )}
      {notice && (
        <p className={`notice notice-${notice.tone}`} role="status">
          {notice.text}
        </p>
      )}
    </div>
  );
}
