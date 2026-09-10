# EffiGov staff dashboard

This Next.js application is the staff view for EffiGov. It reads cases, call transcripts, and resident-approved handoff requests from the FastAPI backend; it does not access SQLite or LiveKit directly.

## Run locally

Start the FastAPI backend first, then configure the optional API URL override:

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

The dashboard polls the API every three seconds and also listens to `/ws/calls` for refresh notifications. REST responses remain the source of truth.

## Checks

```bash
npm run lint
npx tsc --noEmit
npm run build
```

The dashboard intentionally provides no authentication in this local take-home demo.
