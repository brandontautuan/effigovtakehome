# Code Quality, Documentation, and Maintenance Rules

You are responsible for keeping the implementation, comments, README, and tests accurate throughout the entire EffiGov take-home—not only at the end.

The goal is to ship a functional, understandable demo under time constraints. Prefer simple, reliable architecture and a complete end-to-end workflow over unnecessary abstraction or production-scale complexity.

## 1. Understand Before Changing

Before modifying code:

* Inspect the existing project structure and relevant files.
* Identify the current architecture, data flow, scripts, and test commands.
* Reuse existing patterns and utilities where possible.
* Do not introduce a new framework, dependency, abstraction, or service unless it is necessary and justified.
* Preserve existing working behavior unless the task explicitly requires changing it.
* Keep the implementation appropriate for a three-hour take-home. Avoid building infrastructure that does not materially improve the demo.

Before making LiveKit, voice-agent, or AI-analysis changes:

* Verify the relevant LiveKit API, SDK behavior, event shape, authentication requirements, and required environment variables from available documentation.
* Do not guess API fields or silently invent behavior.
* Keep LiveKit-specific logic isolated behind a clear service, agent, or integration module.
* Keep LLM-provider-specific logic isolated from ticket and application logic.

The intended application flow is:

```text
Resident
  → Voice Agent
  → LiveKit Session
  → Backend
  → Transcript / Call Data
  → AI Analysis Agent
  → Structured Service Request
  → SQLite
  → Employee Case Dashboard
```

## 2. Scope and Priorities

Prioritize the core EffiGov workflow:

1. A resident can interact with a voice agent.
2. The conversation produces usable transcript or call data.
3. The backend receives and processes the completed interaction.
4. An AI analysis step converts the conversation into structured ticket data.
5. The ticket is stored in SQLite.
6. An employee can view the ticket in the Next.js dashboard.
7. An employee can inspect enough information to understand and triage the case.

Favor a working vertical slice over broad but incomplete functionality.

Features outside this flow should only be added after the core workflow works.

## 3. Code Quality

Write code that is:

* Clear and readable without requiring extensive explanation.
* Organized around sensible responsibilities.
* Small enough to test and reason about.
* Consistent with the existing language and project conventions.
* Explicit about error cases and unavailable data.
* Typed where the project supports types.
* Free of unused imports, dead code, unexplained magic values, and unnecessary duplication.

Use descriptive names.

Avoid vague names such as:

```text
data
result
thing
process
handleStuff
```

when a more precise name is available.

Prefer names such as:

```text
service_request
call_transcript
resident_message
ticket_analysis
ticket_repository
livekit_session
```

Prefer simple control flow. If a function becomes difficult to understand, split it into smaller functions with clear responsibilities.

Do not hide important behavior in overly clever abstractions.

## 4. Architecture and Boundaries

Keep major responsibilities separated.

The application should have clear boundaries for:

* Voice-agent behavior.
* LiveKit session handling.
* Backend API routes.
* Transcript or call-event processing.
* AI analysis.
* Ticket persistence.
* Ticket retrieval and updates.
* Frontend presentation.

A reasonable structure might resemble:

```text
frontend/
  Next.js application

backend/
  api/
  services/
  models/
  repositories/
  agents/
  tests/
```

Do not create layers purely for architectural appearance. Add separation where it improves clarity, testing, or maintainability.

## 5. LiveKit and Voice-Agent Integration

Keep LiveKit-specific logic isolated from general application logic.

The LiveKit boundary should be responsible for things such as:

* Creating or joining voice sessions.
* Authenticating participants.
* Running the resident-facing voice agent.
* Receiving speech or transcript events.
* Handling session completion.
* Translating LiveKit events into the application's internal representation.

Do not pass raw LiveKit event objects throughout the entire application.

Normalize external events before passing them into application logic.

Handle reasonable failure cases, including:

* Missing environment variables.
* Invalid session configuration.
* Connection failures.
* Unexpected disconnects.
* Empty conversations.
* Missing transcript information.
* Duplicate events where applicable.

Never expose LiveKit API secrets, private keys, or backend credentials to the browser.

Frontend code may only receive credentials intended for client-side use.

## 6. Backend API Boundaries

The FastAPI backend should provide a clear interface between the frontend, voice workflow, AI analysis, and persistence layer.

Keep route handlers small.

Route handlers should primarily:

1. Validate input.
2. Call application or service logic.
3. Return a defined response model.
4. Translate expected errors into appropriate HTTP responses.

Avoid placing transcript parsing, LLM prompting, or database logic directly inside route handlers.

Use typed request and response models where practical.

Validate incoming data before storing or analyzing it.

Return explicit errors rather than silently failing.

## 7. Ticket Data Model

Use a defined internal schema for service requests.

At minimum, consider fields such as:

```text
id
created_at
updated_at
status
category
summary
description
location
priority
resident_name
resident_contact
transcript
```

Only include fields that are actually useful to the demo.

AI-generated fields should be distinguishable from raw source evidence.

The data model should support the primary dashboard workflow without unnecessary complexity.

A ticket should remain usable even when some resident information is unavailable.

## 8. AI Analysis

Treat LLM output as untrusted application data.

The AI analysis agent should convert the conversation into a defined structured schema.

Potential generated fields include:

* Service-request category.
* Short summary.
* Detailed description.
* Location.
* Priority or urgency.
* Resident contact information, if provided.
* Additional notes useful for triage.

Validate the returned structure before storing or rendering it.

Use a typed schema, such as a Pydantic model, for generated output.

Handle:

* Invalid JSON.
* Missing fields.
* Empty responses.
* Unexpected categories.
* Unsupported priority values.
* Provider/API failures.
* Timeouts.

Do not present unsupported inferences as confirmed facts.

For example, if the resident never provides an address, the model must not invent one.

Prefer `null`, `unknown`, or equivalent explicit missing values instead.

Preserve the original transcript so employees can distinguish source evidence from generated interpretation.

## 9. Transcript and Evidence Handling

Preserve the source conversation whenever possible.

Transcript entries should retain available evidence such as:

```text
speaker
timestamp
text
```

Example:

```json
{
  "speaker": "resident",
  "timestamp": 18.4,
  "text": "There is a large pothole outside 123 Main Street."
}
```

If exact timestamps are not available, do not fabricate them.

Make clear which information came directly from the resident and which information was generated by the AI analysis agent.

Generated summaries should never replace the original transcript.

## 10. Database and Persistence

SQLite is sufficient for the take-home unless a different database is already configured.

Keep database operations separate from route and UI logic.

The persistence layer should support the operations required by the demo, such as:

* Create a ticket.
* List tickets.
* Retrieve a ticket.
* Update ticket status.

Avoid unnecessary database abstractions.

Use migrations if the chosen stack already supports them easily. Otherwise, a simple, clearly documented SQLite initialization approach is acceptable for the demo.

Do not store secrets in the database.

## 11. Ticket Status and Triage

Keep ticket workflow simple.

A minimal status model could be:

```text
new
in_progress
resolved
```

Only introduce more statuses if the UI actually uses them.

Employees should be able to quickly understand:

* What happened.
* Where it happened.
* How urgent it appears.
* What the resident said.
* Whether the case has been triaged.

AI-generated priority should be treated as a recommendation, not unquestionable truth.

## 12. Frontend Dashboard

The Next.js frontend should prioritize usability over visual polish.

At minimum, the dashboard should make it possible to:

* View existing service requests.
* See important ticket metadata.
* Select a ticket.
* Inspect its AI-generated summary.
* Inspect the original transcript.
* Understand the current ticket status.

If implemented, status updates or triage controls should clearly reflect backend state.

Handle frontend states explicitly:

* Loading.
* Empty database.
* API error.
* Missing optional information.

Do not crash because a generated field is unavailable.

Avoid exposing backend secrets through `NEXT_PUBLIC_*` environment variables.

## 13. Comments

Comments should explain intent, constraints, or non-obvious decisions—not restate what the code already says.

Good comments explain:

* Why a LiveKit event is normalized.
* Why transcript events are deduplicated.
* Why AI output is validated before storage.
* Why a ticket field can be missing.
* What assumption is made about speaker roles.
* Why a simplified architecture was chosen for the take-home.
* What is intentionally out of scope.

Avoid comments such as:

```text
// Set ticket status to resolved
ticket.status = "resolved";
```

Do not leave stale comments.

Whenever behavior changes, update or remove comments that no longer describe the implementation.

Use TODO comments only when they describe a specific, actionable follow-up.

Avoid vague TODOs such as:

```text
TODO: improve this
TODO: fix later
```

## 14. Error Handling

Handle expected errors explicitly.

Relevant cases include:

* LiveKit connection failures.
* Missing transcript information.
* Invalid API input.
* Database errors.
* LLM API failures.
* Malformed LLM output.
* Ticket not found.
* Missing environment configuration.

User-facing errors should be understandable without leaking implementation details or secrets.

Backend logs may contain useful diagnostic information but must never include API keys, tokens, or sensitive credentials.

## 15. Tests and Verification

Add or update tests for meaningful behavior changes.

Given the take-home time constraint, prioritize tests around important application logic rather than exhaustive coverage.

At minimum, test where practical:

* Ticket creation.
* Invalid API input.
* Ticket retrieval.
* Ticket status updates.
* Transcript parsing.
* Speaker mapping.
* AI output validation.
* Empty AI responses.
* Malformed AI responses.
* Missing transcript data.
* Database behavior.
* Relevant LiveKit event normalization or integration logic.

Prefer deterministic tests with mocked LiveKit and LLM responses.

Do not make the default test suite depend on:

* A live LiveKit account.
* A live LLM API.
* A browser window.
* An interactive prompt.
* External network access.

If live integration tests exist, label them separately.

Before declaring a meaningful milestone complete:

* Run the project's automated test suite headlessly.
* Run linting if configured.
* Run formatting checks if configured.
* Run type checking if configured.
* Verify the relevant backend endpoint manually where useful.
* Verify the main frontend flow where practical.

If no test, lint, formatting, or type-check command exists, report that explicitly instead of inventing one.

Report exact verification commands and their results.

## 16. README Requirements

Keep the README updated as implementation changes.

The README must accurately describe:

* What the application does.
* The EffiGov use case.
* The target users.
* The resident workflow.
* The employee workflow.
* The architecture and data flow.
* How LiveKit is used.
* How AI analysis is performed.
* How tickets are stored.
* Required environment variables.
* How to install dependencies.
* How to start the backend.
* How to start the frontend.
* How to start the voice agent.
* How to run tests.
* How to run linting or type checks.
* How to use demo or mock mode, if implemented.
* Known limitations.
* Future improvements.

Include a concise architecture diagram such as:

```text
Resident
  ↓
LiveKit Voice Agent
  ↓
Transcript / Call Events
  ↓
FastAPI Backend
  ↓
AI Analysis Agent
  ↓
Structured Service Request
  ↓
SQLite
  ↓
Next.js Employee Dashboard
```

Do not claim that features work if they have not been verified.

Do not describe planned functionality as completed functionality.

If a command, endpoint, environment variable, data model, or setup step changes, update the README in the same change.

## 17. Environment Variables and Secrets

Document required environment variables in `.env.example`.

Possible examples include:

```text
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

OPENAI_API_KEY=

DATABASE_URL=
NEXT_PUBLIC_API_URL=
```

Only include variables actually used by the application.

Never commit real credentials.

Never copy real credentials into:

* README files.
* Screenshots.
* Source code.
* Example requests.
* Tests.
* Client-side bundles.

Use placeholder values in documentation.

## 18. Change Management

Keep changes focused on the requested feature.

Do not:

* Rewrite unrelated files.
* Reformat the entire repository unnecessarily.
* Add dependencies without explaining why.
* Remove working behavior without justification.
* Commit generated secrets or local credentials.
* Leave temporary debug files.
* Add production infrastructure that is unnecessary for the demo.
* Over-engineer abstractions for hypothetical future requirements.

After each meaningful milestone, re-check:

* The backend still starts.
* The frontend still starts.
* Tests still pass.
* The README still matches the project.
* The current user-facing flow still works.

## 19. Time-Constrained Engineering

This is a take-home demo, not a production municipal deployment.

Make implementation decisions accordingly.

Prefer:

```text
Simple > Clever
Working > Over-engineered
Explicit > Abstract
End-to-end > Feature-complete
Verified > Claimed
```

When choosing between additional polish and completing the resident-to-ticket workflow, complete the workflow first.

Acceptable simplifications should be documented in the README under known limitations.

Potential examples include:

* SQLite instead of a production database.
* Local development instead of cloud deployment.
* Limited authentication.
* Simplified ticket statuses.
* Mock fallback for unavailable external services.
* Limited concurrency.
* Minimal dashboard styling.

Do not hide these limitations. Explain them briefly and clearly.

## 20. Definition of Done

Before finishing, confirm:

* [ ] A resident can interact with the voice-agent flow.
* [ ] Conversation data reaches the backend.
* [ ] Transcript or equivalent source evidence is preserved.
* [ ] AI analysis produces schema-validated structured data.
* [ ] AI-generated fields do not invent unavailable resident information.
* [ ] A ticket is persisted in SQLite.
* [ ] The frontend can retrieve and display tickets.
* [ ] Employees can inspect the generated analysis.
* [ ] Employees can inspect the original transcript.
* [ ] Relevant error states are handled.
* [ ] LiveKit-specific logic is isolated.
* [ ] LLM-specific logic is isolated.
* [ ] Backend APIs use defined request and response models.
* [ ] Tests cover the most important success and failure paths.
* [ ] Formatting, linting, and type checks pass where configured.
* [ ] README instructions match the current implementation.
* [ ] Environment variables are documented without exposing secrets.
* [ ] Known limitations are clearly documented.
* [ ] No unrelated files, secrets, or temporary artifacts were added.

## 21. Completion Report

When reporting completion, summarize:

1. **What changed**

   * Describe the implemented user-facing and backend behavior.

2. **Files changed**

   * List the relevant files and their responsibilities.

3. **What was verified**

   * Include exact commands and their results.

Example:

```text
uv run pytest
PASS — 14 tests

uv run ruff check .
PASS

npm run lint
PASS

npm run build
PASS
```

4. **Manual verification**

   * Describe which part of the resident → ticket → dashboard workflow was tested.

5. **Remaining limitations**

   * Clearly distinguish incomplete, mocked, or unverified functionality.

6. **Important implementation decisions**

   * Briefly explain meaningful tradeoffs made because of the take-home time constraint.

Never report a feature as complete unless the implemented behavior and verification support that claim.
