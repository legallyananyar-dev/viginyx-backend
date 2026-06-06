from typing import Any

def get_cors_config() -> dict[str, Any]:
    return {
        "allow_origins": [
            "http://localhost:3000",
            "http://localhost:5173",
        ],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }