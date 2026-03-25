from __future__ import annotations

import pytest

from app.services.storage import _split_gcs_uri


def test_split_gcs_uri_parses_bucket_and_blob() -> None:
    bucket, blob = _split_gcs_uri("gs://example-bucket/path/to/file.xlsx")
    assert bucket == "example-bucket"
    assert blob == "path/to/file.xlsx"


@pytest.mark.parametrize("value", ["", "https://example.com/file.xlsx", "gs://bucket-only"])
def test_split_gcs_uri_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        _split_gcs_uri(value)
