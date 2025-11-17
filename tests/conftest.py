import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session

from app.main import app
from app.database import get_session
from app import models  


# BD test
TEST_DATABASE_URL = "sqlite:///./test_pokemon.db"
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)


def get_test_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = get_test_session


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Crear y destruir las tablas para todos los tests."""
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def client():
    # Bucket de rate limit para los tests "normales"
    default_headers = {
        "X-RateLimit-Key": "pokedex-tests",
    }
    with TestClient(app, headers=default_headers) as c:
        yield c


@pytest.fixture(scope="session")
def test_user_payload():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword",
    }


@pytest.fixture(scope="session")
def test_user(client, test_user_payload):
    """Crea un usuario de pruebas (si no existe) y devuelve su payload."""
    resp = client.post("/api/v1/auth/register", json=test_user_payload)
    assert resp.status_code in (201, 400)
    return test_user_payload    



@pytest.fixture(scope="session")
def auth_headers(client, test_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-RateLimit-Key": "pokedex-tests",
    }