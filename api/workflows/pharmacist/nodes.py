from api.workflows.pharmacist.prompts import FDA_SYSTEM_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from api.workflows.pharmacist.schemas import FDADrugInfoResponse
from api.workflows.pharmacist.state import FDAState
import json
from langgraph.types import interrupt
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from sqlmodel import Session

from api.workflows.pharmacist.state import PharmacistState
from api.workflows.pharmacist.prompts import PARSER_SYSTEM_PROMPT, NARANJO_SYSTEM_PROMPT
from api.workflows.pharmacist.schemas import ADRMockResponse, NaranjoAssessment, QCMock
from api.core.database import write_engine
from api.models.user import NaranjoResult
from pydantic import BaseModel, Field

from api.models.report import CreateADR
from api.core.database import write_engine
from sqlmodel import Session
import uuid

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
async def clinical_analysis_node(state: FDAState, config: RunnableConfig) -> dict:
    approved = interrupt("Start Clinical Analysis of the patient? Y/N:")
    if not approved:
        return {"error": "Clinical analysis not approved"}
    llm = config.get("configurable", {}).get("llm")
    if not llm:
        return {"error": "LLM not provided in config"}
        
    try:
        
        api_data = state.get("fda_response", {})
        
        # Naranjo Evaluation
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
                )
                session.add(result)
                session.commit()
        except Exception as db_err:
            print(f"Failed to save NaranjoResult to DB: {db_err}")

        return {
            "naranjo_score": assessment.total_score,
            "naranjo_causality": assessment.causality,
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





@traceable(name="fetch_fda_data_node", run_type="chain")
def fetch_fda_data_node(state: FDAState,config:RunnableConfig) -> dict:
    """
    Fetches drug information and evaluates it against the patient's current symptoms.
    """
    
    drug_list = state.get("drug_list", [])
    symptoms = state.get("symptoms", [])
    
    if not drug_list:
        return {"error": "No drugs provided in the state.", "fda_response": None}

    # Initialize the LLM and bind it to your Pydantic model
    # Use a highly capable model like GPT-4o or Gemini 1.5 Pro for complex schema extraction
    llm = config.get("configurable", {}).get("llm")
    structured_llm = llm.with_structured_output(FDADrugInfoResponse)

   

    prompt = ChatPromptTemplate.from_messages([
        ("system", FDA_SYSTEM_PROMPT),
        ("human", "Drugs to analyze: {drug_list}")
    ])

    # Create the chain
    chain = prompt | structured_llm

    try:
        # Invoke the chain with state variables
         # Pass BOTH variables to invoke
        response: FDADrugInfoResponse = chain.invoke({
            "drug_list": ", ".join(drug_list),
            "symptoms": ", ".join(symptoms) if symptoms else "None reported"
        })
        
        # Return the new keys to update the state
        return {
            "fda_response": response.model_dump(),
            "adr_indicator": response.adr_indicator,
            "error": None
        }
        
    except Exception as e:
        return {
            "error": f"Failed to generate structured FDA data: {str(e)}",
            "fda_response": None
        }


@traceable(name="fda_llm_parser", run_type="chain")
async def fda_llm_parser(state: FDAState, config: RunnableConfig) -> dict:
    llm = config.get("configurable", {}).get("llm")
    if not llm:
        return {"error": "LLM not provided in config"}
        
    class ParsedInput(BaseModel):
        drug_list: list[str] = Field(description="List of drugs mentioned in the input", default_factory=list)
        symptoms_list: list[str] = Field(description="List of symptoms mentioned in the input", default_factory=list)

    structured_llm = llm.with_structured_output(ParsedInput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert pharmacist assistant. Extract a list of drugs and symptoms from the user's input. Return empty lists if none are found."),
        ("human", "{raw_input}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        response: ParsedInput = await chain.ainvoke({"raw_input": state.get("raw_input", "")})
        
        # Merge with existing lists in state if any
        existing_drugs = set(state.get("drug_list", []) or [])
        existing_symptoms = set(state.get("symptoms_list", []) or [])
        
        updated_drugs = list(existing_drugs.union(response.drug_list))
        updated_symptoms = list(existing_symptoms.union(response.symptoms_list))
        
        return {
            "drug_list": updated_drugs,
            "symptoms_list": updated_symptoms,
            "error": None
        }
    except Exception as e:
        print(f"Error in fda_llm_parser: {e}")
        return {"error": f"fda_llm_parser error: {str(e)}"}



@traceable(name="report_adr", run_type="chain")
async def report_adr(state: FDAState, config: RunnableConfig) -> dict:
    approved = interrupt("Do you want to report this ADR to PVPI? Y/N:")
    if approved == "N" or approved == "n":
        return {
            "error": "ADR not reported to PVPI"
        }
    
    try:
        naranjo_score_val = 0
        try:
            naranjo_score_val = int(state.get("naranjo_score", 0))
        except (ValueError, TypeError):
            pass
            
        severity_val = state.get("naranjo_causality", "Unknown")
        
        with Session(write_engine) as session:
            adr_record = CreateADR(
                drug_name=state.get("drug_list", []),
                symptoms=state.get("symptoms_list", []) or state.get("symptoms", []),
                naranjo_score=naranjo_score_val,
                dpdp_score=0,
                overall_score=naranjo_score_val,
                severity=severity_val,
                reported_by_id=uuid.UUID(state.get("pharmacist_id")),
                patient_id=uuid.UUID(state.get("patient_id")),
                thread_id=state.get("thread_id")
            )
            session.add(adr_record)
            session.commit()
        
        return {
            "error": None
        }
    except Exception as e:
        print(f"Error in report_adr: {e}")
        return {"error": f"report_adr error: {str(e)}"}