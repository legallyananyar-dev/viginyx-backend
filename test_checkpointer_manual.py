import asyncio
from app.core.config import settings
from app.workflows.pharmacist.graph import pharmacist_fda_graph_builder
from app.core.checkpointer import get_checkpointer_async

async def main():
    print(f"Checkpointer backend: {settings.checkpointer_backend}")
    print(f"Postgres DB: {settings.postgres_db}")
    
    checkpointer = await get_checkpointer_async()
    graph = pharmacist_fda_graph_builder.compile(checkpointer=checkpointer)
    
    config = {
        "configurable": {
            "thread_id": "test_thread_123"
        }
    }
    
    state_input = {
        "thread_id": "test_thread_123",
        "pharmacist_id": "pharma_1",
        "pharmacy_id": "pharm_1",
        "patient_id": "pat_1",
        "raw_input": "Testing",
        "drug_list": ["aspirin"],
        "symptoms": ["headache"],
        "consent_status": True
    }
    
    print("Invoking graph...")
    result = await graph.ainvoke(state_input, config)
    print("Graph invoked successfully.")
    print("Result:", result)
    
    # Check if checkpoint exists
    checkpoint = await checkpointer.aget_tuple(config)
    if checkpoint:
        print("Checkpoint exists:", checkpoint.checkpoint["id"])
    else:
        print("No checkpoint found!")

if __name__ == "__main__":
    asyncio.run(main())
