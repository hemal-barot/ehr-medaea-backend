# ehr-medaea-backend

FastAPI + Django Admin backend for the **Medaea EHR** platform — a HIPAA/ONC-aware Electronic Health Record system.

---

## Tech stack

| Component | Technology |
|---|---|
| Core API | FastAPI 0.135 + SQLAlchemy 2 + PostgreSQL 16 |
| Admin panel | Django 5.2 + Gunicorn |
| Auth | JWT (python-jose) + bcrypt + TOTP MFA (pyotp) |
| Async email | aiosmtplib (SMTP STARTTLS) |
| SMS | Twilio |
| Containerization | Docker + Docker Compose |
| Tests | pytest + behave (BDD) |

---

## Services

| Service | Port | Description |
|---|---|---|
| FastAPI | 8000 | REST API + interactive docs |
| Django Admin | 9000 | Operator portal |
| PostgreSQL | 5432 | Shared database |

---

## Quick start — Docker

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — set SECRET_KEY, DJANGO_SECRET_KEY, POSTGRES_PASSWORD

# 2. Build and start (Postgres + FastAPI + Django Admin)
docker compose up --build

# 3. (First time) Create Django superuser
docker compose exec django python django_app/manage.py createsuperuser
```

API docs: **http://localhost:8000/api/docs**  
Django admin: **http://localhost:9000/admin/**

---

## Quick start — Local (no Docker)

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables (see .env.example for all options)
export DATABASE_URL="postgresql://medaea:medaea_secret@localhost:5432/medaea_db"
export SECRET_KEY="your-32-char-hex-secret"
export MFA_ENCRYPTION_KEY="your-fernet-key"
export PYTHONPATH=$(pwd)

# 4. Apply schema and start
python scripts/migrate_calendar_tables.py
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Project structure

```
ehr-medaea-backend/
│
├── fastapi_app/                 FastAPI core API
│   ├── core/
│   │   ├── config.py            All settings (env-driven via os.getenv)
│   │   ├── database.py          SQLAlchemy engine + session factory
│   │   ├── security.py          JWT, password hashing, token creation
│   │   └── deps.py              FastAPI dependency injection helpers
│   ├── db/
│   │   └── models.py            All SQLAlchemy ORM models
│   └── domains/
│       ├── identity/            Auth, JWT, MFA (TOTP + SMS), user management
│       ├── patient/             Patient CRUD + demographics
│       ├── organization/        Multi-tenant organization management
│       ├── scheduling/          Appointments, calendar, rooms, PTO, on-call
│       ├── encounter/           SOAP clinical notes
│       ├── charting/            Allergies, medications, problems, immunizations
│       └── audit/               Immutable audit log
│
├── django_app/                  Django admin portal
│   ├── config/                  Settings, URLs, WSGI
│   └── admin_portal/            managed=False model proxies + rich ModelAdmin
│
├── scripts/
│   ├── migrate_calendar_tables.py   psycopg2 migration runner
│   └── generate_postman.py          Postman collection generator
│
├── tests/                       pytest unit + integration tests
│   ├── conftest.py              Shared fixtures (SQLite test DB)
│   ├── test_auth.py             Auth endpoint tests
│   ├── test_patients.py         Patient CRUD tests
│   ├── test_appointments.py     Appointment + calendar tests
│   └── test_scheduling.py       Advanced scheduling (PTO, rooms, rules)
│
├── features/                    Behave BDD tests
│   ├── auth.feature
│   ├── patients.feature
│   ├── appointments.feature
│   ├── environment.py
│   └── steps/
│       ├── auth_steps.py
│       ├── patient_steps.py
│       └── appointment_steps.py
│
├── Dockerfile                   FastAPI image
├── Dockerfile.django            Django image
├── docker-compose.yml           Full backend stack
├── requirements.txt             FastAPI dependencies
├── requirements-django.txt      Django dependencies
├── requirements-test.txt        Test dependencies
├── pyproject.toml               pytest + behave config
├── .env.example                 All environment variables documented
└── .gitignore
```

---

## Environment variables

See [`.env.example`](.env.example). All variables are read via `os.getenv()` — no hardcoded credentials.

Generate secrets:

```bash
# SECRET_KEY / DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# MFA_ENCRYPTION_KEY (Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Key variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | **Yes** | PostgreSQL connection string |
| `SECRET_KEY` | **Yes** | JWT signing key (32+ hex chars) |
| `MFA_ENCRYPTION_KEY` | **Yes** | Fernet key for TOTP secret encryption |
| `DJANGO_SECRET_KEY` | **Yes** | Django CSRF/session signing key |
| `SMTP_USER` / `SMTP_PASSWORD` | Optional | Transactional email via SMTP |
| `TWILIO_*` | Optional | SMS MFA and notifications |
| `REQUIRE_EMAIL_VERIFICATION` | Optional | Gate login on email confirmation (default: false) |

---

## Running tests

### pytest (unit + integration)

```bash
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=fastapi_app --cov-report=html
```

### Behave (BDD)

```bash
pip install behave requests

# Ensure the API is running on localhost:8000, then:
behave features/

# Target a specific feature file
behave features/auth.feature

# Run against a different environment
MEDAEA_API_URL=http://staging.medaea.com behave features/
```

---

## Database schema

All tables created/altered by `scripts/migrate_calendar_tables.py`:

| Table | Description |
|---|---|
| `organizations` | Multi-tenant root |
| `users` | Providers and staff |
| `patients` | Patient demographics |
| `appointments` | Visits (duration, visit type, room) |
| `pto_requests` | Provider PTO |
| `availability_rules` | Recurring availability windows |
| `schedule_templates` | Day-template time blocks |
| `rooms` | Exam/virtual rooms |
| `room_bookings` | Room reservations |
| `staff_schedules` | Staff work calendars |
| `on_call_assignments` | On-call rotation log |
| `encounters` | SOAP clinical notes |
| `allergies` | Patient allergies |
| `medications` | Active medications |
| `problems` | Problem list |
| `immunizations` | Immunization records |
| `audit_logs` | Immutable event log |

### Run migrations

```bash
# Docker
docker compose exec fastapi python scripts/migrate_calendar_tables.py

# Local
PYTHONPATH=$(pwd) python scripts/migrate_calendar_tables.py
```

---

## API overview

Interactive docs: **GET /api/docs** (Swagger UI) · **GET /api/redoc** (ReDoc)

### Authentication

All endpoints except `/api/v1/auth/signup` and `/api/v1/auth/login` require `Authorization: Bearer <token>`.

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"dr@medaea.com","password":"Pass123!","first_name":"Dr","last_name":"Example","role":"physician"}'

# Login → get JWT
curl -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=dr@medaea.com" -F "password=Pass123!"

# Use token
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```

### Regenerate Postman collection

```bash
PYTHONPATH=$(pwd) python scripts/generate_postman.py
```

---

## Branching strategy

```
main ──────────────────────────────── production
  └── develop ───────────────────── staging
        ├── feature/TICKET-auth-mfa
        ├── feature/TICKET-scheduling
        └── hotfix/critical-fix    (→ main + develop)
```

| Branch | Purpose |
|---|---|
| `main` | Production-ready |
| `develop` | Integration / staging |
| `feature/*` | New features (from develop) |
| `bugfix/*` | Non-critical fixes (from develop) |
| `hotfix/*` | Critical fixes (from main → main + develop) |

Commit convention: `<type>(<scope>): <description>`  
Types: `feat` · `fix` · `chore` · `docs` · `test` · `refactor`

---

## Troubleshooting

**`password authentication failed`** — POSTGRES_PASSWORD in `.env` doesn't match the volume. Run `docker compose down -v && docker compose up --build`.

**FastAPI 500 on startup** — Check `docker compose logs fastapi`. A missing or invalid env var surfaces here.

**Django admin unstyled** — Run `docker compose exec django python django_app/manage.py collectstatic --noinput`.
