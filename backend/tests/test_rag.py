import pytest
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.models.query_log import QueryLog

@pytest.fixture
def mock_rag_pipeline():
    with patch("backend.api.v1.endpoints.rag.rag_pipeline") as mock:
        yield mock

def test_rag_query_success(client: TestClient, db: Session, mock_rag_pipeline):
    # Mock RAG response
    mock_source = MagicMock()
    mock_source.page_content = "Este é um trecho de um regimento."
    mock_source.metadata = {"documento": "regimento_teste.pdf", "categoria": "regimento"}
    
    mock_rag_pipeline.query.return_value = ("Esta é a resposta baseada no regimento.", [mock_source])
    
    response = client.post(
        "/api/v1/rag/query",
        json={"question": "O que diz o regimento?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["resposta"] == "Esta é a resposta baseada no regimento."
    assert len(data["fontes"]) == 1
    assert data["fontes"][0]["documento"] == "regimento_teste.pdf"
    
    # Verify DB log
    log = db.query(QueryLog).first()
    assert log is not None
    assert log.question == "O que diz o regimento?"
    assert "regimento_teste.pdf" in log.sources

def test_rag_health(client: TestClient):
    response = client.get("/api/v1/rag/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
