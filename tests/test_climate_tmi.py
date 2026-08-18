import pytest

from climate_tools import thornthwaite_tmi_balance, tmi_climate_class


def test_tmi_classification_matches_gdp_table_302_01():
    assert tmi_climate_class(101) == "Perhúmedo"
    assert tmi_climate_class(10) == "Subhúmedo a húmedo"
    assert tmi_climate_class(-10) == "Seco a subhúmedo"
    assert tmi_climate_class(-30) == "Semiárido"
    assert tmi_climate_class(-50) == "Árido"


def test_annex_b_example_produces_humid_positive_tmi():
    rain = [70, 85, 90, 120, 198, 247, 157, 211, 361, 327, 102, 50]
    temperatures = [20.7, 21.2, 21.6, 22.7, 23.4, 23.2, 22.8, 22.6, 22.4, 22.3, 21.5, 21.0]
    table, summary = thornthwaite_tmi_balance(temperatures, rain, 10.0)
    assert len(table) == 12
    assert summary["annual_precipitation_mm"] == 2018.0
    assert summary["annual_tmi"] > 80.0
    assert summary["climate_class"].startswith("Húmedo")
    assert summary["exponent_a"] == pytest.approx(2.5347, abs=0.001)
