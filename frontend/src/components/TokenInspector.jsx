import { useState } from "react";
import { decodeToken, formatDuration, splitToken } from "../lib/jwt.js";

const PARTS = [
  { key: "header", name: "Header", what: "Which algorithm signed it" },
  { key: "payload", name: "Payload", what: "Claims about you. Encoded, not encrypted: anyone can read it" },
  { key: "signature", name: "Signature", what: "HMAC-SHA256 of the first two parts with the server's secret key" },
];

function time(epoch) {
  return epoch ? new Date(epoch * 1000).toLocaleTimeString() : "";
}

function Claim({ name, value, note }) {
  return (
    <div className="claim">
      <dt>{name}</dt>
      <dd>
        <code>{JSON.stringify(value)}</code>
        {note && <span className="claim-note">{note}</span>}
      </dd>
    </div>
  );
}

export default function TokenInspector({ tokens, now }) {
  const [which, setWhich] = useState("access");

  if (!tokens) {
    return <div className="panel empty">Log in to see your tokens here.</div>;
  }

  const token = tokens[which];
  const parts = splitToken(token);
  const { header, payload } = decodeToken(token);
  const lifetime = payload.exp - payload.iat;
  const left = Math.floor(payload.exp - now / 1000);
  const pct = Math.max(0, Math.min(100, (left / lifetime) * 100));
  const expired = left <= 0;

  return (
    <div className="panel">
      <div className="tabs" role="tablist" aria-label="Token">
        {["access", "refresh"].map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={which === t}
            className={`tab ${which === t ? "active" : ""}`}
            onClick={() => setWhich(t)}
          >
            {t === "access" ? "Access token (5 minutes)" : "Refresh token (1 day)"}
          </button>
        ))}
      </div>

      <p className="token-string" aria-label="The encoded token">
        <span className="part-h">{parts.header}</span>
        <span className="dot">.</span>
        <span className="part-p">{parts.payload}</span>
        <span className="dot">.</span>
        <span className="part-s">{parts.signature}</span>
      </p>

      <ul className="legend">
        {PARTS.map((p) => (
          <li key={p.key}>
            <i className={`swatch swatch-${p.key}`} aria-hidden="true" />
            <strong>{p.name}</strong> {p.what}
          </li>
        ))}
      </ul>

      <div className="decoded">
        <div>
          <h3>Header, decoded</h3>
          <dl>
            <Claim name="alg" value={header.alg} note="the only algorithm the server accepts" />
            <Claim name="typ" value={header.typ} />
          </dl>
        </div>
        <div>
          <h3>Payload, decoded</h3>
          <dl>
            <Claim name="token_type" value={payload.token_type} />
            <Claim name="user_id" value={payload.user_id} note="who you are" />
            <Claim name="iat" value={payload.iat} note={`issued ${time(payload.iat)}`} />
            <Claim name="exp" value={payload.exp} note={`expires ${time(payload.exp)}`} />
            <Claim name="jti" value={payload.jti} note="unique ID, used for blacklisting" />
          </dl>
        </div>
      </div>

      <div className={`expiry ${expired ? "is-expired" : pct < 25 ? "is-low" : ""}`}>
        <div className="expiry-text">
          {expired
            ? `Expired ${formatDuration(-left)} ago. The server will now reject this token.`
            : `Valid for another ${formatDuration(left)} of ${formatDuration(lifetime)}.`}
        </div>
        <div
          className="expiry-bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(pct)}
          aria-label="Time left before expiry"
        >
          <div className="expiry-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}
