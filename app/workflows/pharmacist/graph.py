from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.workflows.pharmacist.state import PharmacistState
from app.workflows.pharmacist.nodes import (
    llm_parser_node,
    input_validation_node,
    adr_calculation_node,
    naranjo_node,
    dpdp_consent_node,
    qc_validation_node,
    dispense_node,
    override_node,
    compliance_node,
    pvpi_report_node,
    knowledge_card_node,
    intent_router,
    qc_router,
    post_dispense_router
)

def create_pharmacist_graph():
    builder = StateGraph(PharmacistState)

    # Add nodes
    builder.add_node("llm_parser_node", llm_parser_node)
    builder.add_node("input_validation_node", input_validation_node)
    builder.add_node("adr_calculation_node", adr_calculation_node)
    builder.add_node("naranjo_node", naranjo_node)
    builder.add_node("dpdp_consent_node", dpdp_consent_node)
    builder.add_node("qc_validation_node", qc_validation_node)
    builder.add_node("dispense_node", dispense_node)
    builder.add_node("override_node", override_node)
    builder.add_node("compliance_node", compliance_node)
    builder.add_node("pvpi_report_node", pvpi_report_node)
    builder.add_node("knowledge_card_node", knowledge_card_node)

    # Flow definitions
    builder.add_edge(START, "llm_parser_node")

    # Intent router
    builder.add_conditional_edges(
        "llm_parser_node",
        intent_router,
        ["input_validation_node", "adr_calculation_node", "dpdp_consent_node"]
    )

    # Naranjo execution follows ADR calculation
    builder.add_edge("adr_calculation_node", "naranjo_node")

    # Merge back into qc_validation_node
    builder.add_edge("input_validation_node", "qc_validation_node")
    builder.add_edge("naranjo_node", "qc_validation_node")
    builder.add_edge("dpdp_consent_node", "qc_validation_node")

    # Route after QC
    builder.add_conditional_edges(
        "qc_validation_node",
        qc_router,
        {
            "dispense_node": "dispense_node",
            "override_node": "override_node"
        }
    )

    # Route after Dispense/Override
    builder.add_conditional_edges(
        "dispense_node",
        post_dispense_router,
        ["compliance_node", "pvpi_report_node", "knowledge_card_node"]
    )
    builder.add_conditional_edges(
        "override_node",
        post_dispense_router,
        ["compliance_node", "pvpi_report_node", "knowledge_card_node"]
    )

    # Merge to END
    builder.add_edge("compliance_node", END)
    builder.add_edge("pvpi_report_node", END)
    builder.add_edge("knowledge_card_node", END)

    # We don't compile with MemorySaver globally anymore.
    # We will compile it dynamically when provided with the Postgres checkpointer.
    return builder

# Global graph builder instance
pharmacist_graph_builder = create_pharmacist_graph()
