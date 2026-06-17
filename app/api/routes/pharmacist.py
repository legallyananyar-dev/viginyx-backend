from app.workflows.pharmacist.graph import pharmacist_fda_graph_builder
from app.services.user import user_service
import json
import asyncio
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.llm import get_llm
from app.core.checkpointer import get_checkpointer_async
from app.workflows.pharmacist.graph import pharmacist_graph_builder
from app.core.config import settings
from app.core.database import WriteSessionDep
from app.models.user import User, PharmacistThread, UserType, UserRole
from app.core.security import get_password_hash
import uuid
import secrets
from sqlmodel import select

router = APIRouter()



class WorkflowInput(BaseModel):
    pharmacist_id: str
    patient_name: str
    age: int
    gender: str
    mobile_number: str
    drugs: str | list[str]
    symptoms: str | list[str]
    additional_notes: str | None = None
    patient_consent: bool = False

@router.post("/workflow/stream")
async def stream_pharmacist_workflow(payload: WorkflowInput, session: WriteSessionDep):
    # Ensure pharmacist exists
    pharmacist = session.get(User, payload.pharmacist_id)
    if not pharmacist:
        raise HTTPException(status_code=404, detail="Pharmacist not found")

    # Check if patient exists by phone number
    patient = session.exec(
        select(User).where(
            User.phone_number == payload.mobile_number,
            User.user_type == UserType.PATIENT
        )
    ).first()

    if not patient:
        # Create new patient user
        # Email is required and unique, so we generate a placeholder email
        dummy_email = f"{payload.mobile_number}@patient.viginyx.local"
        random_password = secrets.token_urlsafe(12)
        patient = User(
            first_name=payload.patient_name,
            phone_number=payload.mobile_number,
            email=dummy_email,
            hashed_password=get_password_hash(random_password),
            user_type=UserType.PATIENT,
            role=UserRole.USER,
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)

    # Generate a unique thread ID for this specific ADR execution
    unique_thread_id = str(uuid.uuid4())
    
    # Store thread_id in PharmacistThread for auditing
    db_thread = PharmacistThread(user_id=pharmacist.id, thread_id=unique_thread_id)
    session.add(db_thread)
    session.commit()

    # Map the drug and symptom inputs (ensure lists)
    drug_list = [payload.drugs] if isinstance(payload.drugs, str) else payload.drugs
    symptom_list = [payload.symptoms] if isinstance(payload.symptoms, str) else payload.symptoms

    state_input = {
        "thread_id": unique_thread_id,
        "pharmacist_id": payload.pharmacist_id,
        "pharmacy_id": str(pharmacist.organization_id) if pharmacist.organization_id else "",
        "patient_id": str(patient.id),
        "raw_input": payload.additional_notes or "No additional notes provided.",
        "drug_list": drug_list,
        "symptoms": symptom_list,
        "consent_status": payload.patient_consent
    }

    # Configuration for the graph using the unique thread_id
    config = {
        "configurable": {
            "thread_id": unique_thread_id,
            "llm": get_llm(temperature=0)
        },
        "run_name": f"pharmacist_adr_{unique_thread_id}",
        "tags": ["pharmacist", "adr_workflow"]
    }

    async def event_generator():
        # Compile graph with configured checkpointer
        checkpointer = await get_checkpointer_async()
        graph = pharmacist_graph_builder.compile(checkpointer=checkpointer)

        VALID_NODES = {
            "llm_parser_node", "input_validation_node", "adr_calculation_node", 
            "naranjo_node", "dpdp_consent_node", "qc_validation_node", 
            "dispense_node", "override_node", "compliance_node", 
            "pvpi_report_node", "knowledge_card_node"
        }
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/stream-fda")
async def stream_fda_workflow(payload: WorkflowInput, session: WriteSessionDep):
    # Ensure pharmacist exists
    pharmacist = user_service.get_by_id(session, user_id=payload.pharmacist_id)
    if not pharmacist:
        raise HTTPException(status_code=404, detail="Pharmacist not found")

    # Check if patient exists by phone number
    patient = user_service.get_by_phone_number(session, phone_number=payload.mobile_number)

    if not patient:
        # Create new patient user
        # Email is required and unique, so we generate a placeholder email
        dummy_email = f"{payload.mobile_number}@patient.viginyx.local"
        random_password = secrets.token_urlsafe(12)
        patient = User(
            first_name=payload.patient_name,
            phone_number=payload.mobile_number,
            email=dummy_email,
            hashed_password=get_password_hash(random_password),
            user_type=UserType.PATIENT,
            role=UserRole.USER,
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)

    # Generate a unique thread ID for this specific ADR execution
    unique_thread_id = str(uuid.uuid4())
    
    # Store thread_id in PharmacistThread for auditing
    db_thread = PharmacistThread(user_id=pharmacist.id, thread_id=unique_thread_id)
    session.add(db_thread)
    session.commit()

    # Map the drug and symptom inputs (ensure lists)
    drug_list = [payload.drugs] if isinstance(payload.drugs, str) else payload.drugs
    symptom_list = [payload.symptoms] if isinstance(payload.symptoms, str) else payload.symptoms

    state_input = {
        "thread_id": unique_thread_id,
        "pharmacist_id": payload.pharmacist_id,
        "pharmacy_id": str(pharmacist.organization_id) if pharmacist.organization_id else "",
        "patient_id": str(patient.id),
        "raw_input": payload.additional_notes or "No additional notes provided.",
        "drug_list": drug_list,
        "symptoms": symptom_list,
        "consent_status": payload.patient_consent
    }

    # Configuration for the graph using the unique thread_id
    config = {
        "configurable": {
            "thread_id": unique_thread_id,
            "llm": get_llm(temperature=0)
        },
        "run_name": f"pharmacist_adr_{unique_thread_id}",
        "tags": ["pharmacist", "adr_workflow"]
    }

    checkpointer = await get_checkpointer_async()
    graph = pharmacist_fda_graph_builder.compile(checkpointer=checkpointer)
    
    # Run the graph to trigger the checkpointer
    result = await graph.ainvoke(state_input, config)

    return {"success": "true", "thread_id": unique_thread_id}