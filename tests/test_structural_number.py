import pytest

from structural_number import DEFAULT_LAYER_COEFFICIENTS, structural_number_breakdown


def test_default_coefficients_match_agreed_layer_types():
    assert DEFAULT_LAYER_COEFFICIENTS == {
        "asphalt": 0.44,
        "granular_base": 0.14,
        "stabilized_base": 0.20,
        "granular_subbase": 0.10,
    }


def test_granular_and_stabilized_bases_have_independent_contributions():
    result = structural_number_breakdown(
        asphalt_in=4.0,
        granular_base_in=6.0,
        stabilized_base_in=6.0,
        granular_subbase_in=8.0,
    )

    assert result["asphalt"] == pytest.approx(1.76)
    assert result["granular_base"] == pytest.approx(0.84)
    assert result["stabilized_base"] == pytest.approx(1.20)
    assert result["granular_subbase"] == pytest.approx(0.80)
    assert result["total"] == pytest.approx(4.60)


def test_missing_layer_contributes_zero_without_hiding_other_layers():
    result = structural_number_breakdown(
        asphalt_in=0.0,
        granular_base_in=0.0,
        stabilized_base_in=5.0,
        granular_subbase_in=0.0,
    )

    assert result["granular_base"] == 0.0
    assert result["stabilized_base"] == pytest.approx(1.0)
    assert result["total"] == pytest.approx(1.0)
