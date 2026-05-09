import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.models.user import User

def test_register_user(client: TestClient, db: Session):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "strongpassword123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Usuário registrado com sucesso"
    assert "user_id" in data
    
    # Verify in DB
    user = db.query(User).filter(User.username == "newuser").first()
    assert user is not None

def test_register_duplicate_username(client: TestClient, test_user: User):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": test_user.username,
            "email": "another@example.com",
            "password": "password"
        }
    )
    assert response.status_code == 400
    assert "indisponível" in response.json()["detail"]

def test_login_success(client: TestClient, test_user: User):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.username,
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient, test_user: User):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.username,
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 400
    assert "incorretos" in response.json()["detail"].lower()
