from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=50)
    issue_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    source: str = Field(default="api", max_length=50)


class CaseUpdate(BaseModel):
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
