"""Append-only audit logging."""
from sqlalchemy.orm import Session
from . import models as m


def record(db: Session, actor: str, action: str, target: str = "", detail: dict | None = None, ip: str = "") -> None:
    db.add(m.AuditLog(actor=actor, action=action, target=target, detail=detail or {}, ip=ip))
    db.commit()
