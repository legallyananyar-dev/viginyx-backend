from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import items, auth, users
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import write_engine, read_engine
from app.core.exceptions import setup_exception_handlers
from app.schemas.response import APIResponse
from sqlmodel import SQLModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database is now managed by Alembic, do not run create_all here
    pass
    
    yield
    
    # --- Shutdown Logic ---
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
from app.middleware.auth import AuthMiddleware
app.add_middleware(AuthMiddleware)



# Including routers without re-declaring prefix/tags if already defined in the router
app.include_router(auth.router, prefix=settings.api_v1_str)
app.include_router(items.router, prefix=settings.api_v1_str)
app.include_router(users.router, prefix=settings.api_v1_str)

@app.get("/health-check", response_model=APIResponse[dict[str, str]])
async def health_check() -> APIResponse[dict[str, str]]:
    return APIResponse(
        success=True,
        message="System is healthy",
        data={"status": "ok"}
    )
