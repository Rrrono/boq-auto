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
    first_observation = price_check["observations"][0]
    assert "confidence_band" in first_observation
    assert "flag_reasons" in first_observation
    assert "generic_match_flag" in first_observation
    assert "category_mismatch_flag" in first_observation
    assert "section_mismatch_flag" in first_observation

    knowledge_response = client.get("/knowledge/candidates")
    assert knowledge_response.status_code == 200
    queue = knowledge_response.json()
    assert queue["scanned_jobs"] == 1
    assert queue["candidate_count"] >= 0
    assert "focus_areas" in queue
    assert "candidates" in queue
    if queue["candidates"]:
        first_candidate = queue["candidates"][0]
        assert "confidence_band" in first_candidate
        assert "flag_reasons" in first_candidate
        assert "generic_match_flag" in first_candidate
        assert "category_mismatch_flag" in first_candidate
        assert "section_mismatch_flag" in first_candidate


def test_sync_claim_and_submit_review_tasks() -> None:
    create_response = client.post("/jobs", json={"title": "Reviewer Job", "region": "Nairobi"})
    job_id = create_response.json()["id"]

    upload_response = client.post(
        f"/jobs/{job_id}/files",
        data={"file_type": "boq"},
        files={"file": ("sample.xlsx", _build_workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_response.status_code == 200

    price_response = client.post(f"/jobs/{job_id}/price-boq")
    assert price_response.status_code == 200

    sync_response = client.post(f"/jobs/{job_id}/review-tasks/sync")
    assert sync_response.status_code == 200
    sync_body = sync_response.json()
    assert sync_body["job_id"] == job_id
    assert "tasks" in sync_body
    assert sync_body["tasks"][0]["task_type"] in {"candidate_selection", "match_confirmation", "manual_rate_entry", "category_classification", "section_alignment"}
    assert sync_body["tasks"][0]["task_question"]
    assert isinstance(sync_body["tasks"][0]["response_schema"], list)

    tasks_response = client.get("/review-tasks")
    assert tasks_response.status_code == 200
    tasks = tasks_response.json()
    assert len(tasks) >= 1

    first_task = tasks[0]
    claim_response = client.post(f"/review-tasks/{first_task['id']}/claim")
    assert claim_response.status_code == 200
    claimed = claim_response.json()
    assert claimed["status"] == "claimed"

    submit_response = client.post(
        f"/review-tasks/{first_task['id']}/submit",
        json={
            "decision": "manual_rate",
            "matched_description": "Manual review item",
            "rate": 1250.0,
            "reviewer_note": "Reviewed for marketplace workflow smoke test.",
        },
    )
    assert submit_response.status_code == 200
    submitted = submit_response.json()
    assert submitted["status"] == "submitted"
    assert submitted["submitted_decision"] == "manual_rate"
    assert submitted["submitted_rate"] == 1250.0


def test_review_task_cannot_be_claimed_or_submitted_twice() -> None:
    create_response = client.post("/jobs", json={"title": "Reviewer Guardrail Job", "region": "Nairobi"})
    job_id = create_response.json()["id"]

    client.post(
        f"/jobs/{job_id}/files",
        data={"file_type": "boq"},
        files={"file": ("sample.xlsx", _build_workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    client.post(f"/jobs/{job_id}/price-boq")
    sync_response = client.post(f"/jobs/{job_id}/review-tasks/sync")
    task_id = sync_response.json()["tasks"][0]["id"]

    first_claim = client.post(f"/review-tasks/{task_id}/claim")
    assert first_claim.status_code == 200

    first_submit = client.post(
        f"/review-tasks/{task_id}/submit",
        json={
            "decision": "confirm_match",
            "matched_description": "Confirmed from review queue",
            "rate": None,
            "reviewer_note": "First submission",
        },
    )
    assert first_submit.status_code == 200

    second_claim = client.post(f"/review-tasks/{task_id}/claim")
    assert second_claim.status_code == 409

    second_submit = client.post(
        f"/review-tasks/{task_id}/submit",
        json={
            "decision": "no_good_match",
            "matched_description": "",
            "rate": None,
            "reviewer_note": "Second submission should fail",
        },
    )
    assert second_submit.status_code == 409


def test_review_task_can_move_into_qa_states() -> None:
    create_response = client.post("/jobs", json={"title": "Reviewer QA Job", "region": "Nairobi"})
    job_id = create_response.json()["id"]

    client.post(
        f"/jobs/{job_id}/files",
        data={"file_type": "boq"},
        files={"file": ("sample.xlsx", _build_workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    client.post(f"/jobs/{job_id}/price-boq")
    sync_response = client.post(f"/jobs/{job_id}/review-tasks/sync")
    task_id = sync_response.json()["tasks"][0]["id"]

    client.post(f"/review-tasks/{task_id}/claim")
    client.post(
        f"/review-tasks/{task_id}/submit",
        json={
            "decision": "manual_rate",
            "matched_description": "Manual line",
            "rate": 2250.0,
            "reviewer_note": "Ready for QA and promotion planning.",
        },
    )

    qa_response = client.post(
        f"/review-tasks/{task_id}/qa",
        json={
            "qa_status": "approved",
            "qa_note": "Good reviewer submission.",
        },
    )
    assert qa_response.status_code == 200
    qa_body = qa_response.json()
    assert qa_body["qa_status"] == "approved"
    assert qa_body["qa_note"] == "Good reviewer submission."
    assert qa_body["promotion_target"] == "rate_observation"
    assert qa_body["promotion_status"] == "ready"
    assert qa_body["feedback_action"] == "rejected"

    invalid_qa_response = client.post(
        f"/review-tasks/{task_id}/qa",
        json={
            "qa_status": "invalid_state",
            "qa_note": "",
        },
    )
    assert invalid_qa_response.status_code == 400


def test_unmatched_rows_create_manual_rate_tasks() -> None:
    create_response = client.post("/jobs", json={"title": "Reviewer Task Type Job", "region": "Nairobi"})
    job_id = create_response.json()["id"]

    upload_response = client.post(
        f"/jobs/{job_id}/files",
        data={"file_type": "boq"},
        files={"file": ("sample.xlsx", _build_workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_response.status_code == 200

    price_response = client.post(f"/jobs/{job_id}/price-boq")
    assert price_response.status_code == 200

    sync_response = client.post(f"/jobs/{job_id}/review-tasks/sync")
    assert sync_response.status_code == 200
    tasks = sync_response.json()["tasks"]
    assert tasks
    assert any(task["task_question"] for task in tasks)
    assert any(task["response_schema"] for task in tasks)
