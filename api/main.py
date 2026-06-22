import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.core.config import settings
from api.endpoints.routes import auth, users, pharmacist
from fastapi.middleware.cors import CORSMiddleware
from api.core.database import write_engine, read_engine
from api.core.exceptions import setup_exception_handlers
from api.schemas.response import APIResponse
from sqlmodel import SQLModel

from api.core.checkpointer import shutdown_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database is now managed by Alembic, do not run create_all here
    pass
    
    yield
    
    # --- Shutdown Logic ---
    # Clean up the checkpointer connection pool (if postgres)
    await shutdown_checkpointer()
    # Clean up the database connection pools on shutdown
    write_engine.dispose()
    read_engine.dispose()

app = FastAPI(
    title=settings.project_name,
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    lifespan=lifespan
)


# CORS Middelware
app.add_middleware(
    CORSMiddleware,
    **settings.cors_config
)

# Register global exception handlers for consistent error structures
setup_exception_handlers(app)

# Auth Middleware
from api.middleware.auth import AuthMiddleware
app.add_middleware(AuthMiddleware)



# Including routers without re-declaring prefix/tags if already defined in the router
app.include_router(auth.router, prefix=settings.api_v1_str)
app.include_router(users.router, prefix=settings.api_v1_str)
app.include_router(pharmacist.router, prefix=f"{settings.api_v1_str}/pharmacist", tags=["Pharmacist"])

@app.get("/health-check", response_model=APIResponse[dict[str, str]])
async def health_check() -> APIResponse[dict[str, str]]:
    return APIResponse(
        success=True,
        message="System is healthy",
        data={"status": "ok"}
    )
