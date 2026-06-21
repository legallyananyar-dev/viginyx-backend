import asyncio
from psycopg import AsyncConnection
from api.api.routes.pharmacist import conn_string

async def test():
    print(conn_string)
    try:
        conn = await AsyncConnection.connect(conn_string)
        print("Connected!")
        await conn.close()
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(test())
