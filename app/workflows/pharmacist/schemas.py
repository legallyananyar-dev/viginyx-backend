from pydantic import BaseModel, Field

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

class QCMock(BaseModel):
    overall: str = Field(description="'pass' or 'fail'")
    flags: list[dict] = Field(description="List of flags")

from pydantic import BaseModel, Field
from typing import Optional, Literal

class FDAContraindication(BaseModel):
    condition: str
    reason: str

class FDADrugInteraction(BaseModel):
    interacting_drug: str
    severity: Literal["minor", "moderate", "major"]
    mechanism: str
    clinical_effect: str

class FDABlackBoxWarning(BaseModel):
    has_warning: bool
    warning_text: Optional[str] = None

class FDADrugInfo(BaseModel):
    drug_name: str
    generic_name: str
    drug_class: str                              # e.g. "Anticoagulant"
    schedule_class: str                          # "H" | "H1" | "X" | "OTC"

    pregnancy_category: Literal["A", "B", "C", "D", "X", "N/A"]
    pregnancy_summary: str                        # one-line plain English

    black_box_warning: FDABlackBoxWarning

    known_adverse_reactions: list[str]            # e.g. ["bleeding","bruising"]
    common_side_effects: list[str]

    drug_interactions: list[FDADrugInteraction]    # structured, not just names
    contraindications: list[FDAContraindication]

    max_daily_dose: Optional[str] = None
    renal_adjustment_required: bool = False
    hepatic_adjustment_required: bool = False

    source: str = "openFDA"                        # or "internal_db"
    last_updated: Optional[str] = None
    error: Optional[str] = None                     # if drug not found

class FDADrugInfoResponse(BaseModel):
    session_id: str
    drugs: list[FDADrugInfo]