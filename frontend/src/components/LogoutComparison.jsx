import { useState } from "react";
import { api } from "../lib/api.js";
import { formatDuration, secondsLeft } from "../lib/jwt.js";
import StatusBadge from "./StatusBadge.jsx";

function StepRow({ label, expected, expectedText, result, onRun, disabled, children }) {
  return (
    <li className="cmp-step">
      <div className="cmp-step-main">
        <button className="btn btn-small" onClick={onRun} disabled={disabled}>
          {label}
        </button>
        <span className="muted small">Expect {expectedText}</span>
      </div>
      <div className="cmp-step-result">
        {result !== undefined && <StatusBadge status={result} expected={expected} />}
      </div>
      {children}
    </li>
  );
}

function JwtSide({ loggedOut, now }) {
  const [r, setR] = useState({});
  const left = loggedOut ? secondsLeft(loggedOut.access, now) : null;

  return (
    <div className="cmp-side">
      <h3>JWT</h3>
      <p className="cmp-where">
        Stored by the client (here, in page memory). The server keeps no record of access tokens.
      </p>
      {!loggedOut ? (
        <p className="empty-inline">Log in and then log out in step 1. The tokens you had are kept here so you can try them.</p>
      ) : (
        <>
          <ol className="cmp-steps">
            <StepRow
              label="Use the old refresh token"
              expected={401}
              expectedText="401: it was blacklisted at logout"
              result={r.refresh}
              onRun={async () => {
                const res = await api("/api/auth/refresh/", {
                  method: "POST",
                  body: { refresh: loggedOut.refresh },
                  label: "After logout: refresh token",
                });
                setR((x) => ({ ...x, refresh: res.status }));
              }}
            />
            <StepRow
              label="Use the old access token"
              expected={left > 0 ? 200 : 401}
              expectedText={left > 0 ? "200: still valid until it expires" : "401: it has now expired"}
              result={r.access}
              onRun={async () => {
                const res = await api("/api/dogs/breeds/?limit=1", {
                  token: loggedOut.access,
                  label: "After logout: access token",
                });
                setR((x) => ({ ...x, access: res.status }));
              }}
            />
          </ol>
          <p className={`cmp-verdict ${left > 0 ? "warn" : "ok"}`}>
            {left > 0
              ? `The logged-out access token still works for ${formatDuration(left)}. JWTs cannot be recalled before they expire.`
              : "The old access token has expired, so it is finally rejected."}
          </p>
        </>
      )}
    </div>
  );
}

function SessionSide({ creds }) {
  const [r, setR] = useState({});
  const [csrf, setCsrf] = useState(null);
  const [cookies, setCookies] = useState(null);

  const run = (key, fn) => async () => {
    const status = await fn();
    setR((x) => ({ ...x, [key]: status }));
  };

  return (
    <div className="cmp-side">
      <h3>Session</h3>
      <p className="cmp-where">
        Stored on the server, in Django's session table. The browser only holds a random ID in an HttpOnly cookie.
      </p>
      <ol className="cmp-steps">
        <StepRow
          label="Log in with a session"
          expected={200}
          expectedText="200"
          result={r.login}
          onRun={run("login", async () => {
            const res = await api("/api/session/login/", { method: "POST", body: creds, label: "Session login" });
            if (res.ok) setCsrf(res.data.csrftoken);
            return res.status;
          })}
        />
        <StepRow
          label="Can JavaScript read the cookie?"
          expectedText="no sessionid visible (HttpOnly)"
          onRun={() => setCookies(document.cookie || "(empty)")}
        >
          {cookies !== null && (
            <p className="cookie-readout">
              <code>document.cookie</code> shows: <code>{cookies}</code>.{" "}
              {cookies.includes("sessionid")
                ? "The session ID is visible."
                : "No sessionid: a malicious script cannot steal it."}
            </p>
          )}
        </StepRow>
        <StepRow
          label="Call a session-protected endpoint"
          expected={200}
          expectedText="200"
          result={r.me}
          onRun={run("me", async () => (await api("/api/session/me/", { label: "Session: who am I?" })).status)}
        />
        <StepRow
          label="Log out without the CSRF token"
          expected={403}
          expectedText="403: cookies need CSRF protection"
          result={r.noCsrf}
          onRun={run("noCsrf", async () =>
            (await api("/api/session/logout/", { method: "POST", label: "Session logout, no CSRF token" })).status,
          )}
        />
        <StepRow
          label="Log out with the CSRF token"
          expected={200}
          expectedText="200: session deleted on the server"
          result={r.logout}
          disabled={!csrf}
          onRun={run("logout", async () =>
            (
              await api("/api/session/logout/", {
                method: "POST",
                headers: { "X-CSRFToken": csrf },
                label: "Session logout with CSRF token",
              })
            ).status,
          )}
        />
        <StepRow
          label="Call the endpoint again"
          expected={403}
          expectedText="403: the session no longer exists"
          result={r.after}
          onRun={run("after", async () => (await api("/api/session/me/", { label: "After session logout" })).status)}
        />
      </ol>
      {r.after !== undefined && (
        <p className={`cmp-verdict ${r.after === 403 ? "ok" : "warn"}`}>
          {r.after === 403
            ? "Session logout takes effect immediately: the server simply forgets the session."
            : "The session still answered. Log in with a session and log out with the CSRF token first."}
        </p>
      )}
    </div>
  );
}

export default function LogoutComparison({ loggedOut, creds, now }) {
  return (
    <div className="panel">
      <div className="cmp">
        <JwtSide loggedOut={loggedOut} now={now} />
        <SessionSide creds={creds} />
      </div>
    </div>
  );
}
