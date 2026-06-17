import json
from langgraph.types import interrupt
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from sqlmodel import Session

from app.workflows.pharmacist.state import PharmacistState
from app.workflows.pharmacist.prompts import PARSER_SYSTEM_PROMPT, NARANJO_SYSTEM_PROMPT
from app.workflows.pharmacist.schemas import ADRMockResponse, NaranjoAssessment, QCMock
from app.core.database import write_engine
from app.models.user import NaranjoResult

@traceable(name="llm_parser_node", run_type="chain")
async def llm_parser_node(state: PharmacistState, config: RunnableConfig) -> dict:
    try:
        # llm = config.get("configurable", {}).get("llm")
        # if not llm:
        #     raise ValueError("LLM not provided in config")

        # messages = [
        #     SystemMessage(content=PARSER_SYSTEM_PROMPT),
        #     HumanMessage(content=state.get("raw_input", ""))
        # ]
        
        # response = await llm.ainvoke(messages, config=config)
        # content = response.content.strip()
        
        # Clean up possible markdown json blocks
        # if content.startswith("```json"):
        #     content = content[7:-3].strip()
        # elif content.startswith("```"):
        #     content = content[3:-3].strip()
            
        # parsed = json.loads(content)
        
        # existing_drugs = state.get("drug_list", [])
        # existing_symptoms = state.get("symptoms", [])
        
        # parsed_drugs = parsed.get("drug_list", [])
        # parsed_symptoms = parsed.get("symptoms", [])
        
        # combined_drugs = list(set(existing_drugs + parsed_drugs))
        # combined_symptoms = list(set(existing_symptoms + parsed_symptoms))
        
        # intent = parsed.get("intent", "full_flow")
        # if combined_drugs:
        #     intent = "full_flow"
            
        return {
            "drug_list": [],
            "symptoms": [],
            "intent": ""
        }
    except Exception as e:
        return {
            "error": f"llm_parser_node error: {str(e)}",
            "drug_list": state.get("drug_list", []),
            "symptoms": state.get("symptoms", [])
        }

@traceable(name="input_validation_node", run_type="chain")
async def input_validation_node(state: PharmacistState, config: RunnableConfig) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        await llm.ainvoke(f"Validate these drugs in the Indian pharmacy context: {state.get('drug_list', [])}", config=config)
        return {}
    except Exception as e:
        return {"error": f"input_validation_node error: {str(e)}"}

@traceable(name="clinical_analysis_node", run_type="chain")
async def clinical_analysis_node(state: PharmacistState, config: RunnableConfig) -> dict:
    llm = config.get("configurable", {}).get("llm")
    if not llm:
        return {"error": "LLM not provided in config"}
        
    try:
        # Step 1: ADR Calculation
        adr_sys_prompt = "You are a clinical pharmacovigilance database. Provide known adverse reactions and clinical notes for the given drugs and symptoms."
        adr_human_prompt = f"Drugs: {state.get('drug_list', [])}\nSymptoms: {state.get('symptoms', [])}"
        
        structured_adr_llm = llm.with_structured_output(ADRMockResponse)
        adr_response = await structured_adr_llm.ainvoke([
            SystemMessage(content=adr_sys_prompt),
            HumanMessage(content=adr_human_prompt)
        ], config=config)
        
        api_data = adr_response.model_dump()
        api_data["pvpi_draft"] = {}
        
        # Step 2: Naranjo Evaluation
        naranjo_human_prompt = f"""
Drugs: {state.get('drug_list', [])}
Symptoms: {state.get('symptoms', [])}
ADR API data: {json.dumps(api_data)}

Answer all 10 Naranjo questions. Calculate total score and causality."""
        
        structured_naranjo_llm = llm.with_structured_output(NaranjoAssessment)
        assessment = await structured_naranjo_llm.ainvoke([
            SystemMessage(content=NARANJO_SYSTEM_PROMPT),
            HumanMessage(content=naranjo_human_prompt)
        ], config=config)

        assessment_dict = assessment.model_dump()

        try:
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
        return {"error": f"clinical_analysis_node error: {str(e)}"}

@traceable(name="dpdp_consent_node", run_type="chain")
async def dpdp_consent_node(state: PharmacistState, config: RunnableConfig) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        # res = await llm.ainvoke(f"Should we assume consent for patient {state.get('patient_id')}? (Mocking True for now)", config=config)
        consent_status = True
        
        updates = {"consent_status": consent_status}
        if not consent_status:
            updates["patient_id"] = "***MASKED***"
            
        return updates
    except Exception as e:
        return {"error": f"dpdp_consent_node error: {str(e)}"}

@traceable(name="qc_validation_node", run_type="chain")
async def qc_validation_node(state: PharmacistState, config: RunnableConfig) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        structured_llm = llm.with_structured_output(QCMock)
        res = await structured_llm.ainvoke(f"Validate QC for drugs: {state.get('drug_list')} and patient {state.get('patient_id')}. Mostly pass.", config=config)
        return {
            "qc_result": res.overall,
            "qc_flags": res.flags
        }
    except Exception as e:
        return {"error": f"qc_validation_node error: {str(e)}"}

@traceable(name="dispense_node", run_type="chain")
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

@traceable(name="override_node", run_type="chain")
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

@traceable(name="compliance_node", run_type="chain")
async def compliance_node(state: PharmacistState, config: RunnableConfig) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        await llm.ainvoke(f"Log compliance record: {state.get('compliance_log', {})}", config=config)
        return {}
    except Exception as e:
        return {"error": f"compliance_node error: {str(e)}"}

@traceable(name="pvpi_report_node", run_type="chain")
async def pvpi_report_node(state: PharmacistState, config: RunnableConfig) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        if state.get("consent_status") is True:
            res = await llm.ainvoke(f"Generate PVPI submission receipt for: {state.get('pvpi_payload', {})}", config=config)
            pvpi_payload = state.get("pvpi_payload", {})
            pvpi_payload["submission_receipt"] = res.content
            return {"pvpi_payload": pvpi_payload}
        return {}
    except Exception as e:
        return {"error": f"pvpi_report_node error: {str(e)}"}

@traceable(name="knowledge_card_node", run_type="chain")
async def knowledge_card_node(state: PharmacistState, config: RunnableConfig) -> dict:
    llm = config.get("configurable", {}).get("llm")
    try:
        res = await llm.ainvoke(f"Generate a brief 2-sentence clinical knowledge card for {state.get('drug_list')} considering {state.get('naranjo_causality')} causality.", config=config)
        summary = res.content
        print("\n=== KNOWLEDGE CARD ===")
        print(summary)
        print("======================\n")
        return {"knowledge_card": summary}
    except Exception as e:
        return {"error": f"knowledge_card_node error: {str(e)}"}
