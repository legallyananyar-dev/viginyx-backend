from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from uuid import UUID, uuid4
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
from api.models.user import User


class ADRBase(SQLModel):
    drug_name: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    symptoms: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    naranjo_score: int = Field(default=0)
    dpdp_score: int = Field(default=0)
    overall_score: int = Field(default=0)
    severity: str = Field(default="Unknown")
    
    reported_by_id: UUID = Field(foreign_key="users.id", nullable=False)
    patient_id: UUID = Field(foreign_key="users.id", nullable=False)
    
    # Store thread_id for workflow correlation
    thread_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReadADR(ADRBase):
    id: UUID
    reported_by: User
    patient: User
    
class CreateADR(ADRBase, table=True):
    __tablename__ = "adr_reports"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)

