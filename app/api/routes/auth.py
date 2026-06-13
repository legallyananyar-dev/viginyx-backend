import jwt
from datetime import datetime, timezone, timedelta
from app.core.security import verify_password, ALGORITHM
from app.schemas.response import LoginRequest
from app.core.security import create_refresh_token
from app.core.security import create_access_token
from fastapi import Response, Request
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep
from app.core.database import ReadSessionDep, WriteSessionDep
from app.core.config import settings
from app.models.user import User, UserCreate, UserRead, Token, TokenPayload
from webauthn import generate_registration_options

from app.services.user import user_service

router = APIRouter(tags=["auth"])

@router.post("/login",response_model=UserRead)
async def login_access_token(
    session: ReadSessionDep, login_request: LoginRequest,response:Response
) -> UserRead:
    """
    OAuth2 compatible token login endpoint. 
    It receives form-encoded credentials (username and password), validates them against the database, 
    and returns a JWT access token.
    
    TODO: Implement logic using user_service.get_by_email(session, email=form_data.username).
    """
    user = user_service.get_by_email(session, email=login_request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_minutes * 60
    )

    return user

@router.post("/refresh-token", response_model=UserRead)
async def refresh_access_token(
    session: ReadSessionDep, request: Request, response: Response
) -> UserRead:
    """
    Receives a refresh token from the cookie and returns a new access token.
    """
    refresh_token = request.cookies.get("refresh_token")
    access_token = request.cookies.get("access_token")
    if not access_token and not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided"
        )
    try:
        payload = jwt.decode(access_token, settings.secret_key, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)
        exp_timestamp = payload.get("exp")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token"
        )
        
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)
        exp_timestamp = payload.get("exp")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    user = user_service.get_by_id(session, user_id=token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    expires_delta = None
    if exp_timestamp:
        exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        expires_delta = exp_time - now
        if expires_delta.total_seconds() <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )

    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id), expires_delta=expires_delta)

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60
    )

    max_age_val = int(expires_delta.total_seconds()) if expires_delta else settings.refresh_token_expire_minutes * 60
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=max_age_val
    )

    return user
    


@router.post("/signup", response_model=UserRead)
async def signup(session: WriteSessionDep, user_in: UserCreate,response:Response) -> UserRead:
    """
    Creates a new user in the database.
    Checks if the email is already registered and hashes the password securely.
    """
    if user_in.password != user_in.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match."
        )
    # 1. Check if user already exists
    existing_user = user_service.get_by_email(session, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    # 2. Call the service to create the user in the database
    new_user = user_service.create(session, obj_in=user_in)

    access_token = create_access_token(str(new_user.id))
    refresh_token = create_refresh_token(str(new_user.id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_minutes * 60
    )

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


