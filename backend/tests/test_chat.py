import pytest
import json
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.models.user import User
from backend.models.conversation import Conversation

@pytest.mark.asyncio
async def test_ask_question_no_stream(client: TestClient, test_user: User, auth_headers: dict, db: Session, mocker):
    # Mock LLM response
    mock_generate = mocker.patch("backend.api.v1.endpoints.chat.generate_response", new_callable=AsyncMock)
    mock_generate.return_value = "Esta é uma resposta de teste."
    
    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={
            "prompt": "Olá, como você está?",
            "stream": False
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert data["response"] == "Esta é uma resposta de teste."
    
    # Verify in DB
    conv = db.query(Conversation).filter(Conversation.id == data["conversation_id"]).first()
    assert conv is not None
    assert conv.prompt == "Olá, como você está?"
    assert conv.response == "Esta é uma resposta de teste."

@pytest.mark.asyncio
async def test_ask_question_streaming(client: TestClient, test_user: User, auth_headers: dict, db: Session, mocker):
    # Mock LLM streaming response
    async def mock_generator(*args, **kwargs):
        yield "Chunk 1 "
        yield "Chunk 2"
        
    mock_generate = mocker.patch("backend.api.v1.endpoints.chat.generate_response", new_callable=AsyncMock)
    mock_generate.return_value = mock_generator()
    
    response = client.post(
        "/api/v1/chat/ask",
        headers=auth_headers,
        json={
            "prompt": "Diga algo em stream.",
            "stream": True
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Process SSE chunks
    content = response.text
    lines = [line for line in content.split("\n") if line.startswith("data: ")]
    
    chunks_text = ""
    done_received = False
    for line in lines:
        data = json.loads(line[6:])
        if "text" in data:
            chunks_text += data["text"]
        if data.get("done"):
            done_received = True
            
    assert "Chunk 1 Chunk 2" in chunks_text
    assert done_received is True

def test_get_conversations(client: TestClient, test_user: User, auth_headers: dict, db: Session):
    # Create a dummy conversation
    conv = Conversation(
        user_id=test_user.id,
        prompt="Pergunta histórica",
        response="Resposta histórica",
        model_used="test-model"
    )
    db.add(conv)
    db.commit()
    
    response = client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["items"][0]["prompt"] == "Pergunta histórica"

def test_get_model_info(client: TestClient):
    response = client.get("/api/v1/chat/model")
    assert response.status_code == 200
    assert "model" in response.json()
