from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class Category(str, Enum):
    refund = "refund"
    exchange = "exchange"
    store_credit = "store_credit"
    escalate = "escalate"


class Language(str, Enum):
    en = "en"
    ar = "ar"


class ClassificationResult(BaseModel):
    category: Category
    confidence: float = Field(..., ge=0.0, le=1.0, description="0.0 = completely uncertain, 1.0 = certain")
    reasoning: str = Field(..., min_length=5, description="Explanation in same language as input")
    language_detected: Language
    uncertainty_flag: bool = Field(..., description="True when intent is genuinely ambiguous")
    suggested_response_hint: str = Field(..., description="One-sentence English hint for CS agent")


class ClassificationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class ClassificationResponse(BaseModel):
    input: str
    result: Optional[ClassificationResult] = None
    validation_passed: bool
    error: Optional[str] = None
