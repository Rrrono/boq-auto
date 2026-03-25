from __future__ import annotations

from fastapi.testclient import TestClient
from firebase_admin import auth as firebase_auth

from app.db import Base, engine, init_db
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    init_db()


def test_health_stays_public_when_firebase_auth_is_enabled(monkeypatch) -> None:
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_AUTH_ENABLED", "true")
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_PROJECT_ID", "demo-project")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_jobs_require_bearer_token_when_auth_is_enabled(monkeypatch) -> None:
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_AUTH_ENABLED", "true")
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_PROJECT_ID", "demo-project")

    response = client.get("/jobs")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "auth_required"


def test_jobs_reject_invalid_bearer_scheme(monkeypatch) -> None:
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_AUTH_ENABLED", "true")
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_PROJECT_ID", "demo-project")

    response = client.get("/jobs", headers={"Authorization": "Token nope"})

    assert response.status_code == 401
    assert "Bearer" in response.json()["detail"]["message"]


def test_jobs_reject_invalid_firebase_token(monkeypatch) -> None:
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_AUTH_ENABLED", "true")
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_PROJECT_ID", "demo-project")

    def raise_invalid_token(_: str) -> dict:
        raise firebase_auth.InvalidIdTokenError("bad token")

    monkeypatch.setattr("app.auth.verify_firebase_token", raise_invalid_token)

    response = client.get("/jobs", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
    assert "invalid or expired" in response.json()["detail"]["message"]


def test_jobs_accept_valid_firebase_token(monkeypatch) -> None:
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_AUTH_ENABLED", "true")
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_PROJECT_ID", "demo-project")

    monkeypatch.setattr(
        "app.auth.verify_firebase_token",
        lambda token: {"uid": "user-123", "email": "estimator@example.com"} if token == "valid-token" else {"uid": "", "email": None},
    )

    create_response = client.post(
        "/jobs",
        json={"title": "Protected Job", "region": "Nairobi"},
        headers={"Authorization": "Bearer valid-token"},
    )

    assert create_response.status_code == 200
    assert create_response.json()["title"] == "Protected Job"

    list_response = client.get("/jobs", headers={"Authorization": "Bearer valid-token"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
