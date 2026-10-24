// Small fetch wrapper. Every request is recorded in a log that the
// "Request log" panel shows, so the audience can see each call and its status.

const listeners = new Set();
let entries = [];
let nextId = 1;

export function subscribeLog(fn) {
  listeners.add(fn);
  fn(entries);
  return () => listeners.delete(fn);
}

export function clearLog() {
  entries = [];
  listeners.forEach((fn) => fn(entries));
}

function record(entry) {
  entries = [{ id: nextId++, at: new Date(), ...entry }, ...entries].slice(0, 60);
  listeners.forEach((fn) => fn(entries));
}

/**
 * Call the Django API.
 * @param {string} path      e.g. "/api/auth/me/"
 * @param {object} options   method, token (Bearer), body (JSON), headers, label (shown in the log)
 * @returns {{status:number, ok:boolean, data:any}}
 */
export async function api(path, { method = "GET", token, body, headers = {}, label } = {}) {
  const h = { Accept: "application/json", ...headers };
  if (body !== undefined) h["Content-Type"] = "application/json";
  if (token !== undefined && token !== null) h.Authorization = `Bearer ${token}`;

  const started = performance.now();
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: h,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: "same-origin", // send the session cookie for the session demo
    });
  } catch {
    const data = { detail: "Could not reach the server. Is it running?" };
    record({ method, path, status: 0, ms: 0, label, auth: authKind(h) });
    return { status: 0, ok: false, data };
  }

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text.slice(0, 200) };
  }
  record({
    method,
    path,
    status: res.status,
    ms: Math.round(performance.now() - started),
    label,
    auth: authKind(h),
  });
  return { status: res.status, ok: res.ok, data, retryAfter: res.headers.get("Retry-After") };
}

function authKind(h) {
  if (h.Authorization) return "Bearer";
  if (h["X-CSRFToken"]) return "Cookie + CSRF";
  return "";
}
