# JWT Authentication in Django REST Framework

A REST API built with Django REST Framework and SimpleJWT that demonstrates login,
access and refresh tokens, a protected Dog API endpoint, logout by refresh-token
blacklisting, and how JWT compares with Django session authentication.

## 1. Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # Windows: copy .env.example .env
# Generate two DIFFERENT keys and paste them into .env
python -c "import secrets; print(secrets.token_urlsafe(50))"   # DJANGO_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))"   # JWT_SIGNING_KEY
# Optional: put your key from https://thedogapi.com in DOG_API_KEY

python manage.py migrate
python manage.py create_demo_user    # users "demo" and "other", password DogsAreGreat!2026
python manage.py runserver
```

The app refuses to start if `DJANGO_SECRET_KEY` or `JWT_SIGNING_KEY` is missing,
if the JWT key is shorter than 32 characters, or if the two keys are the same.

## 2. Configuration (Step 2 of the methodology)

| Setting | Value | Where |
|---|---|---|
| Access-token lifetime | 5 minutes | `SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]` |
| Refresh-token lifetime | 1 day | `SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]` |
| Signing algorithm | HS256 | `SIMPLE_JWT["ALGORITHM"]` |
| Signing key | env var `JWT_SIGNING_KEY` | `.env`, never in code |
| Refresh rotation | on | `ROTATE_REFRESH_TOKENS` |
| Blacklist after rotation | on | `BLACKLIST_AFTER_ROTATION` + `token_blacklist` app |
| Login throttle | 5/min per client IP | `LOGIN_THROTTLE_RATE`, `ScopedRateThrottle` |
| Dog API key | env var `DOG_API_KEY` | sent only server → Dog API |

## 3. Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/login/` | none (throttled) | `{username, password}` → `{access, refresh}` |
| POST | `/api/auth/refresh/` | none | `{refresh}` → new `{access, refresh}`; old refresh blacklisted |
| POST | `/api/auth/logout/` | Bearer access | `{refresh}` → refresh token blacklisted |
| GET | `/api/auth/me/` | Bearer access | current user |
| GET | `/api/dogs/breeds/?limit=10&page=0` | Bearer access | breeds from The Dog API (limit 1–50) |
| GET | `/api/dogs/breeds/<id>/` | Bearer access | one breed |
| POST | `/api/session/login/` | none (throttled) | session login, sets `sessionid` + `csrftoken` cookies |
| POST | `/api/session/logout/` | session + `X-CSRFToken` | deletes the server-side session |
| GET | `/api/session/me/` | session cookie | current user |

Dog API upstream errors map to: timeout → 504, unreachable → 502, upstream 5xx → 502,
upstream rejects our key → 502 (key never echoed), upstream rate limit → 503,
unknown breed → 404, invalid JSON → 502.

## 4. Automated tests (Step 5)

```bash
python manage.py test -v 2
```

The Dog API is mocked in tests, so they run offline. Expiry is tested by moving the
clock with `freezegun` rather than sleeping. After each run, a Markdown results table
(scenario, expected result, outcome) is written to **`test_results/latest.md`** for the report.

| File | Covers |
|---|---|
| `accounts/tests/test_login.py` | login success/failure, token claims and lifetimes, throttling, X-Forwarded-For spoofing |
| `accounts/tests/test_access_control.py` | missing, malformed, expired and modified tokens (user_id, exp, type, signature, `alg: none`, HS512 header, forged key) |
| `accounts/tests/test_refresh_logout.py` | refresh, rotation reuse, refresh expiry, logout, reuse after logout, access after logout |
| `accounts/tests/test_session_comparison.py` | session login/logout, CSRF, cookie reuse after logout, side-by-side revocation |
| `dogs/tests.py` | protected Dog API endpoint, key secrecy, upstream error handling |

## 5. Postman demonstration

Import `../postman/JWT_DRF_Demo.postman_collection.json`, start the server, and run the
folders in order (each request has a pass/fail test):

1. Login — success and failures; stores `{{access}}` and `{{refresh}}`.
2. Protected resources — valid, missing, expired and five kinds of tampered token
   (tampered tokens are built by pre-request scripts from your real token).
3. Refresh and rotation — replaying the rotated-out refresh token fails.
4. Logout — refresh fails afterwards, but the access token still works.
5. Session comparison — CSRF requirement and a copied cookie failing after logout.
6. Throttling — run in the Collection Runner with 6+ iterations; run it last.

For the expired-token request without waiting 5 minutes:

```bash
python manage.py make_expired_token --username demo
```

and paste the output into the `expired_access` collection variable.

## 6. Security decisions worth noting in the report

- **Separate signing key** from `SECRET_KEY`, length-checked at startup.
- **Only HS256 accepted**: `alg: none` and algorithm-switch tokens are rejected.
- **Logout checks ownership**: a user cannot blacklist another user's refresh token.
- **Throttle uses REMOTE_ADDR** (`NUM_PROXIES=0`). DRF's default trusts the
  client-sent `X-Forwarded-For`, which would let an attacker bypass the login limit
  by faking a new IP per request. Set `NUM_PROXIES` to your proxy count in production.
- **Dog API key stays server-side**, and the upstream response is reduced to a
  fixed set of fields.

## 7. Observed limitations (inputs for the comparison)

- An access token keeps working after logout and after a password change until it
  expires (≤ 5 minutes). Logout revokes only the refresh token.
- Rotation gives each new refresh token a fresh 1-day lifetime, so an active client
  can stay logged in indefinitely.
- The JWT payload is readable by anyone holding the token (base64, not encrypted).
- Session logout takes effect immediately, but session auth needs server-side state
  and CSRF protection; session login here is CSRF-exempt (login-CSRF trade-off).
- The login throttle is per IP and stored in LocMem cache: it does not stop
  distributed guessing and is per-process. Production would use Redis and per-account limits.
- HTTPS is assumed (out of scope); without it every token can be intercepted.
