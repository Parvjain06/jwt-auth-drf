import { useState } from "react";
import { api } from "../lib/api.js";
import { buildToken, decodeToken, splitToken } from "../lib/jwt.js";
import StatusBadge from "./StatusBadge.jsx";

const pretty = (obj) => JSON.stringify(obj, null, 2);

const SIGNATURES = [
  { value: "keep", label: "Keep the original signature" },
  { value: "guess", label: "Sign with a guessed secret key" },
  { value: "none", label: "Remove the signature" },
];

export default function TokenEditor({ access }) {
  const original = decodeToken(access);
  const [headerText, setHeaderText] = useState(pretty(original.header));
  const [payloadText, setPayloadText] = useState(pretty(original.payload));
  const [signature, setSignature] = useState("keep");
  const [sent, setSent] = useState(null); // { token, status, detail }
  const [error, setError] = useState(null);

  function reset() {
    const fresh = decodeToken(access);
    setHeaderText(pretty(fresh.header));
    setPayloadText(pretty(fresh.payload));
    setSignature("keep");
    setSent(null);
    setError(null);
  }

  function edit(fn) {
    try {
      setPayloadText(pretty(fn(JSON.parse(payloadText))));
      setError(null);
    } catch {
      setError("The payload is not valid JSON. Fix it or press Reset.");
    }
  }

  async function send() {
    let headerObj, payloadObj;
    try {
      headerObj = JSON.parse(headerText);
      payloadObj = JSON.parse(payloadText);
    } catch {
      setError("The header or payload is not valid JSON. Check the quotes and commas, or press Reset.");
      return;
    }
    setError(null);
    const token = await buildToken(access, headerObj, payloadObj, signature);
    const res = await api("/api/auth/me/", { token, label: "Your own edited token" });
    setSent({ token, status: res.status, detail: res.data?.detail, user: res.data?.username });
  }

  const parts = sent ? splitToken(sent.token) : null;

  return (
    <div className="editor">
      <h3>Write your own attack</h3>
      <p>
        Edit your real token's header or payload, choose what to do with the signature, and send it to a protected
        endpoint. Only an untouched token signed with the server's secret is accepted.
      </p>

      <div className="row">
        <span className="muted small">Quick edits:</span>
        <button
          className="btn btn-small"
          onClick={() =>
            edit((p) => ({ ...p, user_id: typeof p.user_id === "number" ? p.user_id + 1 : String(Number(p.user_id) + 1) }))
          }
        >
          Become the next user
        </button>
        <button className="btn btn-small" onClick={() => edit((p) => ({ ...p, exp: 4102444800 }))}>
          Expire in 2100
        </button>
        <button className="btn btn-small" onClick={() => edit((p) => ({ ...p, is_staff: true, role: "admin" }))}>
          Make me an admin
        </button>
        <button className="btn btn-small btn-quiet" onClick={reset}>
          Reset
        </button>
      </div>

      <div className="editor-grid">
        <label className="editor-field editor-header">
          Header
          <textarea value={headerText} onChange={(e) => setHeaderText(e.target.value)} rows={5} spellCheck={false} />
        </label>
        <label className="editor-field editor-payload">
          Payload
          <textarea value={payloadText} onChange={(e) => setPayloadText(e.target.value)} rows={9} spellCheck={false} />
        </label>
      </div>

      <fieldset className="editor-sig">
        <legend>Signature</legend>
        {SIGNATURES.map((s) => (
          <label key={s.value}>
            <input
              type="radio"
              name="signature"
              value={s.value}
              checked={signature === s.value}
              onChange={() => setSignature(s.value)}
            />
            {s.label}
          </label>
        ))}
      </fieldset>

      {error && <p className="notice notice-bad">{error}</p>}

      <div className="row">
        <button className="btn btn-primary" onClick={send}>
          Send edited token
        </button>
        {sent && <StatusBadge status={sent.status} />}
      </div>

      {sent && (
        <div className="editor-result">
          <p className="token-string small-token">
            <span className="part-h">{parts.header}</span>
            <span className="dot">.</span>
            <span className="part-p">{parts.payload}</span>
            <span className="dot">.</span>
            <span className="part-s">{parts.signature || "(empty)"}</span>
          </p>
          <p className={`notice ${sent.status === 200 ? "notice-good" : "notice-bad"}`}>
            {sent.status === 200
              ? `Accepted as ${sent.user}. Nothing was changed, so the signature still matches.`
              : `Rejected: ${sent.detail || "invalid token"}. The signature no longer matches what the server computes with its secret key.`}
          </p>
        </div>
      )}
    </div>
  );
}
