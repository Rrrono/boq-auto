from src.normalizer import normalize_text, normalize_unit


def test_normalize_text_handles_ranges_and_case() -> None:
    assert normalize_text("Concrete Mixer 0.3 – 0.7 m³/min") == "concrete mixer 0.3 0.7 m3/min"


def test_normalize_unit_maps_common_values() -> None:
    assert normalize_unit("No") == "nr"
