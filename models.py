from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Literal
from datetime import datetime
import uuid

# --- Generator Schemas ---

class MCQOption(BaseModel):
    text: str
    label: str  # "A", "B", "C", "D"

class MCQ(BaseModel):
    question: str
    options: List[str] = Field(..., min_items=4, max_items=4)
    correct_index: int = Field(..., ge=0, le=3)

class TeacherNotes(BaseModel):
    learning_objective: str
    common_misconceptions: List[str]

class Explanation(BaseModel):
    text: str
    grade: int

class GeneratorOutput(BaseModel):
    explanation: Explanation
    mcqs: List[MCQ]
    teacher_notes: TeacherNotes

# --- Reviewer Schemas ---

class ReviewFeedbackItem(BaseModel):
    field: str  # e.g., "explanation.text"
    issue: str

class ReviewScores(BaseModel):
    age_appropriateness: int = Field(..., ge=1, le=5)
    correctness: int = Field(..., ge=1, le=5)
    clarity: int = Field(..., ge=1, le=5)
    coverage: int = Field(..., ge=1, le=5)

class ReviewerOutput(BaseModel):
    scores: ReviewScores
    is_passing: bool = Field(..., alias="pass", serialization_alias="pass")
    feedback: List[ReviewFeedbackItem]

    model_config = {
        "populate_by_name": True
    }

# --- Tagger Schemas ---

class TaggerOutput(BaseModel):
    subject: str
    topic: str
    grade: int
    difficulty: Literal["Easy", "Medium", "Hard"]
    content_type: List[str]
    blooms_level: str

# --- Orchestration / Audit Schemas ---

class InputRequest(BaseModel):
    grade: int
    topic: str
    user_id: str = "anonymous"

class AttemptArtifact(BaseModel):
    attempt: int
    draft: Optional[GeneratorOutput] = None
    review: Optional[ReviewerOutput] = None
    refined: Optional[GeneratorOutput] = None
    validation_error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class FinalContent(BaseModel):
    status: Literal["approved", "rejected"]
    content: Optional[GeneratorOutput] = Field(default=None)
    tags: Optional[TaggerOutput] = Field(default=None)

class RunTimestamps(BaseModel):
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None)

class RunArtifact(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    input: InputRequest
    attempts: List[AttemptArtifact] = Field(default_factory=list)
    final: Optional[FinalContent] = Field(default=None)
    timestamps: RunTimestamps = Field(default_factory=RunTimestamps)
