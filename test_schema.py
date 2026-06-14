from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None

try:
    APIResponse[dict[str, str]](data=None)
    print("OK")
except Exception as e:
    print("Error:", e)
