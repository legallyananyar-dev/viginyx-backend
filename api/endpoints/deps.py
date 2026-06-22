from api.services.user import user_service
from typing import Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from api.core.config import settings
from api.core.database import ReadSessionDep
from api.models.user import User, UserRole

# This configures FastAPI to extract the bearer token from the Authorization header
# Using auto_error=False so it doesn't block requests with cookies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_str}/login", auto_error=False)

# Dependency aliases for clean path operations
TokenDep = Annotated[str | None, Depends(oauth2_scheme)]

def get_current_user(session: ReadSessionDep, request: Request, swagger_token: TokenDep) -> User:
    """
    Dependency that fetches the corresponding user from the database
    using the user_id extracted by the AuthMiddleware.
    """
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_service.get_by_id(session, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Dependency alias used to secure endpoints that require an authenticated user
CurrentUserDep = Annotated[User, Depends(get_current_user)]

class RoleChecker:
    """
    Dependency class to check if the current user has required roles.
    If allowed_roles is None or empty, it won't check privileges.
    """
    def __init__(self, allowed_roles: list[UserRole] | None = None):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: CurrentUserDep) -> User:
        if self.allowed_roles:
            if current_user.role not in self.allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="The user doesn't have enough privileges"
                )
        return current_user

# Retained for backward compatibility
SuperAdminDep = Annotated[User, Depends(RoleChecker([UserRole.SUPER_ADMIN]))]
