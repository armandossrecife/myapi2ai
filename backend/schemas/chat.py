from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AskRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    context: Optional[str] = None
    stream: bool = False

class AskResponse(BaseModel):
    conversation_id: int
    prompt: str
    response: str
    timestamp: str
    model: str
    tokens_used: int

class ConversationItem(BaseModel):
    id: int
    prompt: str
    response: str
    created_at: str

class ConversationsResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ConversationItem]

class ModelInfo(BaseModel):
    model: str
