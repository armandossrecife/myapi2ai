from fastapi.testclient import TestClient
from backend.models.user import User

def test_read_user_me(client: TestClient, test_user: User, auth_headers: dict):
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id

def test_read_user_me_unauthorized(client: TestClient):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
