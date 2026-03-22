import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_db
import uuid

base_db_url = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/postgres")
from urllib.parse import urlparse, urlunparse
parsed = urlparse(base_db_url)
test_db_name = "test_db"
test_db_url = urlunparse((
    parsed.scheme,
    parsed.netloc,
    f"/{test_db_name}",
    parsed.params,
    parsed.query,
    parsed.fragment,
))

engine = create_engine(
    test_db_url,
    poolclass=NullPool,
    echo=False
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_test_database():
    admin_engine = create_engine(base_db_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :dbname"), {"dbname": test_db_name})
        if not result.fetchone():
            conn.execute(text(f"CREATE DATABASE {test_db_name}"))
    admin_engine.dispose()

create_test_database()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True, scope="function")
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def auth_token(client):
    unique = uuid.uuid4().hex[:8]
    username = f"user_{unique}"
    email = f"{username}@example.com"
    reg_resp = client.post("/auth/register", json={
        "email": email,
        "username": username,
        "password": "a"
    })
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.json()}"
    token_resp = client.post("/auth/token", data={
        "username": username,
        "password": "a"
    })
    assert token_resp.status_code == 200, f"Token request failed: {token_resp.json()}"
    return token_resp.json()["access_token"]