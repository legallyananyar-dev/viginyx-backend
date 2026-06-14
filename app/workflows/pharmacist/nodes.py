import json
import httpx
from langgraph.types import Send, interrupt
from langchain_core.messages import SystemMessage, HumanMessage
from app.workflows.pharmacist.state import PharmacistState
from app.core.database import write_engine
from sqlmodel import Session
from app.models.user import NaranjoResult

from pydantic import BaseModel, Field


async def llm_parser_node(state: PharmacistState, config: dict) -> dict:
    try:
        llm = config.get("configurable", {}).get("llm")
        if not llm:
            raise ValueError("LLM not provided in config")

        system_prompt = """You are a clinical data extractor for
an Indian pharmacy system.

Extract the following from the pharmacist
input text and return ONLY valid JSON.
No explanation. No markdown. No preamble.

Return this exact structure:
{
  "drug_list": ["drug name 1", "drug name 2"],
  "symptoms": ["symptom 1", "symptom 2"],
  "intent": "full_flow" or "adr_only"
}

Rules:
- drug_list: all drugs mentioned, brand 
  or generic names, as spoken
- symptoms: all patient reported symptoms
- intent: 
    "full_flow" if any drug is mentioned
    "adr_only"  if only symptoms, no drugs
- If nothing found return empty lists
- Never add fields outside this schema"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state.get("raw_input", ""))
        ]
        
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        
        # Clean up possible markdown json blocks
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        parsed = json.loads(content)
        
        return {
            "drug_list": parsed.get("drug_list", []),
            "symptoms": parsed.get("symptoms", []),
            "intent": parsed.get("intent", "full_flow")
        }
    except Exception as e:
        return {
            "error": f"llm_parser_node error: {str(e)}",
            "drug_list": [],
            "symptoms": []
        }

def intent_router(state: PharmacistState):
    intent = state.get("intent", "")
    if intent == "full_flow":
        return [
            Send("input_validation_node", state),
            Send("adr_calculation_node", state),
            Send("dpdp_consent_node", state)
        ]
    else:
        return [Send("adr_calculation_node", state)]

async def input_validation_node(state: PharmacistState, config: dict) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        await llm.ainvoke(f"Validate these drugs in the Indian pharmacy context: {state.get('drug_list', [])}")
        return {}
    except Exception as e:
        return {"error": f"input_validation_node error: {str(e)}"}


class NaranjoQuestionAnswer(BaseModel):
    question_number: int = Field(description="The Naranjo question number (1-10)")
    answer: str = Field(description="Yes, No, or Unknown")
    score: int = Field(description="The score assigned for this answer")
    reasoning: str = Field(description="Clinical reasoning for the answer")

class NaranjoAssessment(BaseModel):
    questions: list[NaranjoQuestionAnswer]
    total_score: int = Field(description="Sum of all question scores")
    causality: str = Field(description="Definite (>=9), Probable (5-8), Possible (1-4), Doubtful (<=0)")

class ADRMockResponse(BaseModel):
    known_reactions: list[str] = Field(description="List of known adverse reactions for these drugs")
    clinical_notes: str = Field(description="Clinical notes on the interaction")

async def adr_calculation_node(state: PharmacistState, config: dict) -> dict:
    llm = config.get("configurable", {}).get("llm")
    if not llm:
        return {"error": "LLM not provided in config"}
        
    try:
        system_prompt = "You are a clinical pharmacovigilance database. Provide known adverse reactions and clinical notes for the given drugs and symptoms."
        human_prompt = f"Drugs: {state.get('drug_list', [])}\nSymptoms: {state.get('symptoms', [])}"
        
        structured_llm = llm.with_structured_output(ADRMockResponse)
        response = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        api_data = response.model_dump()
        api_data["pvpi_draft"] = {}
        
        return {
            "adr_api_response": api_data,
            "pvpi_payload": {}
        }
    except Exception as e:
        return {"error": f"adr_calculation_node error: {str(e)}"}

async def naranjo_node(state: PharmacistState, config: dict) -> dict:
    llm = config.get("configurable", {}).get("llm")
    if not llm:
        return {"error": "LLM not provided in config"}

    try:
        # Step 1: Read raw ADR API data from state
        api_data = state.get("adr_api_response", {})
            
        # Step 2: Prompt LLM
        system_prompt = """You are a clinical pharmacovigilance expert.

You will be given:
- A list of drugs the patient is taking
- Symptoms the patient reported
- ADR API data about known reactions

Answer all 10 Naranjo questions using only the information provided.

Never ask for more information.
Never say unknown unless truly no data exists.
Use clinical reasoning to infer answers.

Q1. Are there previous conclusive reports of this reaction? Yes +1 | No 0 | Unknown 0
Q2. Did the adverse reaction appear after the suspected drug was given? Yes +2 | No -1 | Unknown 0
Q3. Did the adverse reaction improve when the drug was discontinued or a specific antagonist was given? Yes +1 | No 0 | Unknown 0
Q4. Did the adverse reaction reappear when the drug was re-administered? Yes +2 | No -1 | Unknown 0
Q5. Are there alternative causes that could have caused the reaction on their own? Yes -1 | No +2 | Unknown 0
Q6. Did the reaction reappear when a placebo was given? Yes -1 | No +1 | Unknown 0
Q7. Was the drug detected in the blood or other fluids in a toxic concentration? Yes +1 | No 0 | Unknown 0
Q8. Was the reaction more severe when the dose was increased or less severe when the dose was decreased? Yes +1 | No 0 | Unknown 0
Q9. Did the patient have a similar reaction to the same or similar drugs in a previous exposure? Yes +1 | No 0 | Unknown 0
Q10. Was the adverse reaction confirmed by any objective evidence? Yes +1 | No 0 | Unknown 0"""
        
        human_prompt = f"""
Drugs: {state.get('drug_list', [])}
Symptoms: {state.get('symptoms', [])}
ADR API data: {json.dumps(api_data)}

Answer all 10 Naranjo questions. Calculate total score and causality."""
        
        structured_llm = llm.with_structured_output(NaranjoAssessment)
        assessment = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])

        assessment_dict = assessment.model_dump()

        try:
            # Save to database synchronously
            with Session(write_engine) as session:
                result = NaranjoResult(
                    pharmacist_id=state.get("pharmacist_id"),
                    patient_id=state.get("patient_id"),
                    thread_id=state.get("thread_id"),
                    naranjo_score=assessment.total_score,
                    naranjo_causality=assessment.causality,
                    adr_api_response=assessment_dict,
                    pvpi_payload=api_data.get("pvpi_draft", {})
                )
                session.add(result)
                session.commit()
        except Exception as db_err:
            print(f"Failed to save NaranjoResult to DB: {db_err}")

        return {
            "adr_api_response": assessment_dict,
            "naranjo_score": assessment.total_score,
            "naranjo_causality": assessment.causality,
            "pvpi_payload": api_data.get("pvpi_draft", {})
        }
    except Exception as e:
        return {"error": f"naranjo_node error: {str(e)}"}

async def dpdp_consent_node(state: PharmacistState, config: dict) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        res = await llm.ainvoke(f"Should we assume consent for patient {state.get('patient_id')}? (Mocking True for now)")
        consent_status = True
        
        updates = {"consent_status": consent_status}
        if not consent_status:
            updates["patient_id"] = "***MASKED***"
            
        return updates
    except Exception as e:
        return {"error": f"dpdp_consent_node error: {str(e)}"}

class QCMock(BaseModel):
    overall: str = Field(description="'pass' or 'fail'")
    flags: list[dict] = Field(description="List of flags")

async def qc_validation_node(state: PharmacistState, config: dict) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        structured_llm = llm.with_structured_output(QCMock)
        res = await structured_llm.ainvoke(f"Validate QC for drugs: {state.get('drug_list')} and patient {state.get('patient_id')}. Mostly pass.")
        return {
            "qc_result": res.overall,
            "qc_flags": res.flags
        }
    except Exception as e:
        return {"error": f"qc_validation_node error: {str(e)}"}

def qc_router(state: PharmacistState) -> str:
    res = state.get("qc_result", "fail")
    if res == "pass":
        return "dispense_node"
    else:
        return "override_node"

def dispense_node(state: PharmacistState) -> dict:
    try:
        return {
            "compliance_log": {
                "thread_id": state.get("thread_id"),
                "pharmacist_id": state.get("pharmacist_id"),
                "dispensed": True,
                "override": False
            }
        }
    except Exception as e:
        return {"error": f"dispense_node error: {str(e)}"}

def override_node(state: PharmacistState) -> dict:
    try:
        note = interrupt("Please provide an override note to dispense.")
        return {
            "override_note": str(note),
            "compliance_log": {
                "thread_id": state.get("thread_id"),
                "pharmacist_id": state.get("pharmacist_id"),
                "dispensed": True,
                "override": True,
                "override_note": str(note)
            }
        }
    except Exception as e:
        return {"error": f"override_node error: {str(e)}"}

def post_dispense_router(state: PharmacistState):
    return [
        Send("compliance_node", state),
        Send("pvpi_report_node", state),
        Send("knowledge_card_node", state)
    ]

async def compliance_node(state: PharmacistState, config: dict) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        await llm.ainvoke(f"Log compliance record: {state.get('compliance_log', {})}")
        return {}
    except Exception as e:
        return {"error": f"compliance_node error: {str(e)}"}

async def pvpi_report_node(state: PharmacistState, config: dict) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        if state.get("consent_status") is True:
            res = await llm.ainvoke(f"Generate PVPI submission receipt for: {state.get('pvpi_payload', {})}")
            pvpi_payload = state.get("pvpi_payload", {})
            pvpi_payload["submission_receipt"] = res.content
            return {"pvpi_payload": pvpi_payload}
        return {}
    except Exception as e:
        return {"error": f"pvpi_report_node error: {str(e)}"}

async def knowledge_card_node(state: PharmacistState, config: dict) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        res = await llm.ainvoke(f"Generate a brief 2-sentence clinical knowledge card for {state.get('drug_list')} considering {state.get('naranjo_causality')} causality.")
        summary = res.content
        print("\n=== KNOWLEDGE CARD ===")
        print(summary)
        print("======================\n")
        return {"knowledge_card": summary}
    except Exception as e:
        return {"error": f"knowledge_card_node error: {str(e)}"}
