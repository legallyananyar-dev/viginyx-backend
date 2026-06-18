from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from psycopg_pool import AsyncConnectionPool
from app.core.config import settings


# Module-level singletons (initialized lazily)
_memory_saver: MemorySaver | None = None
_postgres_pool: AsyncConnectionPool | None = None
_postgres_saver: AsyncPostgresSaver | None = None


def get_memory_checkpointer() -> MemorySaver:
    """Returns a singleton in-memory checkpointer."""
    global _memory_saver
    if _memory_saver is None:
        _memory_saver = MemorySaver()
    return _memory_saver


async def get_postgres_checkpointer() -> AsyncPostgresSaver:
    """Returns a singleton async Postgres checkpointer, creating the pool if needed."""
    global _postgres_pool, _postgres_saver
    if _postgres_saver is None:
        conn_string = (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}?sslmode=require"
        )
        _postgres_pool = AsyncConnectionPool(
            conninfo=conn_string,
            kwargs={"autocommit": True},
            open=False
        )
        await _postgres_pool.open()
        _postgres_saver = AsyncPostgresSaver(_postgres_pool)
        await _postgres_saver.setup()
    return _postgres_saver


def get_checkpointer() -> BaseCheckpointSaver:
    """
    Synchronous factory — returns a checkpointer based on CHECKPOINTER_BACKEND config.
    For 'postgres', returns a wrapper that must be awaited at first use.
    For 'memory', returns immediately.
    """
    backend = settings.checkpointer_backend.lower()

    if backend == "memory":
        return get_memory_checkpointer()
    elif backend == "postgres":
        # For sync contexts we can only return the memory saver as a fallback.
        # Use get_checkpointer_async() in async contexts for postgres.
        raise RuntimeError(
            "Postgres checkpointer requires async context. "
            "Use 'await get_checkpointer_async()' instead."
        )
    else:
        raise ValueError(f"Unsupported checkpointer backend: {backend}")


async def get_checkpointer_async() -> BaseCheckpointSaver:
    """
    Async factory — returns the configured checkpointer.
    Use this in async route handlers and graph compilation.
    """
    backend = settings.checkpointer_backend.lower()

    if backend == "memory":
        return get_memory_checkpointer()
    elif backend == "postgres":
        return await get_postgres_checkpointer()
    else:
        raise ValueError(f"Unsupported checkpointer backend: {backend}")


async def shutdown_checkpointer() -> None:
    """Cleanup: close the postgres pool on app shutdown."""
    global _postgres_pool, _postgres_saver
    if _postgres_pool is not None:
        await _postgres_pool.close()
        _postgres_pool = None
        _postgres_saver = None
