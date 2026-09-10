# Effigov Take-home: Backend Milestone

A small FastAPI backend for creating and managing resident service cases. It uses SQLite and SQLAlchemy to keep the implementation easy to inspect and run locally.

## Run locally

From the repository root:

```bash
cd backend
uv sync
uv run fastapi dev app/main.py
```

The API runs at `http://127.0.0.1:8000`. Open the interactive Swagger docs at `http://127.0.0.1:8000/docs`.

The SQLite database is created automatically at `backend/effigov.db` on first startup.

## Test the API

With the server running, in a second terminal:

```bash
curl -X POST http://127.0.0.1:8000/cases \
  -H 'Content-Type: application/json' \
  -d '{"name":"Brandon","phone":"5551234567","issue_type":"missed_pickup","description":"Trash was not collected yesterday."}'

curl http://127.0.0.1:8000/cases
curl http://127.0.0.1:8000/cases/1

curl -X PATCH http://127.0.0.1:8000/cases/1 \
  -H 'Content-Type: application/json' \
  -d '{"notes":"Resident called to follow up."}'

curl 'http://127.0.0.1:8000/cases/lookup?case_number=EG-1001'
curl 'http://127.0.0.1:8000/cases/lookup?phone=5551234567'
```

## API

- `POST /cases` creates a case and generates its case number.
- `GET /cases` lists all cases, newest first.
- `GET /cases/{case_id}` returns one case or a 404.
- `PATCH /cases/{case_id}` partially updates `status`, `notes`, or `description`.
- `GET /cases/lookup?case_number=EG-1001` or `GET /cases/lookup?phone=5551234567` finds matching cases.

Case numbers are derived from the database ID (`EG-1001` for ID 1), which is deterministic and sufficient for the local demo.
