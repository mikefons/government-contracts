"""Authentication & authorisation: bcrypt hashing, JWT, RBAC dependencies."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from . import models as m

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ROLES = ("admin", "analyst", "viewer")
ROLE_RANK = {"viewer": 0, "analyst": 1, "admin": 2}


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(sub: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


def current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> m.User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    payload = _decode(token)
    user = db.scalar(select(m.User).where(m.User.email == payload.get("sub")))
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def require_role(minimum: str):
    """Dependency factory: caller must hold `minimum` role or higher."""
    floor = ROLE_RANK[minimum]

    def checker(user: m.User = Depends(current_user)) -> m.User:
        if ROLE_RANK.get(user.role, -1) < floor:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"Requires '{minimum}' role or higher")
        return user

    return checker
