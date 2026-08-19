import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.database import get_db

client = TestClient(app)

@pytest.fixture
def mock_db():
    # Mock database session
    pass

class TestHealth:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

class TestAuth:
    def test_login_invalid_credentials(self):
        response = client.post("/api/v1/auth/login", json={
            "email": "test@test.com",
            "password": "wrong"
        })
        assert response.status_code == 401

class TestProfiles:
    def test_list_profiles_unauthorized(self):
        response = client.get("/api/v1/profiles")
        assert response.status_code == 403

class TestAnalyses:
    def test_start_analysis_unauthorized(self):
        response = client.post("/api/v1/ai/analyze?photoshoot_id=123")
        assert response.status_code == 403
