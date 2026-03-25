from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.db import Base, engine, init_db
from app.main import app


client = TestClient(app)


def _build_workbook_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "BOQ"
    sheet.append(["Description", "Unit", "Quantity"])
    sheet.append(["Excavate foundation trench", "m3", 10])
    sheet.append(["Concrete to strip footing", "m3", 5])
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    init_db()


def test_create_job_and_list_jobs() -> None:
    response = client.post("/jobs", json={"title": "KAA Demo Job", "region": "Nairobi"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "KAA Demo Job"
    assert body["region"] == "Nairobi"

    list_response = client.get("/jobs")
    assert list_response.status_code == 200
    jobs = list_response.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == body["id"]


def test_upload_boq_and_price_job() -> None:
    create_response = client.post("/jobs", json={"title": "Pricing Job", "region": "Nairobi"})
    job_id = create_response.json()["id"]

    upload_response = client.post(
        f"/jobs/{job_id}/files",
        data={"file_type": "boq"},
        files={"file": ("sample.xlsx", _build_workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_response.status_code == 200
    uploaded_job = upload_response.json()
    assert uploaded_job["files"][0]["file_type"] == "boq"

    price_response = client.post(f"/jobs/{job_id}/price-boq")
    assert price_response.status_code == 200
    priced = price_response.json()
    assert priced["job"]["status"] == "priced"
    assert priced["pricing"]["summary"]["item_count"] == 2

    results_response = client.get(f"/jobs/{job_id}/results")
    assert results_response.status_code == 200
    results = results_response.json()
    assert results["summary"]["item_count"] == 2
    assert len(results["items"]) == 2


def test_price_check_and_knowledge_queue() -> None:
    create_response = client.post("/jobs", json={"title": "Insight Job", "region": "Nairobi"})
    job_id = create_response.json()["id"]

    upload_response = client.post(
        f"/jobs/{job_id}/files",
        data={"file_type": "boq"},
        files={"file": ("sample.xlsx", _build_workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_response.status_code == 200

    price_response = client.post(f"/jobs/{job_id}/price-boq")
    assert price_response.status_code == 200

    price_check_response = client.get("/price-check", params={"q": "concrete"})
    assert price_check_response.status_code == 200
    price_check = price_check_response.json()
    assert price_check["scanned_jobs"] == 1
    assert price_check["filtered_rows"] >= 1
    assert any("concrete" in item["description"].lower() or "concrete" in item["matched_description"].lower() for item in price_check["observations"])

    knowledge_response = client.get("/knowledge/candidates")
    assert knowledge_response.status_code == 200
    queue = knowledge_response.json()
    assert queue["scanned_jobs"] == 1
    assert queue["candidate_count"] >= 0
    assert "candidates" in queue
