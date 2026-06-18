"""Pydantic schemas (API contract)."""
from datetime import date
from pydantic import BaseModel, ConfigDict


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ref: str
    title: str
    agency: str
    market: str
    vehicle: str
    cpv: str
    value: int
    close: date | None
    incumbent: str
    region: str
    desc: str
    source: str


class AwardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ref: str
    title: str
    agency: str
    vendor: str
    value: int
    vehicle: str
    co: str
    date: date | None


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    score: int
    title: str
    body: str
    tags: list[str]
    when: str


class PursuitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    opportunity_id: str
    stage: str
    position: int


class MoveRequest(BaseModel):
    opportunity_id: str
    stage: str


class WorkflowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    enabled: bool
    steps: list


class WorkflowToggle(BaseModel):
    enabled: bool


class AgentRequest(BaseModel):
    question: str


class AgentResponse(BaseModel):
    answer: str
    provider: str


class Summary(BaseModel):
    pipeline_value: int
    active_pursuits: int
    closing_this_week: int
    signals: int
    high_signals: int


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: str
    active: bool


class UserCreate(BaseModel):
    email: str
    name: str = ""
    password: str
    role: str = "analyst"


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ts: object
    actor: str
    action: str
    target: str
    detail: dict
    ip: str
