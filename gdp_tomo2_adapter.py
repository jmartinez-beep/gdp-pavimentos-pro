from __future__ import annotations

from typing import Any

import pandas as pd

from gdp_tomo2 import select_structures


def _surface_name(alt: dict[str, Any]) -> str:
    if bool(alt.get("tratamiento_superficial")):
        return "Tratamiento superficial"
    if float(alt.get("mac_cm", 0.0)) > 0:
        return "Carpeta asfáltica"
    if float(alt.get("base_estabilizada_cm", 0.0)) > 0:
        return "Base estabilizada"
    return "Estructura GDP-2024"


def _base_type(alt: dict[str, Any]) -> str:
    bg = float(alt.get("base_granular_cm", 0.0))
    be = float(alt.get("base_estabilizada_cm", 0.0))
    if bg > 0 and be > 0:
        return "Base granular + estabilizada"
    if be > 0:
        return "Base estabilizada"
    if bg > 0:
        return "Base granular"
    return "Sin base"


def alternatives_for_app(tpd: float, heavy_pct: float, cbr: float, period: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return official Tomo II alternatives using the legacy app row contract.

    The legacy UI expects Código/Superficie/Carpeta_cm/Base_cm/Subbase_cm.
    This adapter preserves those fields while also retaining the exact GDP-2024
    material split and traceability returned by the normative engine.
    """
    result = select_structures(tpd=tpd, heavy_pct=heavy_pct, cbr=cbr, period=period)
    rows: list[dict[str, Any]] = []
    categories = result.get("categories", {})

    for alt in result.get("alternatives", []):
        trace = alt.get("trazabilidad", {}) or {}
        base_granular = float(alt.get("base_granular_cm", 0.0))
        base_stabilized = float(alt.get("base_estabilizada_cm", 0.0))
        rows.append(
            {
                "Tránsito": categories.get("tpd", ""),
                "Subrasante": f"CBR {categories.get('cbr', '')}%",
                "Opción": alt.get("codigo", ""),
                "Código": alt.get("codigo", ""),
                "Superficie": _surface_name(alt),
                "Carpeta_cm": float(alt.get("mac_cm", 0.0)),
                "Base_cm": base_granular + base_stabilized,
                "Subbase_cm": float(alt.get("subbase_cm", 0.0)),
                "Base_granular_cm": base_granular,
                "Base_estabilizada_cm": base_stabilized,
                "Base_tipo": _base_type(alt),
                "Tratamiento_superficial": bool(alt.get("tratamiento_superficial")),
                "Periodo_anios": int(period),
                "Pesados_categoria": categories.get("pesados", ""),
                "TPD_categoria": categories.get("tpd", ""),
                "CBR_categoria": categories.get("cbr", ""),
                "Fuente_GDP": trace.get("fuente", result.get("source", "")),
                "Decreto": trace.get("decreto", result.get("decree", "")),
                "Tabla_definicion": trace.get("definicion_estructura", ""),
                "Tabla_asignacion": trace.get("asignacion", ""),
                "Criterio_GDP": trace.get("criterio", ""),
                "Celda_original": trace.get("celda_original", ""),
                "Nota_extraccion": trace.get("nota_extraccion", ""),
                "Trazabilidad": trace,
            }
        )

    return pd.DataFrame(rows), result


def selected_trace(selected_row: dict[str, Any] | None) -> dict[str, Any]:
    if not selected_row:
        return {}
    trace = selected_row.get("Trazabilidad")
    if isinstance(trace, dict):
        return trace
    return {
        "fuente": selected_row.get("Fuente_GDP", ""),
        "decreto": selected_row.get("Decreto", ""),
        "definicion_estructura": selected_row.get("Tabla_definicion", ""),
        "asignacion": selected_row.get("Tabla_asignacion", ""),
        "criterio": selected_row.get("Criterio_GDP", ""),
        "celda_original": selected_row.get("Celda_original", ""),
        "nota_extraccion": selected_row.get("Nota_extraccion", ""),
    }
