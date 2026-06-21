from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from api.schemas.response import APIErrorResponse

app = FastAPI()

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"custom_error": exc.detail}
    )

class TestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/raise":
            raise HTTPException(status_code=401, detail="Raised in middleware")
        elif request.url.path == "/return-model":
            return APIErrorResponse(message="Returned directly", status_code=401)
        elif request.url.path == "/return-jsonresponse":
            return JSONResponse(
                status_code=401,
                content=APIErrorResponse(message="Returned via JSONResponse", error_code="401", success=False).model_dump()
            )
        return await call_next(request)

app.add_middleware(TestMiddleware)

@app.get("/")
def read_root():
    return {"message": "Hello"}

client = TestClient(app)

print("--- Test /raise ---")
try:
    response = client.get("/raise")
    print("Status:", response.status_code)
    print("Content:", response.text)
except Exception as e:
    print("Exception occurred:", type(e).__name__)

print("\n--- Test /return-model ---")
try:
    response = client.get("/return-model")
    print("Status:", response.status_code)
    print("Content:", response.text)
except Exception as e:
    print("Exception occurred:", type(e).__name__)

print("\n--- Test /return-jsonresponse ---")
try:
    response = client.get("/return-jsonresponse")
    print("Status:", response.status_code)
    print("Content:", response.text)
except Exception as e:
    print("Exception occurred:", type(e).__name__)

