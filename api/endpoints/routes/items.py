from typing import Annotated
from fastapi import APIRouter, Path, Query
from api.models.item import Item, ItemCreate
from api.endpoints.deps import CurrentUserDep
from api.schemas.response import APIResponse

# Applying tags/prefix at the router level
router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=APIResponse[Item])
async def create_item(item: ItemCreate, current_user: CurrentUserDep):
    # Example logic
    return APIResponse(data=Item(id=1, **item.model_dump()))

@router.get("/{item_id}", response_model=APIResponse[Item])
async def read_item(
    item_id: Annotated[int, Path(ge=1, description="The item ID")],
    current_user: CurrentUserDep,
    q: Annotated[str | None, Query(max_length=50)] = None,
):
    return APIResponse(data=Item(id=item_id, name="Test Item", price=10.5))
