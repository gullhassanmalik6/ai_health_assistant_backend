# AI Doctor Backend

Phase 1 production API for **AI Doctor**.

The website lives in [ai_health_assistant_frontend](https://github.com/gullhassanmalik6/ai_health_assistant_frontend). Clients talk only to this HTTPS REST API. They must never contain OpenAI/Gemini keys, Firebase Admin credentials, or database secrets.

Run every command below from this repository root.

```
Flutter / Web
    → HTTPS REST API
        → FastAPI
            → Service layer
                → Repository layer
                    → PostgreSQL
```

Authentication:

```
Flutter / Web
    → Firebase Authentication
        → Firebase ID token
            → FastAPI verifies the token
                → FastAPI creates/updates the application user
                    → PostgreSQL
```

Firebase Authentication owns identity. This API owns authorization, profiles, health data, and (in later phases) AI, files, subscriptions, and notifications.

Passwords are never stored in PostgreSQL.

---

## Project overview

Phase 1 covers:

- Splash / session initialization
- Registration, login, logout
- Email verification and password reset
- Google, Apple, and guest (anonymous) authentication
- User profile
- Structured allergies, conditions, and current medications
- Profile completion scoring
- Account deletion

Later phases (AI chat, lab OCR, imaging, premium, and so on) plug into the existing service/repository layout. Provider seams already exist for AI (`app/services/ai`) and object storage (`app/services/storage`). Those implementations are intentionally not built in Phase 1.

---

## Requirements

- Python 3.12+
- PostgreSQL 16+
- A Firebase project with Authentication enabled (Email/Password, Google, Apple, Anonymous)
- Docker and Docker Compose (optional, recommended for local PostgreSQL)

---

## Installation

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with real values. Never commit `.env` or a Firebase service-account JSON file.

---

## Environment variables

See `.env.example`. Important variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+asyncpg://...`) |
| `TEST_DATABASE_URL` | Dedicated test database (never production) |
| `FIREBASE_PROJECT_ID` | Firebase project |
| `FIREBASE_CLIENT_EMAIL` | Service account email |
| `FIREBASE_PRIVATE_KEY` | Service account private key (`\n` escaped) |
| `FIREBASE_API_KEY` | Firebase Web API key (Identity Toolkit REST: login, reset, anonymous) |
| `FIREBASE_CREDENTIALS_PATH` | Optional path to the service-account JSON (preferred in production) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origins. Do not use `*` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `ENVIRONMENT` | `development`, `staging`, `production`, or `test` |
| `LOG_LEVEL` | Logging level |

Production refuses `CORS_ALLOWED_ORIGINS=*` and `ALLOWED_HOSTS=*`.

---

## Database

Create the database, then run migrations. Do not create tables by hand.

```bash
alembic upgrade head
```

Rollback:

```bash
alembic downgrade -1
```

Tables created in Phase 1:

- `users` — identity only (Firebase UID, email, provider, guest flag)
- `user_profiles` — demographics and vitals, with units
- `user_allergies`
- `user_conditions`
- `user_medications`

A guest row can later be upgraded to a registered account by linking a Firebase credential to the same UID (`is_guest` is cleared automatically).

---

## Run

With PostgreSQL running and `.env` configured:

```bash
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`.

---

## Docker

```bash
docker compose up --build
```

Compose starts PostgreSQL and the API. Secrets come from `.env`, not from `docker-compose.yml`. On startup the container runs `alembic upgrade head`, then Uvicorn.

---

## Cloud deployment (Render / Railway / Fly)

The crash `Connect call failed ('127.0.0.1', 5432)` means the API container tried to open Postgres on **itself**. There is no database process in the web service.

1. Create a **PostgreSQL** addon on the same platform (or Neon/Supabase).
2. Copy that database URL into the API service env var `DATABASE_URL`.
   Provider URLs such as `postgres://user:pass@host:5432/db` are accepted.
3. Do **not** leave `DATABASE_URL` pointing at `localhost` or `127.0.0.1`.
4. Set `ENVIRONMENT=production`.
5. Set `CORS_ALLOWED_ORIGINS` to your frontend origin.
6. Set `ALLOWED_HOSTS` to your API hostname (example: `ai-doctor-api.onrender.com`).

Internal Docker Compose still uses host `db`, which is correct for local compose only.

---

## API documentation

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- OpenAPI JSON: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

Authorize Swagger with a Firebase ID token: `Bearer <idToken>`.

---

## Health checks

- `GET /health` — process is running
- `GET /health/ready` — database is reachable

Neither endpoint exposes infrastructure details.

---

## Testing

Tests use an in-memory SQLite database and mocked Firebase. They never touch production data.

```bash
pytest
```

With coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

To run against a real PostgreSQL test database instead, set `TEST_DATABASE_URL` and point tests at that URL. Do not use the production database.

---

## Authentication contract for Flutter / Web

1. Obtain a Firebase ID token on the client (email/password, Google, Apple, or anonymous).
2. Call this API with `Authorization: Bearer <idToken>`.
3. Never send a `user_id` to select whose data to load. The backend derives the user from the verified token.
4. Registration and login also return `tokens.id_token` / `refresh_token` when the backend performs the Identity Toolkit call. Social sign-in sends the token the client already has.

### Versioned endpoints

Base URL: `/api/v1`

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Email/password registration |
| POST | `/api/v1/auth/login` | Email/password login |
| POST | `/api/v1/auth/google` | Google (Firebase ID token) |
| POST | `/api/v1/auth/apple` | Apple (Firebase ID token) |
| POST | `/api/v1/auth/guest` | Anonymous guest session |
| POST | `/api/v1/auth/logout` | Application-level session invalidation |
| POST | `/api/v1/auth/forgot-password` | Generic reset email (no account-existence leak) |
| POST | `/api/v1/auth/reset-password` | Confirm reset with `oob_code` |
| GET | `/api/v1/auth/verification-status` | `{ "verified": true }` |
| POST | `/api/v1/auth/send-verification` | Send verification email |
| GET | `/api/v1/auth/session` | Splash / session bootstrap |
| POST | `/api/v1/auth/refresh` | Refresh Firebase ID token |
| GET | `/api/v1/users/me` | Current user |
| PATCH | `/api/v1/users/me` | Name / onboarding flag |
| DELETE | `/api/v1/users/me` | Account deletion |
| GET/PUT/PATCH/DELETE | `/api/v1/profile` | Health profile (DELETE resets profile, not the account) |
| GET | `/api/v1/profile/completion` | Backend-calculated completion |
| CRUD | `/api/v1/profile/allergies` | Allergies |
| CRUD | `/api/v1/profile/conditions` | Existing diseases |
| CRUD | `/api/v1/profile/medications` | Current medications |

### Response envelope

Success:

```json
{
  "success": true,
  "message": "Profile updated successfully.",
  "data": {}
}
```

Error:

```json
{
  "success": false,
  "message": "Invalid authentication token.",
  "error_code": "AUTH_TOKEN_INVALID",
  "details": null
}
```

Height and weight always include units:

```json
{
  "height": { "value": 175, "unit": "cm" },
  "weight": { "value": 70, "unit": "kg" }
}
```

---

## Security notes

- Verify Firebase ID tokens on every authenticated request.
- Guests are flagged (`is_guest`) and rejected by `require_registered_user()` when a later feature needs a registered account.
- Logout records `token_invalidated_at` so tokens issued before that moment are rejected. Redis-backed revocation can be added later without changing the API.
- Request bodies containing health data or passwords are not logged.
- Rate limiting is in-memory in Phase 1 (`slowapi`). Redis can replace the storage backend later.
- CORS and trusted hosts are environment-driven.

---

## Adding a later phase

1. Add models under `app/models/`.
2. Add a repository under `app/repositories/`.
3. Add a service under `app/services/`.
4. Add `app/api/v1/<feature>/router.py` and schemas.
5. Include the router in `app/api/v1/router.py`.
6. Generate an Alembic revision.

Do not put business logic in routers. Do not put AI provider keys in Flutter.
