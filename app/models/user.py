from sqlmodel import Relationship
from enum import Enum
from uuid import uuid4
from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4
from datetime import datetime, timezone


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    
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

class UserCreate(UserBase):
    """
    Schema used to validate data when creating a new user.
    """
    password: str

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
        