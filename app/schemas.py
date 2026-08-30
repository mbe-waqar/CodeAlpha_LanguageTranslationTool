"""Request/response contracts for the HTTP API."""

from pydantic import BaseModel, Field

from app.providers import AUTO
from app.translator import MAX_CHARS


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)
    source: str = AUTO
    target: str = "en"


class TranslationResponse(BaseModel):
    text: str
    source: str
    target: str
    provider: str
