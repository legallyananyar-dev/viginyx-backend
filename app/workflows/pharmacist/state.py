from typing import TypedDict, List, Dict, Any

class PharmacistState(TypedDict):
    thread_id: str
    pharmacist_id: str
    pharmacy_id: str
    patient_id: str
    raw_input: str
    intent: str
    drug_list: list[str]
    symptoms: list[str]
    qc_result: str
    qc_flags: list[dict]
    naranjo_score: int
    naranjo_causality: str
    adr_api_response: dict
    pvpi_payload: dict
    consent_status: bool
    override_note: str
    compliance_log: dict
    knowledge_card: str
    error: str

