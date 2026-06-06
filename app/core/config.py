import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

# Determines which environment file to load (default is dev)
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

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
    access_token_expire_minutes: int = 60 * 24 * 8 # 8 days
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

    @computed_field
    @property
    def sqlalchemy_database_uri(self) -> str:
        """URI for primary (write) database"""
        return f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"

    @computed_field
    @property
    def sqlalchemy_replica_uri(self) -> str:
        """URI for replica (read) database. Falls back to primary if no replica server is set."""
        server = self.postgres_replica_server or self.postgres_server
        port = self.postgres_replica_port or self.postgres_port
        return f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{server}:{port}/{self.postgres_db}"

    # Tell pydantic to load variables from the correct .env file
    model_config = SettingsConfigDict(
        env_file=f".env.{ENVIRONMENT}", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
