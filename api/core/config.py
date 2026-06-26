import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from typing import ClassVar


# Determines which environment file to load (default is dev)
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

from dotenv import load_dotenv
load_dotenv(f".env.{ENVIRONMENT}")

class Settings(BaseSettings):
    """
    Application settings and configurations.
    These are loaded from the environment variables or the corresponding .env file.
    """
    project_name: str = "Viginyx Backend API"
    api_v1_str: str = "/api/v1"
    environment: str = ENVIRONMENT
    
    # Auth configuration
    secret_key: str
    access_token_expire_minutes: int = 60 * 24 * 30 # 5 minutes
    refresh_token_expire_minutes: int = 60 * 24 * 30 # 30 days
    
    # Database connection parameters
    postgres_server: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: int
    
    # Optional replica parameters
    postgres_replica_server: str | None = None
    postgres_replica_port: int | None = None

    # WebAuthn Configuration
    webauthn_rp_id: str  
    webauthn_rp_name: str 
    webauthn_expected_origin: str = "http://localhost:4001"

    #Hashing key
    hashing_secret_key: str 

    #Cookie configuration
    cookie_secure: bool = True
    cookie_samesite: str = "None"
    cookie_domain: str | None = None
    cookie_path: str = "/"

    # Initial Superuser
    first_superuser: str | None = None
    first_superuser_password: str | None = None

    # LLM Configuration
    llm_provider: str = "ollama" # Options: "google", "openai", "anthropic", "grok", "ollama"
    llm_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    chat_gpt_api_key: str | None = None
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    grok_api_key: str | None = None
    ollama_base_url: str | None = "https://8080-01krc32prg8r3e6sd3v76vscg9.cloudspaces.litng.ai"

    # Checkpointer Configuration
    checkpointer_backend: str = "memory" # Options: "memory", "postgres"


    cors_config: ClassVar[dict] = {
        "allow_origins": ["http://localhost:3000","http://localhost:4001"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_username: str = ""
    redis_exp:int = 1800

    @computed_field
    @property
    def sqlalchemy_database_uri(self) -> str:
        """URI for primary (write) database"""
        return f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}?sslmode=require"

    @computed_field
    @property
    def sqlalchemy_replica_uri(self) -> str:
        """URI for replica (read) database. Falls back to primary if no replica server is set."""
        server = self.postgres_replica_server or self.postgres_server
        port = self.postgres_replica_port or self.postgres_port
        return f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{server}:{port}/{self.postgres_db}?sslmode=require"

    # Tell pydantic to load variables from the correct .env file
    model_config = SettingsConfigDict(
        env_file=f".env.{ENVIRONMENT}", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
