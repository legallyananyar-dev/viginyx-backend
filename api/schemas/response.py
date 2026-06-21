from typing import Generic, TypeVar, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationMeta(BaseModel):
    """
    Standard pagination metadata structure.
    """
    total_items: int
    total_pages: int
    current_page: int
    page_size: int

class APIResponse(BaseModel, Generic[T]):
    """
    Generic standard response structure for all success API responses.
    Works with single models, lists, dicts, or any data type via the Generic type T.
    """
    success: bool = Field(default=True, description="Indicates if the API request was successful")
    message: str = Field(default="Request successful", description="A human-readable success message")
    data: T | None = Field(default=None, description="The actual data payload of the response")
    meta: PaginationMeta | dict[str, Any] | None = Field(
        default=None, 
        description="Optional metadata, commonly used for pagination or additional context"
    )

class APIErrorResponse(BaseModel):
    """
    Generic standard response structure for all error API responses.
    """
    success: bool = Field(default=False, description="Indicates if the API request was successful")
    error_code: str | int = Field(default="ERROR", description="A machine-readable error code")
    message: str = Field(..., description="A human-readable error message")
    details: Any | None = Field(default=None, description="Additional error details, such as validation field errors")

class LoginRequest(BaseModel):
    username: str
    password: str
    