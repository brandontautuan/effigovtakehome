"""Pydantic contracts at the API boundary.

These schemas validate external input before persistence and prevent ORM internals
from leaking into the voice agent or dashboard responses.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    """Required resident information for a new service case."""

    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=50)
    issue_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    source: str = Field(default="api", max_length=50)


class CaseUpdate(BaseModel):
    """Partial staff or agent update; ``source`` is retained for the audit event."""

    status: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = None
    description: str | None = Field(default=None, min_length=1)
    source: str = Field(default="api", max_length=50)


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_number: str
    name: str
    phone: str
    issue_type: str
    description: str
    status: str
    notes: str
    created_at: datetime
    updated_at: datetime


class CaseEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    event_type: str
    description: str
    source: str
    old_value: str | None
    new_value: str | None
    created_at: datetime


class CallCreate(BaseModel):
    """Initial state for a new voice call record."""

    status: str = "active"


class CallUpdate(BaseModel):
    """Information collected over a call as it becomes available."""

    case_id: int | None = None
    status: str | None = None
    caller_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    issue_type: str | None = Field(default=None, max_length=100)


class CallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int | None
    case_number: str | None = None
    status: str
    caller_name: str | None
    phone: str | None
    issue_type: str | None
    started_at: datetime
    ended_at: datetime | None


class TranscriptMessageCreate(BaseModel):
    """One non-empty, finalized utterance from a known conversation role."""

    role: Literal["resident", "agent"]
    content: str = Field(min_length=1)


class TranscriptMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    call_id: int
    role: Literal["resident", "agent"]
    content: str
    created_at: datetime


class ServiceTime(BaseModel):
    day: str
    time: str


class ServiceScheduleRead(BaseModel):
    city: str
    trash: ServiceTime
    recycling: ServiceTime
    is_demo_data: bool = True
