import json
from pathlib import Path

from src.audit_logger import log_event


def test_log_event_appends_jsonl_record(tmp_path) -> None:
    audit_path = tmp_path / "logs" / "release_audit.jsonl"

    log_event(
        "Owner",
        "database_release_created",
        {
            "release_id": "prod_20260318_100000",
            "path": "database/releases/demo.xlsx",
            "_audit_log_path": str(audit_path),
        },
    )

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["user"] == "Owner"
    assert payload["action"] == "database_release_created"
    assert payload["details"]["release_id"] == "prod_20260318_100000"
    assert "_audit_log_path" not in payload["details"]


def test_log_event_is_append_only(tmp_path) -> None:
    audit_path = tmp_path / "logs" / "release_audit.jsonl"

    log_event("Owner", "database_release_created", {"release_id": "r1", "_audit_log_path": str(audit_path)})
    log_event("Owner", "database_release_selected", {"release_id": "r0", "_audit_log_path": str(audit_path)})

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
