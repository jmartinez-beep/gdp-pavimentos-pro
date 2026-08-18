import pytest

from climate_catalog import (
    CLIMATE_ZONES, parse_power_climatology, parse_power_point_climatology,
    project_climate_point,
)


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


def test_parse_power_point_climatology_preserves_project_coordinates():
    monthly = {key: 20.0 + index for index, key in enumerate(
        ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    )}
    result = parse_power_point_climatology(
        {"properties": {"parameter": {"T2M": monthly}}},
        9.75543,
        -84.16021,
        "Coordenadas del proyecto (NASA POWER)",
    )
    assert result["latitude"] == 9.75543
    assert result["longitude"] == -84.16021
    assert result["zone"] == "Coordenadas del proyecto (NASA POWER)"
    assert "coordenadas WGS84" in result["source"]


def test_parse_power_point_climatology_converts_daily_rain_to_monthly():
    keys = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    payload = {"properties": {"parameter": {
        "T2M": {key: 24.0 for key in keys},
        "PRECTOTCORR": {key: 2.0 for key in keys},
    }}}
    result = parse_power_point_climatology(payload, 9.8, -84.1, "Proyecto")
    assert result["monthly_precip_mm"][0] == 62.0
    assert result["monthly_precip_mm"][1] == 56.0


def test_project_climate_point_uses_segment_midpoint():
    point = project_climate_point(
        {"geometry_mode": "Tramo (inicio–fin)", "latitude": 9.0, "longitude": -84.0},
        {"start_lat": 9.7, "start_lon": -84.2, "end_lat": 9.8, "end_lon": -84.1},
    )
    assert point == (9.75, -84.15, "Punto medio del tramo")
