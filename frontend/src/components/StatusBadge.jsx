const TEXT = {
  0: "No response",
  200: "200 OK",
  400: "400 Bad Request",
  401: "401 Unauthorized",
  403: "403 Forbidden",
  404: "404 Not Found",
  429: "429 Too Many Requests",
  502: "502 Bad Gateway",
  503: "503 Unavailable",
  504: "504 Timeout",
};

export function statusText(code) {
  return TEXT[code] || String(code);
}

/** Coloured HTTP status. `expected` (optional) adds a match / mismatch mark. */
export default function StatusBadge({ status, expected }) {
  if (status === undefined || status === null) return <span className="badge badge-idle">Not run</span>;
  const tone = status >= 200 && status < 300 ? "ok" : status === 429 ? "warn" : "err";
  const match = expected === undefined ? null : status === expected;
  return (
    <span className={`badge badge-${tone}`}>
      {statusText(status)}
      {match !== null && (
        <span className={`match ${match ? "yes" : "no"}`} aria-label={match ? "as expected" : "unexpected"}>
          {match ? "✓" : "✗"}
        </span>
      )}
    </span>
  );
}
