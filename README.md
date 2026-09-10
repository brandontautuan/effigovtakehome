# EffiGov Take-home

EffiGov is a local demo for city-service intake. Residents speak with a LiveKit voice agent to report missed trash pickups, ask about demo trash/recycling schedules, or approve a handoff request for another city team. Staff use a Next.js dashboard to monitor calls, service cases, transcripts, and handoffs. FastAPI and SQLite provide the application boundary and persistence layer.

```text
Resident
  ↓
LiveKit voice agent
  ↓
FastAPI call, transcript, and service-request API
  ↓
SQLite
  ↓
Next.js staff dashboard
```

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
- `GET /service-info/schedule?city=folsom` returns demo trash and recycling schedule data.
- `POST /service-requests` records a resident-approved handoff for another city team; `GET /service-requests` lists them.
- `POST /calls`, `GET /calls`, `GET /calls/{call_id}`, and `PATCH /calls/{call_id}` manage voice-call state.
- `POST` and `GET /calls/{call_id}/transcript` preserve finalized transcript messages.
- `GET /ws/calls` sends dashboard refresh notifications after call, transcript, case, and handoff changes. It is not a source of record.

Case numbers are derived from the database ID (`EG-1001` for ID 1), which is deterministic and sufficient for the local demo.

## Automated checks

No automated test suite is configured yet. The available static checks are:

```bash
cd backend && uv run python -m compileall -q app
cd agent && uv run python -m compileall -q agent.py case_api.py
cd frontend && npm run lint && npx tsc --noEmit
```

## Voice agent

The `agent/` directory contains the LiveKit voice agent. It handles missed-trash-pickup reports, demo schedule questions, existing cases, and resident-approved non-trash handoffs. It calls FastAPI over HTTP and never opens the SQLite database directly.

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

The agent uses six LLM tools: `create_case`, `lookup_case`, `update_case`, `lookup_service_schedule`, `create_service_request`, and `end_conversation`. Each application-data tool calls FastAPI over HTTP. If a backend call fails, the tool returns a safe error and the agent is instructed not to claim success.

## Known limitations

- This demo requires LiveKit Cloud credentials for LiveKit Inference; no provider keys are needed beyond those credentials.
- Schedule information is static demo data, not an authoritative municipal feed.
- Non-trash requests are recorded as handoffs; this demo does not route or transfer calls to another team.
- No authentication, production deployment, automated AI analysis, or telephony integration is included.

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

Open http://127.0.0.1:3000. The dashboard shows live calls, other-city handoffs, and cases. It polls FastAPI every three seconds and also refreshes after WebSocket notifications, so updates appear without a manual browser refresh.

## Case activity

Each new case receives a `CaseEvent` in SQLite. Later changes to status, notes, or description receive one event per field that actually changed. Events record a concise description, timestamp, source (`voice_agent`, `staff_dashboard`, or `api`), and old/new values when applicable.

The case detail page requests `GET /cases/{id}/events` every three seconds alongside the case itself. The voice agent sends `voice_agent` as source metadata and the dashboard sends `staff_dashboard` when it changes a status.

## Live calls and transcript

Starting a LiveKit session creates an active `Call` through `POST /calls`. The agent forwards finalized resident transcription from LiveKit's `user_input_transcribed` event and committed agent replies from `conversation_item_added` to `POST /calls/{id}/transcript`. When `create_case` succeeds, the agent links the call to its returned case ID and known name, phone, and issue type through `PATCH /calls/{id}`. The shutdown callback marks an active call completed and preserves its transcript.

When the resident clearly says they are finished, the agent records a farewell, marks that `Call` completed, and clears its conversational context without stopping the LiveKit session. The next finalized resident utterance creates a separate active `Call`, so a new “hello” starts a new request without reusing names, contact details, or prior case information. A service `Case` is still created only after a resident supplies the information needed to report a missed pickup.

The staff dashboard loads calls and transcripts through the REST API, using SQLite as the source of truth. It also opens `ws://127.0.0.1:8000/ws/calls`; FastAPI broadcasts small notifications after call, transcript, and case changes, and the dashboard refetches after each notification. Existing three-second polling remains as a reconnect/failure fallback.

## Demo service schedules

The voice agent can look up mock trash and recycling schedules through `GET /service-info/schedule?city=folsom`. The backend reads the data from `backend/app/data/service_schedules.json`; this is intentionally demo data, not real municipal service information. Sacramento, Folsom, El Dorado, Rancho Cordova, and Elk Grove are supported. City matching ignores casing and extra spacing. Unsupported cities return a clear `404` response rather than a guessed schedule.
