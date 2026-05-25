from fastapi.testclient import TestClient

def test_register(client: TestClient):
    response = client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "password": "StrongPass1!",
        "email": "test@example.com"
    })
    assert response.status_code == 200

def test_login_invalid(client: TestClient):
    response = client.post("/api/v1/auth/login", json={
        "username": "nobody",
        "password": "wrong"
    })
    assert response.status_code == 401
