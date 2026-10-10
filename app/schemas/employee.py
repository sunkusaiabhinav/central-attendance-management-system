"""
app/schemas/employee.py
-----------------------
Pydantic schemas for Employee CRUD and authentication.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmployeeCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    department: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="EMPLOYEE")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("ADMIN", "EMPLOYEE"):
            raise ValueError("role must be 'ADMIN' or 'EMPLOYEE'")
        return v


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    department: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class EmployeeStatusUpdate(BaseModel):
    is_active: bool


class EmployeePasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class EmployeeResponse(BaseModel):
    id: int
    full_name: str
    email: str
    department: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    employees: list[EmployeeResponse]
