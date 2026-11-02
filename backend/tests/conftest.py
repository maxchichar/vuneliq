import pytest
from fastapi.testclient import TestClient

from app.main import create_app

@pytest.fixture(scope="session")
def client() -> TestClient:
    """Provides a TestClient instance for testing API endpoints."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client