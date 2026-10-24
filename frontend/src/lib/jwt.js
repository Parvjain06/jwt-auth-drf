// Helpers to read and tamper with JWTs in the browser — exactly what an
// attacker holding a token could do without knowing the server's signing key.

function b64urlToBytes(segment) {
  const b64 = segment.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(segment.length / 4) * 4, "=");
  const bin = atob(b64);
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

function bytesToB64url(bytes) {
  let bin = "";
  bytes.forEach((b) => (bin += String.fromCharCode(b)));
  return btoa(bin).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
}

export const enc = (obj) => bytesToB64url(new TextEncoder().encode(JSON.stringify(obj)));

export function splitToken(token) {
  const [header = "", payload = "", signature = ""] = (token || "").split(".");
  return { header, payload, signature };
}

export function decodeSegment(segment) {
  try {
    return JSON.parse(new TextDecoder().decode(b64urlToBytes(segment)));
  } catch {
    return null;
  }
}

export function decodeToken(token) {
  const { header, payload } = splitToken(token);
  return { header: decodeSegment(header), payload: decodeSegment(payload) };
}

/** Change claims but keep the ORIGINAL signature. */
export function withPayloadChanges(token, changes) {
  const { header, payload, signature } = splitToken(token);
  const claims = { ...decodeSegment(payload), ...changes };
  return `${header}.${enc(claims)}.${signature}`;
}

/** Change the first signature character (the last one may only hold padding bits). */
export function withCorruptedSignature(token) {
  const { header, payload, signature } = splitToken(token);
  const first = signature[0] === "A" ? "B" : "A";
  return `${header}.${payload}.${first}${signature.slice(1)}`;
}

/** The classic attack: header says "no signature needed", signature left empty. */
export function withAlgNone(token) {
  const { payload } = splitToken(token);
  return `${enc({ alg: "none", typ: "JWT" })}.${payload}.`;
}

export const GUESSED_KEY = "secret-guess-1234567890-abcdefghij";

async function hmacSha256(signingInput, secret) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return bytesToB64url(new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(signingInput))));
}

/** Same claims, signed with a key the attacker guessed. */
export async function resignedWithGuessedKey(token, guessedKey = GUESSED_KEY) {
  const claims = decodeToken(token).payload;
  const signingInput = `${enc({ alg: "HS256", typ: "JWT" })}.${enc(claims)}`;
  return `${signingInput}.${await hmacSha256(signingInput, guessedKey)}`;
}

/**
 * Build a token from an edited header and payload.
 * signature: "keep" = reuse the original signature, "guess" = sign with a guessed key, "none" = leave it empty.
 * Unchanged parts reuse the original bytes exactly, so an unedited token stays genuine.
 */
export async function buildToken(original, headerObj, payloadObj, signature) {
  const parts = splitToken(original);
  const orig = decodeToken(original);
  const h = JSON.stringify(headerObj) === JSON.stringify(orig.header) ? parts.header : enc(headerObj);
  const p = JSON.stringify(payloadObj) === JSON.stringify(orig.payload) ? parts.payload : enc(payloadObj);
  const signingInput = `${h}.${p}`;
  if (signature === "none") return `${signingInput}.`;
  if (signature === "guess") return `${signingInput}.${await hmacSha256(signingInput, GUESSED_KEY)}`;
  return `${signingInput}.${parts.signature}`;
}

/** Seconds until the token's exp claim (negative once expired). */
export function secondsLeft(token, nowMs) {
  const exp = decodeToken(token).payload?.exp;
  return typeof exp === "number" ? Math.floor(exp - nowMs / 1000) : null;
}

export function formatDuration(totalSeconds) {
  const s = Math.max(0, totalSeconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
}
