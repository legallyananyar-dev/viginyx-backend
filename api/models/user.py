from openai import BaseModel
from sqlmodel import Relationship
from enum import Enum
from uuid import uuid4
from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4
from datetime import datetime, timezone, date


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"
    CLINIC_ADMIN = "clinic_admin"
    CLINIC_USER = "clinic_user"
    
class UserType(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    

class UserBase(SQLModel):
    """
    Base user properties shared across different user models.
    """
    email: str = Field(unique=True, index=True)
    is_active: bool = True
    role: UserRole = Field(default=UserRole.USER)
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True
    )
    user_type: UserType = Field(default=UserType.PATIENT)
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)
    organization_id: UUID | None = Field(default=None, foreign_key="organizations.id")

class PharmacistThread(SQLModel, table=True):
    __tablename__ = "pharmacist_threads"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    thread_id: str = Field(unique=True, index=True, nullable=False, description="LangGraph execution thread id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

class NaranjoResult(SQLModel, table=True):
    __tablename__ = "naranjo_results"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    pharmacist_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    patient_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    thread_id: str = Field(index=True, nullable=False)
    naranjo_score: int = Field(default=0)
    naranjo_causality: str = Field(default="Unknown")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class OrganizationBase(SQLModel):
    id: UUID = Field(default_factory=uuid4,primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    license_no:str|None=Field(default=None)
    

class Organization(OrganizationBase, table=True):
    __tablename__ = "organizations"
    users: list["User"] = Relationship(back_populates="organization")

class UserCreate(UserBase):
    """
    Schema used to validate data when creating a new user.
    """
    password: str
    confirm_password: str

class UserRead(UserBase):
    """
    Schema used for returning user data via the API.
    """
    id: UUID

class UserUpdate(SQLModel):
    """
    Schema used for updating user data.
    """
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None

class User(UserBase, table=True):
    """
    The main database model representing a User in PostgreSQL.
    """
    __tablename__ = "users"
    hashed_password: str
    passkeys: list["Passkeys"] = Relationship(back_populates="user")
    organization: Organization | None = Relationship(back_populates="users")

class Token(SQLModel):
    """
    Schema used for the authentication token response.
    """
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

class TokenPayload(SQLModel):
    """
    Schema for decoding the contents of the JWT token.
    """
    sub: str | None = None

class PasskeyRead(SQLModel):
    """
    Schema for returning passkey info securely to the client.
    """
    id: UUID
    device_type: str | None
    created_at: datetime
    last_used_at: datetime | None

class Passkeys(SQLModel, table=True):
    """
    The main database model representing a Passkey in PostgreSQL.
    """
    __tablename__ = "passkeys"
    id: UUID = Field(default_factory=uuid4,primary_key=True)

    user_id: UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=False
    )

    credintial_id: str = Field( unique=True,
        index=True,
        nullable=False,
        description="Unique credential identifier from WebAuthn")

    public_key: str = Field(
        nullable=False,
        description="Public key used for verification."
    )

    device_type: str | None = Field(
        default=None,
        description="single_device or multi_device"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    last_used_at: datetime | None = Field(
        default=None
    )

    user: User = Relationship(
        back_populates="passkeys"
    )

class SessionData(BaseModel):
    user_id: UUID
    user_role:str