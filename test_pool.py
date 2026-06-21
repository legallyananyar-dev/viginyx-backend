import asyncio
from api.api.routes.pharmacist import pool

async def test():
    print("Opening pool...")
    try:
        await asyncio.wait_for(pool.open(), timeout=5.0)
        print("Pool opened successfully")
    except Exception as e:
        print("Error:", type(e), e)
    
asyncio.run(test())
