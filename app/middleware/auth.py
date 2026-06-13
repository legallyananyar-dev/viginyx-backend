from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from starlette.responses import JSONResponse
import jwt

from app.core.config import settings
from app.core.security import ALGORITHM
from app.models.user import TokenPayload

class AuthMiddleware(BaseHTTPMiddleware):
    # Paths that do not require authentication
    public_paths = {
        f"{settings.api_v1_str}/signup",
        f"{settings.api_v1_str}/login",
        f"{settings.api_v1_str}/login/refresh-token",
        "/health-check",
        "/docs",
        "/redoc",
        f"{settings.api_v1_str}/refresh-token",
        "/openapi.json"
    }

    async def dispatch(self, request: Request, call_next):
        # 1. Skip authentication for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)

        # 2. Extract Token
        token = request.cookies.get("access_token")
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        # 3. Deny if no token exists
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # 4. Decode and Verify Token
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            token_data = TokenPayload(**payload)
            request.state.user_id = token_data.sub
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authentication credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # 5. Proceed to the endpoint
        response = await call_next(request)
        return response
