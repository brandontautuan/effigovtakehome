from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Case, CaseEvent
from .schemas import CaseCreate, CaseEventRead, CaseRead, CaseUpdate


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


def get_case_or_404(case_id: int, db: Session) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.post("/cases", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, db: DbSession) -> Case:
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
def update_case(case_id: int, payload: CaseUpdate, db: DbSession) -> Case:
    case = get_case_or_404(case_id, db)
    updates = payload.model_dump(exclude_unset=True, exclude={"source"})
    for field, value in updates.items():
        old_value = getattr(case, field)
        if old_value == value:
            continue
        setattr(case, field, value)
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
    return case


def event_description(field: str, old_value: str, new_value: str) -> str:
    if field == "status":
        return f"Status changed: {old_value} → {new_value}"
    if field == "notes":
        return "Notes updated"
    return "Description updated"
