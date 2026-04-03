"""
Shared pytest fixtures for the Medaea EHR FastAPI test suite.
Uses an in-memory SQLite database so no Postgres is needed to run tests.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_medaea.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("MFA_ENCRYPTION_KEY", "b7-PqUqy4_k2zPUHRpsL2PUWmXglTjdBpOZibh6CT7Q=")
os.environ.setdefault("ENVIRONMENT", "test")

from backend.fastapi_app.main import app
from backend.fastapi_app.core.database import get_db
from backend.fastapi_app.db.models import Base

TEST_DB_URL = "sqlite:///./test_medaea.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def provider_payload():
    return {
        "email": "provider@medaea-test.com",
        "password": "TestProvider123!",
        "first_name": "Test",
        "last_name": "Provider",
        "role": "physician",
    }


@pytest.fixture
def auth_headers(client, provider_payload):
    client.post("/api/v1/auth/signup", json=provider_payload)
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": provider_payload["email"], "password": provider_payload["password"]},
    )
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}
