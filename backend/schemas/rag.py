from pydantic import BaseModel
from typing import List

class QueryRequest(BaseModel):
    question: str

class SourceItem(BaseModel):
    documento: str
    categoria: str
    trecho: str

class QueryResponse(BaseModel):
    resposta: str
    fontes: List[SourceItem]

class HealthResponse(BaseModel):
    status: str
