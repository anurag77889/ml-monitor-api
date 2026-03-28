import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import get_application
from app.database import Base, get_db

# Separate in-memory SQLite DB for tests
# In-memory means it vanishes after each test — no cleanup needed
TEST_DATABASE_URL = "sqlite:///./test_ml_monitor.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    """
    Replaces the real get_db dependency with test DB session.
    FastAPI dependency injection makes this seamless.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """
    Runs before every test function.
    Creates all tables fresh, yields, then drops everything.
    Guarantees zero state leakage between tests.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client():
    """
    Provides a TestClient with the test DB injected.
    Use this in every test that makes HTTP requests.
    """
    app = get_application()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


# ── Reusable helper fixtures ──────────────────────────────────────────────────

@pytest.fixture
def registered_user(client: TestClient) -> dict:
    """Register a user and return the response body."""
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
    })
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_headers(client: TestClient, registered_user: dict) -> dict:
    """
    Log in and return Authorization headers.
    Inject this into any test that needs an authenticated request.
    """
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123",
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def registered_model(client: TestClient, auth_headers: dict) -> dict:
    """Register an ML model and return the response body."""
    response = client.post("/models/", json={
        "name": "Test Churn Model",
        "version": "1.0.0",
        "description": "Test model for unit tests",
        "model_type": "classification",
        "drift_threshold": 0.05,
    }, headers=auth_headers)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def logged_prediction(
    client: TestClient,
    auth_headers: dict,
    registered_model: dict,
) -> dict:
    """Log a prediction and return the response body."""
    model_id = registered_model["id"]
    response = client.post(f"/models/{model_id}/predictions/", json={
        "input_data": {"age": 34, "tenure_months": 12},
        "prediction_output": {"label": "churn", "probability": 0.87},
        "confidence_score": 0.87,
        "latency_ms": 42.5,
    }, headers=auth_headers)
    assert response.status_code == 201
    return response.json()