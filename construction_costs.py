"""Quantity-based conceptual construction cost model for GDP Pavimentos."""

from __future__ import annotations

from typing import Mapping


def layer_thicknesses_cm(selected: Mapping[str, object]) -> dict[str, float]:
    """Return mutually exclusive pavement layer thicknesses.

    Older catalog rows only contain ``Base_cm``.  In that case it is treated as
    granular base; rows that already distinguish both base types keep each one.
    """
    granular = float(selected.get("Base_granular_cm", 0.0) or 0.0)
    stabilized = float(selected.get("Base_estabilizada_cm", 0.0) or 0.0)
    if granular <= 0.0 and stabilized <= 0.0:
        granular = float(selected.get("Base_cm", 0.0) or 0.0)
    return {
        "asphalt": float(selected.get("Carpeta_cm", 0.0) or 0.0),
        "granular_base": granular,
        "stabilized_base": stabilized,
        "granular_subbase": float(selected.get("Subbase_cm", 0.0) or 0.0),
    }


def quantity_rows(
    *,
    length_m: float,
    width_m: float,
    selected: Mapping[str, object],
    earthwork_depth_m: float,
    drainage_length_m: float,
    marking_length_m: float,
    unit_prices: Mapping[str, float],
) -> list[dict[str, float | str]]:
    """Build an auditable bill of conceptual quantities and subtotals."""
    area_m2 = float(length_m) * float(width_m)
    layers = layer_thicknesses_cm(selected)
    definitions = [
        ("Preliminares", "Preparación y replanteo", area_m2, "m²", "site_preparation"),
        ("Movimiento de tierras", "Excavación, conformación y acarreo", area_m2 * float(earthwork_depth_m), "m³", "earthworks"),
        ("Pavimento", "Carpeta asfáltica colocada", area_m2 * layers["asphalt"] / 100.0, "m³", "asphalt"),
        ("Pavimento", "Base granular colocada", area_m2 * layers["granular_base"] / 100.0, "m³", "granular_base"),
        ("Pavimento", "Base estabilizada colocada", area_m2 * layers["stabilized_base"] / 100.0, "m³", "stabilized_base"),
        ("Pavimento", "Subbase granular colocada", area_m2 * layers["granular_subbase"] / 100.0, "m³", "granular_subbase"),
        ("Pavimento", "Imprimación y riego de liga", area_m2, "m²", "prime_tack"),
        ("Drenaje", "Drenaje longitudinal / obras menores", float(drainage_length_m), "m", "drainage"),
        ("Seguridad vial", "Demarcación y señalización básica", float(marking_length_m), "m", "marking"),
    ]
    rows: list[dict[str, float | str]] = []
    for group, item, quantity, unit, price_key in definitions:
        if quantity <= 0.0:
            continue
        unit_price = float(unit_prices.get(price_key, 0.0) or 0.0)
        rows.append({
            "Grupo": group,
            "Rubro": item,
            "Cantidad": quantity,
            "Unidad": unit,
            "Precio unitario": unit_price,
            "Subtotal": quantity * unit_price,
        })
    return rows


def cost_summary(
    rows: list[Mapping[str, object]],
    *,
    preliminaries_pct: float,
    quality_pct: float,
    overhead_profit_pct: float,
    contingency_pct: float,
    escalation_pct: float,
    tax_pct: float,
    uncertainty_pct: float,
) -> dict[str, float]:
    """Calculate a transparent conceptual estimate and uncertainty interval."""
    basic_direct = sum(float(row["Subtotal"]) for row in rows)
    project_direct = basic_direct * (1.0 + (preliminaries_pct + quality_pct) / 100.0)
    overhead_profit = project_direct * overhead_profit_pct / 100.0
    subtotal = project_direct + overhead_profit
    contingency = subtotal * contingency_pct / 100.0
    escalated = (subtotal + contingency) * (1.0 + escalation_pct / 100.0)
    tax = escalated * tax_pct / 100.0
    total = escalated + tax
    spread = max(0.0, uncertainty_pct) / 100.0
    return {
        "basic_direct": basic_direct,
        "preliminaries_quality": project_direct - basic_direct,
        "overhead_profit": overhead_profit,
        "contingency": contingency,
        "escalation": escalated - subtotal - contingency,
        "tax": tax,
        "total": total,
        "low": total * (1.0 - spread),
        "high": total * (1.0 + spread),
    }
