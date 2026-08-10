from gdp_tomo2_adapter import alternatives_for_app, selected_trace


def test_adapter_preserves_legacy_contract_and_traceability():
    options, result = alternatives_for_app(tpd=800, heavy_pct=10, cbr=5, period=10)
    assert result["status"] in {"ok", "sin_alternativa"}
    if not options.empty:
        row = options.iloc[0].to_dict()
        for key in ("Código", "Superficie", "Carpeta_cm", "Base_cm", "Subbase_cm"):
            assert key in row
        assert row["Base_cm"] == row["Base_granular_cm"] + row["Base_estabilizada_cm"]
        trace = selected_trace(row)
        assert "Tabla 301-01" in trace["definicion_estructura"]
        assert "Tabla 301-" in trace["asignacion"]
        assert trace["criterio"]
        assert trace["celda_original"]


def test_adapter_does_not_fabricate_out_of_scope_options():
    options, result = alternatives_for_app(tpd=3600, heavy_pct=10, cbr=5, period=10)
    assert result["status"] == "fuera_alcance"
    assert options.empty


def test_adapter_does_not_interpolate_period():
    options, result = alternatives_for_app(tpd=800, heavy_pct=10, cbr=5, period=9)
    assert result["status"] == "fuera_alcance"
    assert options.empty
