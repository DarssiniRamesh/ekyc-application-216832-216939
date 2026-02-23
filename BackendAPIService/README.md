# BackendAPIService (FastAPI)

Implements the EKYC backend business logic:
- Auth (JWT) and role-based access control (user/admin)
- KYC workflow (draft, document upload, submit, admin approve/reject)
- Audit logging for compliance-relevant actions
- PostgreSQL persistence via SQLAlchemy

## Configuration

Copy `.env.example` to your runtime environment and set at least:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `FRONTEND_ORIGIN` (optional for dev)

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize DB tables (dev-only create_all)
python -c "from app.db.init_db import init_db; init_db()"

uvicorn main:app --reload --port 8000
```

Open:
- http://localhost:8000/docs

## Notes

- Email verification is implemented as a workflow-state endpoint (`POST /auth/verify-email`) because the requirements do not specify an email delivery/token mechanism yet.
- Documents are stored as blobs in PostgreSQL by default; this can be replaced with object storage later without changing the API contract.
