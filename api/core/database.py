from sqlmodel import Session, create_engine
from typing import Annotated, Generator
from fastapi import Depends
from api.core.config import settings
from redis.asyncio import Redis

redis_session = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password,
    db=settings.redis_db,
    username=settings.redis_username,
    decode_responses=True,
)

# Create the Primary (Write) Database Engine
write_engine = create_engine(
    settings.sqlalchemy_database_uri,
    echo=True, # Set to False in production
    pool_pre_ping=True
)

# Create the Replica (Read) Database Engine
# Falls back to the primary URI if no replica is configured
read_engine = create_engine(
    settings.sqlalchemy_replica_uri,
    echo=True, # Set to False in production
    pool_pre_ping=True
)

def get_write_session() -> Generator[Session, None, None]:
    """
    Yields a session connected to the Primary (Write) database.
    Use this for INSERT, UPDATE, DELETE operations.
    """
    with Session(write_engine) as session:
        yield session

def get_read_session() -> Generator[Session, None, None]:
    """
    Yields a session connected to the Replica (Read) database.
    Use this strictly for SELECT operations to offload read traffic.
    """
    with Session(read_engine) as session:
        yield session

def get_redis_session() -> Generator[Redis, None, None]:
    """
    Yields a Redis session.
    """
    yield redis_session

# Dependencies to be injected into FastApi routers
WriteSessionDep = Annotated[Session, Depends(get_write_session)]
ReadSessionDep = Annotated[Session, Depends(get_read_session)]
ReadRedisDep = Annotated[Redis, Depends(get_redis_session)]
