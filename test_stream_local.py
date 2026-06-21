import asyncio
from api.endpoints.routes.pharmacist import pharmacist_graph_builder, pool
from api.workflows.pharmacist.graph import PharmacistState
from api.core.llm import get_llm
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def run_test():
    state_input = PharmacistState(
        pharmacist_id="test_pharmacist",
        patient_id="test_patient",
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
    
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    
    graph = pharmacist_graph_builder.compile(checkpointer=checkpointer)
    
    async for event in graph.astream_events(state_input, config=config, version="v2"):
        print(event["event"], event["name"])

asyncio.run(run_test())
