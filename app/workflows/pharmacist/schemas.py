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
