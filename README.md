# JWT Authentication in Django REST Framework

A college project on how JSON Web Tokens work in a Django REST Framework API, how well they hold up against tampered and expired tokens, and how they compare with Django's normal session login.

Live demo: [add Render link]

Team: Dhruv Parekh (E021), Parv Jain (E022), Jash Vakharia (E023), Himanshu Thakkar (E062)

## About the project

The API lets a user log in and get two tokens from SimpleJWT: an access token that lasts 5 minutes and a refresh token that lasts 1 day. The access token is needed to read dog breed data, which the server fetches from [The Dog API](https://thedogapi.com/). Logging out puts the refresh token on a blacklist so it cannot be used again.

We also added Django session login to the same server so the two methods could be tested side by side.

The main things we wanted to find out:

- Can the API be fooled by a token that has been edited, forged or has expired?
- What actually happens to each kind of login when the user logs out?
- Where should a browser keep a token, and what are the risks of each option?

## What we found

- Every edited or fake token was rejected with 401. This included changing the user ID, pushing the expiry date forward, breaking or removing the signature, the "alg: none" trick, and signing with a guessed key.
- Expired tokens were rejected exactly on time.
- After logout the refresh token stopped working straight away, but the access token kept working until its 5 minutes ran out.
- A session cookie stopped working the moment the user logged out.
- A token saved in localStorage could be read by a script running on the page. Tokens kept in memory and HttpOnly cookies could not.

## The demo page

The live site walks through the project in six steps:

1. Log in and get the two tokens
2. See what is inside a token (header, payload and signature)
3. Load dog breeds with and without a valid token
4. Try different attacks on the API, or edit the token yourself
5. Compare where a token can be stored
6. Log out with JWT and with sessions and compare the results

Demo login: `demo` / `DogsAreGreat!2026`

The site is on Render's free plan, so if nobody has opened it for a while the first load can take about a minute.

## Built with

Python, Django, Django REST Framework, SimpleJWT, SQLite, React, Postman and The Dog API. Hosted on Render.

## Running it locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and fill in `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY` (two different random strings) and your `DOG_API_KEY`. Then:

```bash
python manage.py migrate
python manage.py create_demo_user
python manage.py runserver
```

The site will be at http://127.0.0.1:8000/

To run the tests:

```bash
python manage.py test
```

There are 72 tests and all of them pass. The `postman` folder has a collection of 27 requests that can be imported into Postman.

## Folders

- `backend` has the Django project and the tests
- `frontend` has the React code for the demo page
- `postman` has the Postman collection
