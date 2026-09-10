"""HTTP and WebSocket boundary for EffiGov cases, calls, and transcripts.

Route handlers keep persistence and validation at the API edge.  The voice agent
and staff dashboard use this module rather than accessing SQLite directly.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Call, Case, CaseEvent, ServiceRequest, TranscriptMessage
from .schemas import (
    CallCreate,
    CallRead,
    CallUpdate,
    CaseCreate,
    CaseEventRead,
    CaseRead,
    CaseUpdate,
    TranscriptMessageCreate,
    TranscriptMessageRead,
    ServiceScheduleRead,
    ServiceRequestCreate,
    ServiceRequestRead,
)


# SQLite is initialized lazily for this local demo; a migration system is out of scope.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Effigov Case API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DbSession = Annotated[Session, Depends(get_db)]


class CallConnectionManager:
    """Tracks dashboard sockets and emits best-effort refresh notifications.

    SQLite remains the source of truth.  Clients refetch after a notification and
    also poll, so dropping a disconnected socket cannot lose application data.
    """

    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, event_type: str, **data: object) -> None:
        message = {"type": event_type, **data}
        for websocket in self.connections.copy():
            try:
                await websocket.send_json(message)
            except Exception:
                # A failed send normally means the browser disconnected between
                # events; remove it without making the completed API request fail.
                self.disconnect(websocket)


call_connections = CallConnectionManager()

SCHEDULES_PATH = Path(__file__).parent / "data" / "service_schedules.json"
SERVICE_SCHEDULES = json.loads(SCHEDULES_PATH.read_text())
SUPPORTED_CITIES = ", ".join(schedule["city"] for schedule in SERVICE_SCHEDULES.values())


def get_case_or_404(case_id: int, db: Session) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def normalize_city(city: str) -> str:
    return " ".join(city.split()).casefold()


@app.get("/service-info/schedule", response_model=ServiceScheduleRead)
def get_service_schedule(city: str = Query(min_length=1)) -> dict[str, object]:
    schedule = SERVICE_SCHEDULES.get(normalize_city(city))
    if schedule is None:
        raise HTTPException(
            status_code=404,
            detail=f"Demo schedule information is available only for: {SUPPORTED_CITIES}.",
        )
    return {**schedule, "is_demo_data": True}


@app.post("/cases", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(payload: CaseCreate, db: DbSession) -> Case:
    last_id = db.scalar(select(func.max(Case.id))) or 0
    case = Case(
        case_number=f"EG-{1001 + last_id}",
        **payload.model_dump(exclude={"source"}),
    )
    db.add(case)
    db.flush()
    db.add(
        CaseEvent(
            case_id=case.id,
            event_type="created",
            description="Case created",
            source=payload.source,
        )
    )
    db.commit()
    db.refresh(case)
    await call_connections.broadcast("case_created", case_id=case.id)
    return case


@app.get("/cases", response_model=list[CaseRead])
def list_cases(db: DbSession) -> list[Case]:
    return list(db.scalars(select(Case).order_by(Case.created_at.desc(), Case.id.desc())))


@app.get("/cases/lookup", response_model=list[CaseRead])
def lookup_cases(
    db: DbSession,
    case_number: str | None = Query(default=None),
    phone: str | None = Query(default=None),
) -> list[Case]:
    if not case_number and not phone:
        raise HTTPException(status_code=400, detail="Provide case_number or phone")

    statement = select(Case)
    if case_number:
        statement = statement.where(Case.case_number == case_number)
    if phone:
        statement = statement.where(Case.phone == phone)
    return list(db.scalars(statement.order_by(Case.created_at.desc(), Case.id.desc())))


@app.get("/cases/{case_id}", response_model=CaseRead)
def get_case(case_id: int, db: DbSession) -> Case:
    return get_case_or_404(case_id, db)


@app.get("/cases/{case_id}/events", response_model=list[CaseEventRead])
def list_case_events(case_id: int, db: DbSession) -> list[CaseEvent]:
    get_case_or_404(case_id, db)
    statement = select(CaseEvent).where(CaseEvent.case_id == case_id)
    return list(db.scalars(statement.order_by(CaseEvent.created_at.desc(), CaseEvent.id.desc())))


@app.patch("/cases/{case_id}", response_model=CaseRead)
async def update_case(case_id: int, payload: CaseUpdate, db: DbSession) -> Case:
    case = get_case_or_404(case_id, db)
    updates = payload.model_dump(exclude_unset=True, exclude={"source"})
    did_change = False
    for field, value in updates.items():
        old_value = getattr(case, field)
        if old_value == value:
            continue
        setattr(case, field, value)
        did_change = True
        db.add(
            CaseEvent(
                case_id=case.id,
                event_type=f"{field}_updated",
                description=event_description(field, old_value, value),
                source=payload.source,
                old_value=old_value,
                new_value=value,
            )
        )
    db.commit()
    db.refresh(case)
    if did_change:
        await call_connections.broadcast("case_updated", case_id=case.id)
    return case


def event_description(field: str, old_value: str, new_value: str) -> str:
    if field == "status":
        return f"Status changed: {old_value} → {new_value}"
    if field == "notes":
        return "Notes updated"
    return "Description updated"


def get_call_or_404(call_id: int, db: Session) -> Call:
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


def call_read(call: Call, db: Session) -> CallRead:
    """Add the human-readable case number without exposing an ORM relationship."""
    response = CallRead.model_validate(call)
    if call.case_id is not None:
        case = db.get(Case, call.case_id)
        response.case_number = case.case_number if case else None
    return response


@app.post(
    "/service-requests", response_model=ServiceRequestRead, status_code=status.HTTP_201_CREATED
)
async def create_service_request(
    payload: ServiceRequestCreate, db: DbSession
) -> ServiceRequest:
    if payload.call_id is not None:
        get_call_or_404(payload.call_id, db)
    request = ServiceRequest(**payload.model_dump())
    db.add(request)
    db.commit()
    db.refresh(request)
    await call_connections.broadcast("service_request_created", service_request_id=request.id)
    return request


@app.get("/service-requests", response_model=list[ServiceRequestRead])
def list_service_requests(db: DbSession) -> list[ServiceRequest]:
    statement = select(ServiceRequest).order_by(
        ServiceRequest.created_at.desc(), ServiceRequest.id.desc()
    )
    return list(db.scalars(statement))


@app.post("/calls", response_model=CallRead, status_code=status.HTTP_201_CREATED)
async def create_call(payload: CallCreate, db: DbSession) -> CallRead:
    call = Call(status=payload.status)
    db.add(call)
    db.commit()
    db.refresh(call)
    response = call_read(call, db)
    await call_connections.broadcast("call_started", call_id=call.id)
    return response


@app.get("/calls", response_model=list[CallRead])
def list_calls(db: DbSession) -> list[CallRead]:
    calls = db.scalars(select(Call).order_by(Call.started_at.desc(), Call.id.desc()))
    return [call_read(call, db) for call in calls]


@app.get("/calls/{call_id}", response_model=CallRead)
def get_call(call_id: int, db: DbSession) -> CallRead:
    return call_read(get_call_or_404(call_id, db), db)


@app.get("/calls/{call_id}/transcript", response_model=list[TranscriptMessageRead])
def list_transcript_messages(call_id: int, db: DbSession) -> list[TranscriptMessage]:
    get_call_or_404(call_id, db)
    statement = select(TranscriptMessage).where(TranscriptMessage.call_id == call_id)
    return list(db.scalars(statement.order_by(TranscriptMessage.created_at, TranscriptMessage.id)))


@app.post(
    "/calls/{call_id}/transcript",
    response_model=TranscriptMessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_transcript_message(
    call_id: int, payload: TranscriptMessageCreate, db: DbSession
) -> TranscriptMessage:
    get_call_or_404(call_id, db)
    message = TranscriptMessage(call_id=call_id, **payload.model_dump())
    db.add(message)
    db.commit()
    db.refresh(message)
    await call_connections.broadcast("transcript_added", call_id=call_id)
    return message


@app.patch("/calls/{call_id}", response_model=CallRead)
async def update_call(call_id: int, payload: CallUpdate, db: DbSession) -> CallRead:
    call = get_call_or_404(call_id, db)
    updates = payload.model_dump(exclude_unset=True)
    if "case_id" in updates and updates["case_id"] is not None:
        get_case_or_404(updates["case_id"], db)

    for field, value in updates.items():
        setattr(call, field, value)
    if updates.get("status") == "completed" and call.ended_at is None:
        call.ended_at = datetime.utcnow()

    db.commit()
    db.refresh(call)
    response = call_read(call, db)
    event_type = "call_ended" if call.status == "completed" else "call_updated"
    await call_connections.broadcast(event_type, call_id=call.id)
    return response


@app.websocket("/ws/calls")
async def call_updates(websocket: WebSocket) -> None:
    """Keep a dashboard socket open for refresh hints; it carries no case data."""
    await call_connections.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        call_connections.disconnect(websocket)
