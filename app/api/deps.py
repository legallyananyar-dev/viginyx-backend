from app.services.user import user_service
import jwt
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from pydantic import ValidationError
from jwt.exceptions import InvalidTokenError

from app.core.config import settings
from app.core.database import ReadSessionDep
from app.models.user import User, TokenPayload
from app.core.security import ALGORITHM

# This configures FastAPI to extract the bearer token from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_str}/login/access-token")

# Dependency aliases for clean path operations
TokenDep = Annotated[str, Depends(oauth2_scheme)]

def get_current_user(session: ReadSessionDep, token: TokenDep) -> User:
    """
    Dependency that decodes the provided JWT token, extracts the user ID,
    and fetches the corresponding user from the database.
    
    TODO: Implement token decoding and user retrieval logic using user_service.get(session, user_id).
    """
    pass
    
    try:
        payload = jwt.decode(token,settings.secret_key,algorithms=ALGORITHM)
        token_data = TokenPayload(**payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_service.get_by_id(session, user_id=token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Dependency alias used to secure endpoints that require an authenticated user
CurrentUserDep = Annotated[User, Depends(get_current_user)]
