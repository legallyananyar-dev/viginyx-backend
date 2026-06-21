from langsmith import traceable
from api.workflows.pharmacist.state import PharmacistState

@traceable(name="intent_router", run_type="chain")
def intent_router(state: PharmacistState):
    intent = state.get("intent", "")
    if intent == "full_flow":
        return [
            "input_validation_node",
            "clinical_analysis_node"
        ]
    else:
        return ["clinical_analysis_node"]

def consent_router(state: PharmacistState) -> str:
    if state.get("consent_status", False):
        return "llm_parser_node"
    return "END"

def qc_router(state: PharmacistState) -> str:
    res = state.get("qc_result", "fail")
    if res == "pass":
        return "dispense_node"
    else:
        return "override_node"

@traceable(name="post_dispense_router", run_type="chain")
def post_dispense_router(state: PharmacistState):
    return [
        "compliance_node",
        "pvpi_report_node",
        "knowledge_card_node"
    ]
