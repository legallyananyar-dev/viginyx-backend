from pydantic import BaseModel, Field

class ItemBase(BaseModel):
    name: str
    description: str | None = None

class ItemCreate(ItemBase):
    price: float = Field(gt=0)

class Item(ItemBase):
    id: int
    price: float
