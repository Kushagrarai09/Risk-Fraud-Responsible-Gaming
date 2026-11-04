# Risk, Fraud & Responsible-Gaming Analytics Platform

A local-first portfolio MVP covering responsible-gaming policy enforcement, fraud rules, Isolation Forest anomaly scoring, an admin review queue, and audit records.

## Stack
- Django REST Framework + PostgreSQL
- Redis + Celery
- scikit-learn Isolation Forest
- React + Vite + TypeScript
- Docker Compose

## Features
- JWT authentication and staff-gated admin endpoints
- Deposit and loss limits, cool-off and self-exclusion controls
- Transaction-safe deposit checks and event idempotency
- Rapid-deposit and bonus-claim detection rules
- Synthetic-data Isolation Forest training/scoring
- Admin review decisions and audit trail

## Quick start
1. Copy `.env.example` to `.env` and replace `DJANGO_SECRET_KEY`.
2. Run `docker compose up --build`.
3. Create a staff user: `docker compose exec api python manage.py createsuperuser`.
4. Open the dashboard at http://localhost:5173 and API at http://localhost:8000/api/health/.

## Safety and limitations
This repository is a portfolio prototype using synthetic/demo activity only. It does not integrate real-money payments and is not a production compliance or fraud-prevention system. Model anomaly scores are review signals, not proof of fraud. Production use requires independent security, legal, privacy, data governance, and responsible-gaming review.

See `docs/PLAYLEDGER_INTEGRATION.md` for a suggested event integration design.