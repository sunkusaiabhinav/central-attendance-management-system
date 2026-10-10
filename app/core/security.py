"""
app/core/security.py
--------------------
Password hashing, JWT creation and validation, and dependency helpers for
protected route injection (current user, admin guard).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

settings = get_settings()

import bcrypt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ── Password Hashing ─────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    pwd_bytes = plain.encode("utf-8")
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pwd_bytes = plain.encode("utf-8")
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT ──────────────────────────────────────────────────────────────────────
def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT.

    Parameters
    ----------
    subject:
        Typically the employee's primary-key ID (as a string).
    extra_claims:
        Additional claims to embed (e.g. role).
    expires_delta:
        Token lifetime; defaults to ``ACCESS_TOKEN_EXPIRE_MINUTES``.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT; raises HTTPException on failure."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── Route Dependencies ────────────────────────────────────────────────────────
def get_current_employee(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Dependency that resolves and returns the authenticated Employee ORM object.
    Raises 401 if the token is invalid or the employee no longer exists.
    """
    from app.models.employee import Employee  # avoid circular import at module level

    payload = decode_access_token(token)
    employee_id_str: str | None = payload.get("sub")
    if not employee_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    try:
        employee_id = int(employee_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    employee = db.get(Employee, employee_id)
    if employee is None or not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee not found or deactivated",
        )
    return employee


def require_admin(current_employee=Depends(get_current_employee)):
    """
    Dependency that ensures the authenticated user has the ADMIN role.
    Raises 403 otherwise.
    """
    if current_employee.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_employee
