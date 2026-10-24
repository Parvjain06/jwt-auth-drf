# JWT Lab: JWT Authentication in Django REST Framework

A Django REST Framework API secured with SimpleJWT, and a React page that demonstrates it live:
log in, inspect the token, fetch protected dog breeds from [The Dog API](https://thedogapi.com/),
attack the API with tampered and expired tokens, and compare JWT logout with session logout.

**Live demo:** _add your Render link here_ (demo login: `demo` / `DogsAreGreat!2026`)

## What it shows

| Step on the page | What happens | Result |
|---|---|---|
| 1. Log in | Username + password → access token (5 min) + refresh token (1 day); optional auto-refresh before expiry | 200 |
| 2. Look inside the token | Header, payload and signature, decoded, with an expiry countdown | — |
| 3. Fetch protected data | Dog breeds through the API, only with a valid access token | 200 / 401 |
| 4. Attack the API | Nine attacks (changed user ID, extended expiry, corrupted signature, `alg: none`, forged key, wrong token type, expired token…) plus a token editor to write your own; refresh-token replay; password guessing | 401, 429 |
| 5. Where to keep the token | A simulated XSS script steals the token from localStorage, but not from page memory or an HttpOnly cookie | stolen vs safe |
| 6. Log out | JWT: refresh token blacklisted, access token still works until expiry. Session: cookie dead at once | 200 vs 403 |
| Research answers | Structure of a JWT; access vs refresh token; JWT vs session storage and risks | — |

## Project layout

```
backend/    Django + DRF + SimpleJWT API, 72 automated tests (see backend/README.md)
  frontend_dist/   the built React app, served by Django at /
frontend/   React source (Vite)
postman/    Postman collection with 27 demo requests
render.yaml one-click deployment to Render
```

## Run it on your computer

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # then add two different random keys (see backend/README.md)
python manage.py migrate
python manage.py create_demo_user
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the React page. Run the tests with `python manage.py test -v 2`.

### Changing the frontend

The built page is already in `backend/frontend_dist`, so Node is only needed if you edit the React code:

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, with /api forwarded to Django on port 8000
npm run build    # writes the new build into backend/frontend_dist; commit it
```

## Deploy (Render, free)

1. Push this repository to GitHub.
2. On [render.com](https://render.com), sign in with GitHub and choose **New → Blueprint**, then pick this repository.
3. Render reads `render.yaml`. When asked, paste your Dog API key into `DOG_API_KEY`. The Django and JWT keys are generated automatically.
4. Click **Apply**. After the build finishes, your site is live at `https://<name>.onrender.com`.

Free Render services sleep after 15 minutes without visitors; the first visit after that takes about a minute to wake up. The database resets on each restart, and the demo user is recreated automatically.

## Security notes

- Signing key and API key come from environment variables, never from the code.
- Only HS256 is accepted; the key must be 32+ characters and differ from Django's `SECRET_KEY`.
- The browser keeps tokens in memory, not `localStorage`, so a malicious script cannot read them from storage.
- Login is throttled to 5 attempts per minute per IP, using the real client IP behind Render's proxy.
- The Dog API key stays on the server and never appears in a response.
