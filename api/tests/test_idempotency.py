import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Application, IdempotencyKey, UpstreamHealth  # noqa: F401
from app.sample_data import SAMPLE_APPLICATION

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.routes.applications.asyncio.create_task", lambda coro: None)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


KAVERI_KEY = "kaveri_key_deepvue_2026"
NEXA_KEY = "nexa_key_deepvue_2026"


class TestIdempotency:
    def test_same_key_returns_same_application(self, client):
        headers = {"X-API-Key": KAVERI_KEY, "Idempotency-Key": "test-key-001"}
        r1 = client.post("/v1/applications", json=SAMPLE_APPLICATION, headers=headers)
        assert r1.status_code == 202
        id1 = r1.json()["application_id"]

        r2 = client.post("/v1/applications", json=SAMPLE_APPLICATION, headers=headers)
        assert r2.status_code == 202
        id2 = r2.json()["application_id"]
        assert id1 == id2

    def test_different_keys_create_different_apps(self, client):
        h1 = {"X-API-Key": KAVERI_KEY, "Idempotency-Key": "key-a"}
        h2 = {"X-API-Key": KAVERI_KEY, "Idempotency-Key": "key-b"}
        r1 = client.post("/v1/applications", json=SAMPLE_APPLICATION, headers=h1)
        r2 = client.post("/v1/applications", json=SAMPLE_APPLICATION, headers=h2)
        assert r1.json()["application_id"] != r2.json()["application_id"]

    def test_customer_isolation(self, client):
        headers = {"X-API-Key": KAVERI_KEY}
        r = client.post("/v1/applications", json=SAMPLE_APPLICATION, headers=headers)
        app_id = r.json()["application_id"]

        other_headers = {"X-API-Key": NEXA_KEY}
        r2 = client.get(f"/v1/applications/{app_id}", headers=other_headers)
        assert r2.status_code == 404

    def test_list_isolation(self, client):
        client.post("/v1/applications", json=SAMPLE_APPLICATION, headers={"X-API-Key": KAVERI_KEY})
        client.post("/v1/applications", json=SAMPLE_APPLICATION, headers={"X-API-Key": NEXA_KEY})

        kaveri_list = client.get("/v1/applications", headers={"X-API-Key": KAVERI_KEY}).json()
        nexa_list = client.get("/v1/applications", headers={"X-API-Key": NEXA_KEY}).json()
        kaveri_ids = {a["application_id"] for a in kaveri_list}
        nexa_ids = {a["application_id"] for a in nexa_list}
        assert kaveri_ids.isdisjoint(nexa_ids)

    def test_invalid_api_key(self, client):
        r = client.post("/v1/applications", json=SAMPLE_APPLICATION, headers={"X-API-Key": "bad_key"})
        assert r.status_code == 401
