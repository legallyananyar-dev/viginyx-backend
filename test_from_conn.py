import asyncio
from api.endpoints.routes.pharmacist import conn_string
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def test():
    async with AsyncPostgresSaver.from_conn_string(conn_string.replace("localhost", "127.0.0.1")) as checkpointer:
        await checkpointer.setup()
        print("Setup successful with from_conn_string!")

asyncio.run(test())
