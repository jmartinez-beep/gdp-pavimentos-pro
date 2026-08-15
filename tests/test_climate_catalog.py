import pytest

from climate_catalog import CLIMATE_ZONES, parse_power_climatology


def test_parse_power_climatology_builds_traceable_catalog_entry():
    values = {key: 20.0 + index / 10 for index, key in enumerate(
        ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    )}
    result = parse_power_climatology(
        {"properties": {"parameter": {"T2M": values}}},
        "Cartago",
    )
    assert result["monthly_c"] == pytest.approx([20.0 + index / 10 for index in range(12)])
    assert result["annual_c"] == pytest.approx(20.55)
    assert result["latitude"] == CLIMATE_ZONES["Cartago"][0]
    assert "NASA POWER" in result["source"]


def test_parse_power_climatology_rejects_missing_months():
    with pytest.raises(KeyError):
        parse_power_climatology({"properties": {"parameter": {"T2M": {"JAN": 20.0}}}}, "Cartago")
