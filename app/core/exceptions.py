from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.schemas.response import APIErrorResponse
from app.core.config import settings

def setup_exception_handlers(app: FastAPI):
    """
    Registers global exception handlers to enforce a consistent error response structure
    across the entire application.
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Catches all standard HTTP exceptions (e.g., when you call `raise HTTPException(...)`).
        Converts the exception into a unified APIErrorResponse format so the client always 
        receives a consistent JSON structure.
        """
        response = APIErrorResponse(
            success=False,
            error_code=exc.status_code,
            message="An HTTP error occurred",
            details=exc.detail
        )
        return JSONResponse(status_code=exc.status_code, content=response.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Catches all Pydantic validation errors that occur when the client sends a bad request 
        payload (e.g., missing required fields, wrong data types). Maps these automatically 
        generated errors into the specific format requested.
        """
        errors = []
        if settings.environment in ("dev", "staging"):
            for err in exc.errors():
                field = str(err.get("loc", [""])[-1])
                msg = err.get("msg", "Invalid value")
                errors.append({"field": field, "message": msg})
                
        return JSONResponse(
            status_code=422, 
            content={
                "message": "Validation failed",
                "errors": errors
            }
        )
        
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        A global catch-all handler for any unhandled internal server crashes or exceptions.
        This ensures that even if the app crashes unexpectedly, the client still receives 
        a safely formatted standard APIErrorResponse (500) rather than an ugly stack trace.
        """
        response = APIErrorResponse(
            success=False,
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details=str(exc) if settings.environment in ("dev", "staging") else None
        )
        return JSONResponse(status_code=500, content=response.model_dump())
