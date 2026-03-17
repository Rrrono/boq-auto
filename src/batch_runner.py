"""Batch BOQ pricing helpers."""

from __future__ import annotations

from pathlib import Path

from .engine import PricingEngine
from .models import RunArtifacts
from .utils import slugify


def run_batch(
    engine: PricingEngine,
    db_path: str,
    boq_dir: str,
    out_dir: str,
    region: str | None = None,
    threshold: float | None = None,
    apply_rates: bool | None = None,
) -> list[RunArtifacts]:
    """Price all Excel BOQs in a folder."""
    results: list[RunArtifacts] = []
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    for boq_file in sorted(Path(boq_dir).glob("*.xlsx")):
        if boq_file.name.startswith("~$"):
            continue
        output_file = out_root / f"{slugify(boq_file.stem)}_priced.xlsx"
        artifacts = engine.price_workbook(
            db_path=db_path,
            boq_path=str(boq_file),
            output_path=str(output_file),
            region=region,
            threshold=threshold,
            apply_rates=apply_rates,
        )
        results.append(artifacts)
    return results
