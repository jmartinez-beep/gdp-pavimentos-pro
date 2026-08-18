from gdp_tomo2 import (
    classify_cbr,
    classify_heavy_pct,
    classify_tpd,
    nearby_catalog_options,
    representative_cbr_for_mr,
    select_structures,
)


def test_scope_boundaries():
    assert classify_tpd(0) == "T500"
    assert classify_tpd(500) == "T500"
    assert classify_tpd(501) == "T800"
    assert classify_tpd(3500) == "T3500"
    assert classify_tpd(3501) is None
    assert classify_cbr(2.99) is None
    assert classify_cbr(3.0) == 3
    assert classify_cbr(4.0) == 4
    assert classify_cbr(6.0) == 6
    assert classify_cbr(9.0) == 9
    assert classify_cbr(11.0) == 11
    assert classify_heavy_pct(3.0) == "3"
    assert classify_heavy_pct(15.0) == "15"
    assert classify_heavy_pct(15.01) is None


def test_representative_cbr_for_mr_uses_tomo2_category():
    assert representative_cbr_for_mr(6.5) == 6.0
    assert representative_cbr_for_mr(8.99) == 6.0
    assert representative_cbr_for_mr(2.99) is None


def test_out_of_scope_does_not_emit_structure():
    r = select_structures(tpd=3600, heavy_pct=10, cbr=5, period=10)
    assert r["status"] == "fuera_alcance"
    assert r["alternatives"] == []


def test_non_tabulated_period_does_not_interpolate():
    r = select_structures(tpd=800, heavy_pct=10, cbr=5, period=9)
    assert r["status"] == "fuera_alcance"
    assert r["alternatives"] == []


def test_traced_result_schema():
    r = select_structures(tpd=800, heavy_pct=10, cbr=5, period=10)
    assert r["status"] in {"ok", "sin_alternativa"}
    assert r["table"].startswith("Tabla 301-")
    assert isinstance(r["page"], int)
    for alt in r["alternatives"]:
        tr = alt["trazabilidad"]
        assert "Tabla 301-01" in tr["definicion_estructura"]
        assert "Tabla 301-" in tr["asignacion"]
        assert tr["criterio"]
        assert tr["celda_original"]


def test_empty_cell_remains_unassigned_and_guidance_is_only_tabulated():
    result = select_structures(tpd=1227, heavy_pct=14.8329, cbr=6.1, period=10)
    assert result["status"] == "sin_alternativa"
    assert result["alternatives"] == []

    nearby = nearby_catalog_options(tpd=1227, heavy_pct=14.8329, cbr=6.1, period=10)
    assert nearby
    assert any(row["ajuste"] == "Periodo de diseño" and row["valor"] == 6 for row in nearby)
    assert all(row["estructuras"] for row in nearby)
