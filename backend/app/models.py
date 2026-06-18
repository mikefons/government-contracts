"""ORM models for the Chancery procurement-intelligence platform."""
from datetime import date, datetime
from sqlalchemy import String, Integer, BigInteger, Date, DateTime, Boolean, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    ref: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    agency: Mapped[str] = mapped_column(String, index=True)
    market: Mapped[str] = mapped_column(String, index=True)   # Federal | SLED | EU
    vehicle: Mapped[str] = mapped_column(String, index=True)
    cpv: Mapped[str] = mapped_column(String, default="")
    value: Mapped[int] = mapped_column(BigInteger, default=0)
    close: Mapped[date | None] = mapped_column(Date, nullable=True)
    incumbent: Mapped[str] = mapped_column(String, default="None (new requirement)")
    region: Mapped[str] = mapped_column(String, default="")
    desc: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String, default="seed")  # seed | find-a-tender | contracts-finder
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Award(Base):
    __tablename__ = "awards"
    ref: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    agency: Mapped[str] = mapped_column(String, index=True)
    vendor: Mapped[str] = mapped_column(String, index=True)
    value: Mapped[int] = mapped_column(BigInteger, default=0)
    vehicle: Mapped[str] = mapped_column(String)
    co: Mapped[str] = mapped_column(String, default="")        # contracting officer
    date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score: Mapped[int] = mapped_column(Integer, default=50)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    when: Mapped[str] = mapped_column(String, default="")


class Pursuit(Base):
    """An opportunity placed on the capture board at a given stage."""
    __tablename__ = "pursuits"
    opportunity_id: Mapped[str] = mapped_column(String, primary_key=True)
    stage: Mapped[str] = mapped_column(String, index=True)     # Identify..Submitted
    position: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    steps: Mapped[list] = mapped_column(JSON, default=list)    # [["trig","..."],["","..."]]


class SavedSearch(Base):
    __tablename__ = "saved_searches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    query: Mapped[dict] = mapped_column(JSON, default=dict)
    alert: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="analyst")  # admin|analyst|viewer
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    """Append-only record of who did what. Never updated or deleted in app code."""
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    actor: Mapped[str] = mapped_column(String, index=True)   # user email or "system"
    action: Mapped[str] = mapped_column(String, index=True)  # e.g. board.move
    target: Mapped[str] = mapped_column(String, default="")  # affected entity id
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str] = mapped_column(String, default="")


class VendorOntology(Base):
    """Persisted vendor ontology so the intel engine is stateless across invocations."""
    __tablename__ = "vendor_ontology"
    company: Mapped[str] = mapped_column(String, primary_key=True)   # lower-cased key
    display_name: Mapped[str] = mapped_column(String, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
