import asyncio
from psycopg import AsyncConnection
from app.api.routes.pharmacist import conn_string
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def test():
    conn = await AsyncConnection.connect(conn_string, autocommit=True)
    checkpointer = AsyncPostgresSaver(conn)
    await checkpointer.setup()
    print("Setup successful with explicit autocommit=True!")
    await conn.close()

asyncio.run(test())
