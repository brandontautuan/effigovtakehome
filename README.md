# Effigov Take-home

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

## Voice agent

The `agent/` directory contains the LiveKit voice agent for the missed-trash-pickup demo. It collects the resident's name, phone number, and a short description, then calls `POST /cases` on this backend. The agent never opens the SQLite database directly.

### Configure LiveKit

Create `agent/.env.local` from the example and add your LiveKit Cloud credentials. LiveKit Inference supplies the speech-to-text, language model, and text-to-speech models used by this small demo.

```bash
cd agent
cp .env.example .env.local
```

Required values:

```text
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
BACKEND_URL=http://127.0.0.1:8000
```

### Run the backend and voice agent

In one terminal, start the API:

```bash
cd backend
uv run fastapi dev app/main.py
```

In a second terminal, install and start the LiveKit agent:

```bash
cd agent
uv sync
uv run python agent.py console
```

`console` starts an interactive local voice session. Current LiveKit releases mark this source-command form as deprecated in favor of the LiveKit CLI equivalent, `lk agent console`. It remains a working option when the CLI is not installed. To make the agent available to a LiveKit room later, use:

```bash
uv run python agent.py dev
```

After reporting a missed pickup, confirm the case was stored with:

```bash
curl http://127.0.0.1:8000/cases
```

The agent exposes three LLM tools: `create_case` (required), plus `lookup_case` and `update_case`. Each calls the existing FastAPI endpoint over HTTP and returns the API response to the agent. If the backend call fails, the tool returns an error and the agent is instructed not to claim that a case was created.

## Known limitations

- This demo requires LiveKit Cloud credentials for LiveKit Inference; no provider keys are needed beyond those credentials.
- The agent supports only the narrow missed-trash-pickup workflow. Telephony is intentionally not part of this phase.

## Staff dashboard

The `frontend/` Next.js app is a lightweight staff view over the FastAPI case API. It reads cases through `GET /cases` and `GET /cases/{id}`, and the status selector sends `PATCH /cases/{id}`. It does not access SQLite directly.

Create `frontend/.env.local` from the example if the API is not running on its default local URL:

```bash
cd frontend
cp .env.example .env.local
```

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start the dashboard while the backend is running:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:3000. The case list and detail view poll FastAPI every three seconds, so cases created or updated by the voice agent appear without a manual browser refresh.

## Case activity

Each new case receives a `CaseEvent` in SQLite. Later changes to status, notes, or description receive one event per field that actually changed. Events record a concise description, timestamp, source (`voice_agent`, `staff_dashboard`, or `api`), and old/new values when applicable.

The case detail page requests `GET /cases/{id}/events` every three seconds alongside the case itself. The voice agent sends `voice_agent` as source metadata and the dashboard sends `staff_dashboard` when it changes a status.
