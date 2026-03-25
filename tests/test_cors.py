from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_jobs_preflight_allows_hosted_frontend_origin(monkeypatch) -> None:
    monkeypatch.setenv("BOQ_AUTO_FIREBASE_PROJECT_ID", "demo-project")
    client = TestClient(create_app())

    response = client.options(
        "/jobs",
        headers={
            "Origin": "https://boq-auto-web--demo-project.us-central1.hosted.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://boq-auto-web--demo-project.us-central1.hosted.app"
