# Changelog — ehr-medaea-backend

  All notable changes to the Medaea EHR FastAPI backend.

  ## [1.2.0] — 2026-04-03

  ### Added
  - Demo provider account created: demo@medaea.ai / Demo@1234 (Dr. Sarah Johnson, Internal Medicine)
  - Live environment validated: all 48 API endpoints tested and responding
  - API confirmed at external port 8000 via Replit proxy

  ### Tests (already in repo via Phase 1)
  - Full pytest suite: tests/test_auth.py, tests/test_patients.py, tests/test_appointments.py, tests/test_scheduling.py
  - BDD Behave suite: features/auth.feature, features/patients.feature, features/appointments.feature
  - Shared fixtures in tests/conftest.py (SQLite in-memory, no Postgres needed for tests)

  ## [1.1.0] — 2026-03-25

  ### Added
  - 48 REST API endpoints across 9 domain routers (auth, users, patients, encounters, appointments, calendar, documents, admin, analytics)
  - JWT authentication with MFA (TOTP + SMS)
  - HIPAA audit logging on all protected routes
  - Email service (SMTP) with templated emails
  - Full Alembic migration chain

  ## [1.0.0] — 2026-03-20

  ### Added
  - Initial FastAPI project structure with domain-driven design
  - PostgreSQL database with 19 tables
  - All DB models with HIPAA/ONC compliance comments
  - Docker + docker-compose setup
  