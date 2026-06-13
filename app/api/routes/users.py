from fastapi import APIRouter, HTTPException, status
from typing import Any
from uuid import UUID

from app.core.database import ReadSessionDep, WriteSessionDep
from app.api.deps import SuperAdminDep
from app.models.user import UserCreate, UserRead, UserUpdate
from app.services.user import user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=list[UserRead])
def get_users(
    session: ReadSessionDep,
    current_user: SuperAdminDep,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve users. Only SUPER_ADMIN can perform this.
    """
    users = user_service.get_multi(session, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    session: ReadSessionDep,
    current_user: SuperAdminDep
) -> Any:
    """
    Get a specific user by ID. Only SUPER_ADMIN can perform this.
    """
    user = user_service.get_by_id(session, user_id=str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    *,
    session: WriteSessionDep,
    current_user: SuperAdminDep,
    user_in: UserCreate
) -> Any:
    """
    Create a new user. Only SUPER_ADMIN can perform this.
    """
    user = user_service.get_by_email(session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    if user_in.password != user_in.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )
    user = user_service.create(session, obj_in=user_in)
    return user

@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    *,
    session: WriteSessionDep,
    user_id: UUID,
    user_in: UserUpdate,
    current_user: SuperAdminDep
) -> Any:
    """
    Update a user. Only SUPER_ADMIN can perform this.
    """
    user = user_service.get_by_id(session, user_id=str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_in.email and user_in.email != user.email:
        existing_user = user_service.get_by_email(session, email=user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists in the system.",
            )
            
    user = user_service.update(session, db_obj=user, obj_in=user_in)
    return user

@router.delete("/{user_id}", response_model=UserRead)
def delete_user(
    *,
    session: WriteSessionDep,
    user_id: UUID,
    current_user: SuperAdminDep
) -> Any:
    """
    Delete a user. Only SUPER_ADMIN can perform this.
    """
    user = user_service.get_by_id(session, user_id=str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Super admins cannot delete themselves.")
        
    user = user_service.remove(session, id=user.id)
    return user
