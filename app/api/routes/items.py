from typing import Annotated
from fastapi import APIRouter, Path, Query
from app.models.item import Item, ItemCreate
from app.api.deps import CurrentUserDep

# Applying tags/prefix at the router level
router = APIRouter(prefix="/items", tags=["items"])

@router.post("/")
async def create_item(item: ItemCreate, current_user: CurrentUserDep) -> Item:
    # Example logic
    return Item(id=1, **item.model_dump())

@router.get("/{item_id}")
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
    current_user: CurrentUserDep,
    q: Annotated[str | None, Query(max_length=50)] = None,
) -> Item:
    return Item(id=item_id, name="Test Item", price=10.5)
