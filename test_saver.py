import asyncio
from psycopg import AsyncConnection
from api.api.routes.pharmacist import conn_string
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def test():
    async with await AsyncConnection.connect(conn_string.replace("localhost", "127.0.0.1")) as conn:
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()
        print("Setup successful with AsyncConnection!")

asyncio.run(test())
