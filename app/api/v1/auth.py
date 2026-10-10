"""
app/api/v1/auth.py
------------------
Authentication endpoints: login (token issuance).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.services.employee_service import get_employee_by_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee_id: int
    role: str


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Obtain a JWT access token",
    description=(
        "Authenticate with email (username field) and password. "
        "Returns a Bearer token that must be included in subsequent requests."
    ),
)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    employee = get_employee_by_email(db, form.username)
    if not employee or not verify_password(form.password, employee.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    token = create_access_token(
        subject=employee.id,
        extra_claims={"role": employee.role, "email": employee.email},
    )
    return TokenResponse(
        access_token=token,
        employee_id=employee.id,
        role=employee.role,
    )
