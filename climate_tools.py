from __future__ import annotations

from typing import Iterable

import pandas as pd

MONTHS_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


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
