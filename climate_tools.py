from __future__ import annotations

from typing import Iterable

import pandas as pd

MONTHS_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# Tabla 302-02 del GDP-2024 Tomo I, filas que cubren Costa Rica.
DAYLIGHT_FACTORS_NORTH = {
    5.0: [1.02, 0.93, 1.03, 1.02, 1.06, 1.03, 1.06, 1.05, 1.01, 1.03, 0.99, 1.02],
    10.0: [1.00, 0.91, 1.03, 1.03, 1.08, 1.06, 1.08, 1.07, 1.02, 1.02, 0.98, 0.99],
    15.0: [0.97, 0.91, 1.03, 1.04, 1.11, 1.08, 1.12, 1.08, 1.02, 1.01, 0.95, 0.97],
}


def normalize_monthly_temperatures(values: Iterable[float]) -> list[float]:
    vals = [float(v) for v in values]
    if len(vals) != 12:
        raise ValueError("Se requieren exactamente 12 temperaturas mensuales.")
    if any(v < -20.0 or v > 60.0 for v in vals):
        raise ValueError("Las temperaturas mensuales deben estar entre -20 y 60 °C.")
    return vals


def monthly_climate_table(values: Iterable[float], latitude: float, depth_mm: float,
                          ltpp_fn, shrp_fn) -> pd.DataFrame:
    vals = normalize_monthly_temperatures(values)
    rows = []
    for month, air_c in zip(MONTHS_ES, vals):
        rows.append({
            "Mes": month,
            "Aire (°C)": air_c,
            "Pavimento LTPP (°C)": float(ltpp_fn(air_c, latitude, depth_mm)),
            "Pavimento SHRP (°C)": float(shrp_fn(air_c, latitude, depth_mm)),
        })
    return pd.DataFrame(rows)


def representative_temperature(values: Iterable[float]) -> float:
    vals = normalize_monthly_temperatures(values)
    return sum(vals) / len(vals)


def monthly_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    return {
        "air_mean_c": float(df["Aire (°C)"].mean()),
        "air_min_c": float(df["Aire (°C)"].min()),
        "air_max_c": float(df["Aire (°C)"].max()),
        "ltpp_mean_c": float(df["Pavimento LTPP (°C)"].mean()),
        "ltpp_min_c": float(df["Pavimento LTPP (°C)"].min()),
        "ltpp_max_c": float(df["Pavimento LTPP (°C)"].max()),
        "shrp_mean_c": float(df["Pavimento SHRP (°C)"].mean()),
        "shrp_min_c": float(df["Pavimento SHRP (°C)"].min()),
        "shrp_max_c": float(df["Pavimento SHRP (°C)"].max()),
    }


def tmi_climate_class(tmi: float) -> str:
    """Clasificación de la Tabla 302-01, GDP-2024 Tomo I."""
    value = float(tmi)
    if value > 100:
        return "Perhúmedo"
    if value >= 80:
        return "Húmedo (TMI 80–100)"
    if value >= 60:
        return "Húmedo (TMI 60–80)"
    if value >= 40:
        return "Húmedo (TMI 40–60)"
    if value >= 20:
        return "Húmedo (TMI 20–40)"
    if value >= 0:
        return "Subhúmedo a húmedo"
    if value >= -20:
        return "Seco a subhúmedo"
    if value >= -40:
        return "Semiárido"
    if value >= -60:
        return "Árido"
    return "Fuera de la escala tabulada (< -60)"


def _daylight_factors(latitude: float) -> list[float]:
    latitude = min(max(abs(float(latitude)), 5.0), 15.0)
    lower = 5.0 if latitude <= 10.0 else 10.0
    upper = 10.0 if latitude <= 10.0 else 15.0
    ratio = (latitude - lower) / (upper - lower)
    return [
        lo + ratio * (hi - lo)
        for lo, hi in zip(DAYLIGHT_FACTORS_NORTH[lower], DAYLIGHT_FACTORS_NORTH[upper])
    ]


def thornthwaite_tmi_balance(
    temperatures_c: Iterable[float], precipitation_mm: Iterable[float],
    latitude: float, storage_max_mm: float = 200.0,
) -> tuple[pd.DataFrame, dict]:
    """GDP-2024 Sec. 302 water balance and annual Thornthwaite index."""
    temperatures = normalize_monthly_temperatures(temperatures_c)
    precipitation = [max(float(value), 0.0) for value in precipitation_mm]
    if len(precipitation) != 12:
        raise ValueError("Se requieren exactamente 12 precipitaciones mensuales.")
    heat = [(0.2 * max(temp, 0.0)) ** 1.514 for temp in temperatures]
    annual_heat = sum(heat)
    if annual_heat <= 0:
        raise ValueError("El índice anual de calor debe ser mayor que cero.")
    # El signo negativo del término cuadrático reproduce a=2,5347 del Anexo B
    # y corresponde a la formulación de Thornthwaite usada en ese ejemplo.
    exponent = (
        6.75e-7 * annual_heat ** 3
        - 7.71e-5 * annual_heat ** 2
        + 0.017921 * annual_heat
        + 0.49239
    )
    unadjusted = [16.0 * ((10.0 * max(temp, 0.0) / annual_heat) ** exponent) for temp in temperatures]
    factors = _daylight_factors(latitude)
    potential = [
        pe * factor * days / 30.0
        for pe, factor, days in zip(unadjusted, factors, MONTH_DAYS)
    ]

    storage_max = max(float(storage_max_mm), 0.0)
    storage = storage_max
    # Itera años completos hasta que el almacenamiento inicial sea cíclico.
    for _ in range(100):
        initial = storage
        for rain, pe in zip(precipitation, potential):
            storage = min(storage_max, max(0.0, storage + rain - pe))
        if abs(storage - initial) < 1e-7:
            break

    rows = []
    total_excess = total_deficit = 0.0
    for month, temp, rain, heat_index, pe0, factor, pe in zip(
        MONTHS_ES, temperatures, precipitation, heat, unadjusted, factors, potential
    ):
        available = storage + rain
        evap_actual = min(pe, available)
        storage = min(storage_max, max(0.0, available - evap_actual))
        excess = max(0.0, available - evap_actual - storage_max)
        deficit = max(0.0, pe - evap_actual)
        monthly_tmi = (100.0 * excess - 60.0 * deficit) / pe if pe > 0 else 0.0
        total_excess += excess
        total_deficit += deficit
        rows.append({
            "Mes": month, "Precipitación (mm)": rain, "Temperatura (°C)": temp,
            "Índice de calor": heat_index, "ETP no ajustada (mm)": pe0,
            "Factor de corrección": factor, "ETP ajustada (mm)": pe,
            "Almacenamiento (mm)": storage, "Exceso (mm)": excess,
            "Déficit (mm)": deficit, "TMI mensual": monthly_tmi,
        })
    total_pe = sum(potential)
    annual_tmi = (100.0 * total_excess - 60.0 * total_deficit) / total_pe
    summary = {
        "annual_heat_index": annual_heat, "exponent_a": exponent,
        "annual_precipitation_mm": sum(precipitation),
        "annual_pet_mm": total_pe, "annual_excess_mm": total_excess,
        "annual_deficit_mm": total_deficit, "annual_tmi": annual_tmi,
        "climate_class": tmi_climate_class(annual_tmi),
        "storage_max_mm": storage_max,
    }
    return pd.DataFrame(rows), summary
