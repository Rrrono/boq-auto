from src.ingestion import normalize_region_name
from src.normalizer import normalize_unit


def test_normalize_region_name_maps_common_aliases() -> None:
    assert normalize_region_name("Nairobi County") == "Nairobi"
    assert normalize_region_name("Kisumu") == "Nyanza"


def test_normalize_unit_handles_import_variants() -> None:
    assert normalize_unit("m^2") == "m2"
    assert normalize_unit("tonne") == "ton"
    assert normalize_unit("kW") == "kw"
