from typing import Annotated
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUserDep
from app.core.database import ReadSessionDep, WriteSessionDep
from app.core import security
from app.core.config import settings
from app.models.user import User, UserCreate, UserRead, Token
from webauthn import generate_registration_options

from app.services.user import user_service

router = APIRouter(tags=["auth"])

@router.post("/login/access-token")
async def login_access_token(
    session: ReadSessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login endpoint. 
    It receives form-encoded credentials (username and password), validates them against the database, 
    and returns a JWT access token.
    
    TODO: Implement logic using user_service.get_by_email(session, email=form_data.username).
    """
    pass

@router.post("/login/refresh-token")
async def refresh_access_token(
    session: ReadSessionDep, refresh_token: str
) -> Token:
    """
    Receives a refresh token and returns a new access token if the refresh token is valid.
    
    TODO: Implement token decoding, validation, and generation of a new access token.
    """
    pass

@router.post("/signup", response_model=UserRead)
async def signup(session: WriteSessionDep, user_in: UserCreate) -> UserRead:
    """
    Creates a new user in the database.
    Checks if the email is already registered and hashes the password securely.
    """
    # 1. Check if user already exists
    existing_user = user_service.get_by_email(session, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    # 2. Call the service to create the user in the database
    new_user = user_service.create(session, obj_in=user_in)
    
    return new_user

@router.post("/test-token", response_model=UserRead)
async def test_token(current_user: CurrentUserDep) -> UserRead:
    """
    Test endpoint to verify if the provided bearer token is valid.
    Returns the user data of the authenticated user.
    
    TODO: Return the current_user object.
    """
    pass

@router.post('/register-passkey',response_model=UserRead)
async def register_passkey(current_user: CurrentUserDep):
    try:
        options = generate_registration_options(
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            user_id=str(current_user.id),
            user_name=str(current_user.email)
            )
        return options
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating registration options: {str(e)}"
        )


    