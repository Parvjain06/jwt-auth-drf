import { useState } from "react";
import { api } from "../lib/api.js";
import {
  decodeToken,
  resignedWithGuessedKey,
  withAlgNone,
  withCorruptedSignature,
  withPayloadChanges,
} from "../lib/jwt.js";
import StatusBadge from "./StatusBadge.jsx";
import TokenEditor from "./TokenEditor.jsx";

function otherUserId(token) {
  const id = decodeToken(token).payload.user_id;
  return typeof id === "number" ? id + 1 : String(Number(id) + 1);
}

// Each attack builds a token from your real one and sends it to GET /api/auth/me/.
const ATTACKS = [
  {
    id: "genuine",
    name: "Genuine access token",
    change: "Nothing. This is the control.",
    expected: 200,
    build: (t) => t.access,
  },
  { id: "missing", name: "No token", change: "Authorization header left out", expected: 401, build: () => null },
  {
    id: "user",
    name: "Pretend to be another user",
    change: "user_id in the payload changed, signature kept",
    expected: 401,
    build: (t) => withPayloadChanges(t.access, { user_id: otherUserId(t.access) }),
  },
  {
    id: "exp",
    name: "Extend the expiry",
    change: "exp pushed one year into the future",
    expected: 401,
    build: (t) => withPayloadChanges(t.access, { exp: decodeToken(t.access).payload.exp + 365 * 24 * 3600 }),
  },
  {
    id: "sig",
    name: "Corrupt the signature",
    change: "One character of the signature changed",
    expected: 401,
    build: (t) => withCorruptedSignature(t.access),
  },
  {
    id: "none",
    name: "The alg: none trick",
    change: "Header says no signature is needed; signature removed",
    expected: 401,
    build: (t) => withAlgNone(t.access),
  },
  {
    id: "forged",
    name: "Forge with a guessed key",
    change: "Same claims, re-signed with a wrong secret",
    expected: 401,
    build: (t) => resignedWithGuessedKey(t.access),
  },
  {
    id: "refresh",
    name: "Refresh token as access token",
    change: "Genuine signature, but token_type is refresh",
    expected: 401,
    build: (t) => t.refresh,
  },
  {
    id: "expired",
    name: "Expired token",
    change: "Genuine token that expired a minute ago",
    expected: 401,
    build: async (t) => {
      const res = await api("/api/auth/demo/expired-token/", { token: t.access, label: "Get an expired token" });
      if (!res.ok) throw new Error("Could not get an expired token. Is your access token still valid?");
      return res.data.expired_access;
    },
  },
];

export default function AttackLab({ tokens, previousRefresh }) {
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(false);
  const [replay, setReplay] = useState(null);
  const [brute, setBrute] = useState([]);
  const [bruting, setBruting] = useState(false);

  async function run(attack) {
    try {
      const token = await attack.build(tokens);
      const res = await api("/api/auth/me/", { token, label: `Attack: ${attack.name}` });
      setResults((r) => ({ ...r, [attack.id]: { status: res.status } }));
    } catch (e) {
      setResults((r) => ({ ...r, [attack.id]: { status: 0, error: e.message } }));
    }
  }

  async function runAll() {
    setRunning(true);
    setResults({});
    for (const a of ATTACKS) {
      // Sequential, so the request log reads in order.
      await run(a);
    }
    setRunning(false);
  }

  async function replayRotated() {
    const res = await api("/api/auth/refresh/", {
      method: "POST",
      body: { refresh: previousRefresh },
      label: "Attack: replay a rotated-out refresh token",
    });
    setReplay(res.status);
  }

  async function bruteForce() {
    setBruting(true);
    setBrute([]);
    for (let i = 1; i <= 6; i++) {
      const res = await api("/api/auth/login/", {
        method: "POST",
        body: { username: "demo", password: `guess-${i}` },
        label: `Brute-force guess ${i}`,
      });
      setBrute((b) => [...b, res.status]);
    }
    setBruting(false);
  }

  const done = Object.keys(results).length;
  const passed = ATTACKS.filter((a) => results[a.id]?.status === a.expected).length;

  return (
    <div className="panel">
      {!tokens ? (
        <p className="empty-inline">Log in first: every attack starts from your real access token.</p>
      ) : (
        <>
          <div className="row between">
            <button className="btn btn-primary" onClick={runAll} disabled={running}>
              {running ? "Running attacks…" : "Run all attacks"}
            </button>
            {done > 0 && (
              <span className={`score ${passed === ATTACKS.length ? "score-good" : ""}`}>
                {passed} of {ATTACKS.length} behaved as expected
              </span>
            )}
          </div>

          <div className="table-wrap">
            <table className="attacks">
              <thead>
                <tr>
                  <th scope="col">Attack</th>
                  <th scope="col">What was changed</th>
                  <th scope="col">Expected</th>
                  <th scope="col">Server said</th>
                  <th scope="col">
                    <span className="sr-only">Run</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {ATTACKS.map((a) => (
                  <tr key={a.id} className={a.id === "genuine" ? "control" : ""}>
                    <th scope="row">{a.name}</th>
                    <td>{a.change}</td>
                    <td className="nowrap">{a.expected === 200 ? "Allowed" : "Rejected"}</td>
                    <td className="nowrap">
                      <StatusBadge status={results[a.id]?.status} expected={a.expected} />
                      {results[a.id]?.error && <div className="cell-error">{results[a.id].error}</div>}
                    </td>
                    <td>
                      <button className="btn btn-small" onClick={() => run(a)} disabled={running}>
                        Run
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <TokenEditor key={tokens.access} access={tokens.access} />
        </>
      )}

      <div className="subpanels">
        <div className="subpanel">
          <h3>Replay an old refresh token</h3>
          <p>
            Each refresh rotates the refresh token and blacklists the old one. Click Refresh tokens in step 1, then
            try the old one here.
          </p>
          <div className="row">
            <button className="btn btn-small" onClick={replayRotated} disabled={!previousRefresh}>
              Replay old refresh token
            </button>
            {replay !== null && <StatusBadge status={replay} expected={401} />}
          </div>
          {!previousRefresh && <p className="muted small">Refresh your tokens once to enable this.</p>}
        </div>

        <div className="subpanel">
          <h3>Guess the password</h3>
          <p>
            Six wrong passwords in a row. The first five get 401; then the server throttles this network with 429
            for about a minute, including real logins.
          </p>
          <div className="row">
            <button className="btn btn-small" onClick={bruteForce} disabled={bruting}>
              {bruting ? "Guessing…" : "Send 6 wrong passwords"}
            </button>
          </div>
          {brute.length > 0 && (
            <ol className="brute">
              {brute.map((s, i) => (
                <li key={i}>
                  <span className="muted">Guess {i + 1}</span> <StatusBadge status={s} />
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}
