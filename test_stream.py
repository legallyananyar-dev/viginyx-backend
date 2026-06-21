import asyncio
from api.api.routes.pharmacist import pharmacist_graph_builder
from api.workflows.pharmacist.graph import PharmacistState
from api.core.llm import get_llm
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

async def test():
    state_input = PharmacistState(
        pharmacist_id="00000000-0000-0000-0000-000000000000",
        patient_id="00000000-0000-0000-0000-000000000000",
        drug_list=["Aspirin"],
        symptoms=["Headache"],
        consent_status=True
    )
    
    config = {
        "configurable": {
            "thread_id": "test_thread",
            "llm": get_llm(temperature=0)
        }
    }
    
    pool = AsyncConnectionPool(
        conninfo="postgresql://viginyx:viginyx_local_secret@localhost:5432/viginyx",
        open=False
    )
    await pool.open()
    
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    graph = pharmacist_graph_builder.compile(checkpointer=checkpointer)
    
    try:
        async for event in graph.astream_events(state_input, config=config, version="v2"):
            print("Event:", event["event"], event["name"])
    except Exception as e:
        print("EXCEPTION:", e)

asyncio.run(test())
