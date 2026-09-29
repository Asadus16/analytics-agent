"""HTTP request schemas."""

from typing import Optional

from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    narrate: bool = True


class QueryRequest(BaseModel):
    metric: str
    params: Optional[dict] = None
