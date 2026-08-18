from construction_costs import cost_summary, layer_thicknesses_cm, quantity_rows


def test_legacy_base_is_granular_without_double_counting():
    layers = layer_thicknesses_cm({"Carpeta_cm": 9, "Base_cm": 27, "Subbase_cm": 20})
    assert layers == {
        "asphalt": 9.0,
        "granular_base": 27.0,
        "stabilized_base": 0.0,
        "granular_subbase": 20.0,
    }


def test_separate_bases_keep_independent_quantities():
    rows = quantity_rows(
        length_m=150,
        width_m=6,
        selected={"Carpeta_cm": 5, "Base_cm": 40, "Base_granular_cm": 20,
                  "Base_estabilizada_cm": 20, "Subbase_cm": 15},
        earthwork_depth_m=0.2,
        drainage_length_m=300,
        marking_length_m=150,
        unit_prices={"site_preparation": 1, "earthworks": 1, "asphalt": 1,
                     "granular_base": 1, "stabilized_base": 1,
                     "granular_subbase": 1, "prime_tack": 1,
                     "drainage": 1, "marking": 1},
    )
    quantities = {row["Rubro"]: row["Cantidad"] for row in rows}
    assert quantities["Base granular colocada"] == 180.0
    assert quantities["Base estabilizada colocada"] == 180.0


def test_summary_exposes_adjustments_and_range():
    result = cost_summary(
        [{"Subtotal": 1_000_000}], preliminaries_pct=5, quality_pct=2,
        overhead_profit_pct=10, contingency_pct=10, escalation_pct=0,
        tax_pct=0, uncertainty_pct=20,
    )
    assert result["basic_direct"] == 1_000_000
    assert result["total"] == 1_177_000
    assert result["low"] == 941_600
    assert result["high"] == 1_412_400
