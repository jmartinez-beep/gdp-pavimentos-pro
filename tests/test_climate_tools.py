import pandas as pd
import pytest

from climate_tools import MONTHS_ES, monthly_climate_table, monthly_summary, representative_temperature


def ltpp_stub(air, lat, depth):
    return air + lat * 0.0 + depth * 0.0 + 10.0


def shrp_stub(air, lat, depth):
    return air + 20.0


def test_representative_temperature_requires_12_values():
    with pytest.raises(ValueError):
        representative_temperature([20.0] * 11)


def test_representative_temperature_is_annual_mean():
    vals = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
    assert representative_temperature(vals) == pytest.approx(sum(vals) / 12.0)


def test_monthly_table_contains_all_months_and_models():
    vals = [24.0] * 12
    df = monthly_climate_table(vals, 9.93, 35.0, ltpp_stub, shrp_stub)
    assert list(df["Mes"]) == MONTHS_ES
    assert len(df) == 12
    assert df["Pavimento LTPP (°C)"].iloc[0] == pytest.approx(34.0)
    assert df["Pavimento SHRP (°C)"].iloc[0] == pytest.approx(44.0)


def test_monthly_summary_reports_extremes():
    vals = list(range(20, 32))
    df = monthly_climate_table(vals, 9.93, 35.0, ltpp_stub, shrp_stub)
    s = monthly_summary(df)
    assert s["air_min_c"] == 20.0
    assert s["air_max_c"] == 31.0
    assert s["ltpp_mean_c"] == pytest.approx(sum(vals) / 12.0 + 10.0)
