from api.core.database import ReadRedisDep
from uuid import uuid4
from api.models.user import SessionData
import jwt
from datetime import datetime, timezone
from api.core.security import verify_password, ALGORITHM
from api.schemas.response import LoginRequest, APIResponse
from api.core.security import create_refresh_token
from api.core.security import create_access_token
from fastapi import Response, Request
from fastapi import APIRouter, HTTPException, status

from api.endpoints.deps import CurrentUserDep
from api.core.database import ReadSessionDep, WriteSessionDep
from api.core.config import settings
from pydantic import BaseModel
from sqlmodel import select
from api.models.user import  UserCreate, UserRead, TokenPayload, Passkeys, PasskeyRead
from webauthn import generate_registration_options, verify_registration_response, options_to_json, generate_authentication_options, verify_authentication_response
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

from api.services.user import user_service
from typing import Dict, Any
import json

router = APIRouter(tags=["auth"])

@router.post("/login",response_model=APIResponse[UserRead])
async def login_access_token(
    session: ReadSessionDep, login_request: LoginRequest,response:Response,redis_sess:ReadRedisDep
):
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

    # insert into redis
    session_id = str(uuid4())
    session_data = SessionData(
        user_id=user.id,
        user_role=user.role
    )
    await redis_sess.set(session_id,session_data.model_dump_json(),ex=settings.redis_exp)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60
    )
    return {"data":user,"message":"login success"}

@router.post("/refresh-token", response_model=APIResponse[UserRead])
async def refresh_access_token(
    session: ReadSessionDep, request: Request, response: Response
):
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

    return APIResponse(data=user)
    


@router.post("/signup", response_model=APIResponse[UserRead])
async def signup(session: WriteSessionDep, user_in: UserCreate,response:Response):
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

    return APIResponse(data=new_user)

@router.post("/test-token", response_model=APIResponse[UserRead])
async def test_token(current_user: CurrentUserDep):
    """
    Test endpoint to verify if the provided bearer token is valid.
    Returns the user data of the authenticated user.
    """
    return APIResponse(data=current_user)

@router.post('/generate-passkey-registration-options', response_model=APIResponse[dict[str, Any]])
async def generate_passkey_registration_options(current_user: CurrentUserDep, response: Response):
    try:
        options = generate_registration_options(
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            user_id=str(current_user.id).encode('utf-8'),
            user_name=str(current_user.email)
        )
        
        # Set challenge cookie
        response.set_cookie(
            key="passkey_registration_challenge",
            value=bytes_to_base64url(options.challenge) if isinstance(options.challenge, bytes) else options.challenge,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=300 # 5 minutes
        )
        

        return APIResponse(data=json.loads(options_to_json(options)))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating registration options: {str(e)}"
        )

@router.post('/verify-passkey-registration', response_model=APIResponse[dict[str, str]])
async def verify_passkey_registration(
    request: Request,
    current_user: CurrentUserDep,
    session: WriteSessionDep,
    body: Dict[str, Any]
):
    challenge = request.cookies.get("passkey_registration_challenge")
    if not challenge:
        raise HTTPException(status_code=400, detail="Registration challenge not found")
        
    try:
        verification = verify_registration_response(
            credential=body,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_expected_origin,
        )
        
        new_passkey = Passkeys(
            user_id=current_user.id,
            credintial_id=verification.credential_id.hex() if isinstance(verification.credential_id, bytes) else verification.credential_id,
            public_key=verification.credential_public_key.hex() if isinstance(verification.credential_public_key, bytes) else verification.credential_public_key,
            device_type=str(verification.credential_device_type) if hasattr(verification, 'credential_device_type') else None,
        )
        session.add(new_passkey)
        session.commit()
        return APIResponse(message="Passkey registered successfully", data=None)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/generate-passkey-login-options', response_model=APIResponse[dict[str, Any]])
async def generate_passkey_login_options(response: Response):
    """
    Generates a secure challenge for passkey authentication to prevent replay attacks.
    """
    try:
        options = generate_authentication_options(
            rp_id=settings.webauthn_rp_id
        )
        
        # Set challenge cookie
        response.set_cookie(
            key="passkey_login_challenge",
            value=bytes_to_base64url(options.challenge) if isinstance(options.challenge, bytes) else options.challenge,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=300 # 5 minutes
        )
        
        return APIResponse(data=json.loads(options_to_json(options)))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating authentication options: {str(e)}"
        )

class PasskeyLoginRequest(BaseModel):
    credential: Dict[str, Any]

@router.post('/login-passkey', response_model=APIResponse[UserRead])
async def login_passkey(
    request: PasskeyLoginRequest,
    request_obj: Request,
    session: ReadSessionDep,
    response: Response
):
    # 1. Retrieve the challenge we generated for this user/session
    challenge_b64url = request_obj.cookies.get("passkey_login_challenge")
    if not challenge_b64url:
        raise HTTPException(status_code=400, detail="Login challenge not found in cookies")
        
    expected_challenge = base64url_to_bytes(challenge_b64url)
        
    credential_id_b64 = request.credential.get("id")
    if not credential_id_b64:
        raise HTTPException(status_code=400, detail="Credential ID missing")
        
    try:
        raw_id = base64url_to_bytes(credential_id_b64)
        hex_id = raw_id.hex()
        print(hex_id,"hex_id")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid credential ID format")
    
    passkey = session.exec(select(Passkeys).where(Passkeys.credintial_id == hex_id)).first()
    
    if not passkey:
        raise HTTPException(status_code=404, detail="Passkey not found")
        
    user = passkey.user
    if not user:
        raise HTTPException(status_code=404, detail="User for this passkey not found")
        
    try:
        verification = verify_authentication_response(
            credential=request.credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_expected_origin,
            credential_public_key=bytes.fromhex(passkey.public_key) if isinstance(passkey.public_key, str) else passkey.public_key,
            credential_current_sign_count=0
        )
        
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        
        response.set_cookie(
            key="access_token", value=access_token, httponly=True,
            secure=settings.cookie_secure, samesite=settings.cookie_samesite,
            max_age=settings.access_token_expire_minutes * 60
        )
        response.set_cookie(
            key="refresh_token", value=refresh_token, httponly=True,
            secure=settings.cookie_secure, samesite=settings.cookie_samesite,
            max_age=settings.refresh_token_expire_minutes * 60
        )
        
        return APIResponse(data=user)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/passkeys', response_model=APIResponse[list[PasskeyRead]])
async def get_passkeys(current_user: CurrentUserDep, session: ReadSessionDep):
    passkeys = session.exec(select(Passkeys).where(Passkeys.user_id == current_user.id)).all()
    return APIResponse(data=passkeys)

@router.post("/logout")
async def logout(response:Response):
    """Logout a user"""
    response.set_cookie("access_token", "", httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, max_age=0)
    response.set_cookie("refresh_token", "", httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, max_age=0)
    return APIResponse(data=None)

@router.get('/ping')
async def ping():
    return APIResponse(data={'message':'pong'})
    