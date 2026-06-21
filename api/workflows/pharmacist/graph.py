from api.workflows.pharmacist.nodes import fda_llm_parser
from api.workflows.pharmacist.nodes import fetch_fda_data_node
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from api.workflows.pharmacist.state import PharmacistState, FDAState
from api.workflows.pharmacist.nodes import (
    llm_parser_node,
    input_validation_node,
    clinical_analysis_node,
    dpdp_consent_node,
    qc_validation_node,
    dispense_node,
    override_node,
    compliance_node,
    pvpi_report_node,
    knowledge_card_node
)
from api.workflows.pharmacist.routers import (
    intent_router,
    qc_router,
    post_dispense_router,
    consent_router
)

def create_pharmacist_graph():
    builder = StateGraph(PharmacistState)

    # Add nodes
    builder.add_node("llm_parser_node", llm_parser_node)
    builder.add_node("input_validation_node", input_validation_node)
    builder.add_node("clinical_analysis_node", clinical_analysis_node)
    builder.add_node("dpdp_consent_node", dpdp_consent_node)
    builder.add_node("qc_validation_node", qc_validation_node)
    builder.add_node("dispense_node", dispense_node)
    builder.add_node("override_node", override_node)
    builder.add_node("compliance_node", compliance_node)
    builder.add_node("pvpi_report_node", pvpi_report_node)
    builder.add_node("knowledge_card_node", knowledge_card_node)

    # Flow definitions
    builder.add_edge(START, "dpdp_consent_node")

    # Consent Router
    builder.add_conditional_edges(
        "dpdp_consent_node",
        consent_router,
        {
            "llm_parser_node": "llm_parser_node",
            "END": END
        }
    )

    # Intent router
    builder.add_conditional_edges(
        "llm_parser_node",
        intent_router,
        ["input_validation_node", "clinical_analysis_node"]
    )

    # Merge back into qc_validation_node
    builder.add_edge("input_validation_node", "qc_validation_node")
    builder.add_edge("clinical_analysis_node", "qc_validation_node")

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

def create_pharmacist_fda_graph():
    builder = StateGraph(FDAState)
    # Add nodes

    builder.add_node("fda_llm_parser", fda_llm_parser)
    # builder.add_node("dpdp_consent_node", dpdp_consent_node)
    builder.add_node("fetch_fda_data_node", fetch_fda_data_node)

    # Flow definitions
    builder.add_edge(START, "fda_llm_parser")

    # Consent Router
    # builder.add_conditional_edges(
    #     "dpdp_consent_node",
    #     consent_router,
    #     {
    #         "fda_llm_parser": "fda_llm_parser",
    #         "END": END
    #     }
    # )
    builder.add_edge("fda_llm_parser", "fetch_fda_data_node")
    builder.add_edge("fetch_fda_data_node", END)



    # We don't compile with MemorySaver globally anymore.
    # We will compile it dynamically when provided with the Postgres checkpointer.
    return builder


# Global graph builder instance
pharmacist_graph_builder = create_pharmacist_graph()
pharmacist_fda_graph_builder = create_pharmacist_fda_graph()
