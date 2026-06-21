from fastapi import HTTPException, status
import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from api.core.config import settings

# Context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against the stored hashed password.
    
    TODO: Implement password verification logic.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password for secure storage.
    
    TODO: Implement password hashing logic.
    """
    return pwd_context.hash(password)

def create_access_token(user_id: str | int, expires_delta: timedelta | None = None) -> str:
    """
    Generates a JSON Web Token (JWT) for user authentication.
    
    TODO: Implement JWT token creation logic.
    """
    pass

    try:
        subject = str(user_id)
        if expires_delta:
            exp_time = datetime.now(timezone.utc) + expires_delta
        else:
            exp_time = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
            
        payload = {
            "exp": exp_time,
            "sub": subject,
            "aud":"web-client",
            "iat":datetime.now(timezone.utc),
            "iss":settings.project_name
            }
        encoded_jwt = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
        return encoded_jwt
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating access token: {str(e)}"
        )
        


def create_refresh_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """
    Generates a longer-lived JWT to be used for acquiring new access tokens.
    
    TODO: Implement refresh token creation logic.
    """
    pass

    if expires_delta:
        exp_time = datetime.now(timezone.utc) + expires_delta
    else:
        exp_time = datetime.now(timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes)

    payload = {
        "exp": exp_time,
        "sub": str(subject),
        "aud":"web-client",
        "iat":datetime.now(timezone.utc),
        "iss":settings.project_name
        }
    encoded_jwt = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt