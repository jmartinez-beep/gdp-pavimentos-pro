from __future__ import annotations

import json
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


MONTH_KEYS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

# Coordenadas urbanas representativas. No deben interpretarse como estaciones IMN.
CLIMATE_ZONES = {
    "Upala": (10.897, -85.015),
    "Los Chiles": (11.033, -84.716),
    "San Carlos": (10.323, -84.430),
    "Liberia": (10.635, -85.438),
    "Nicoya": (10.149, -85.452),
    "Puntarenas": (9.976, -84.838),
    "San José": (9.928, -84.091),
    "Alajuela": (10.016, -84.214),
    "Barva de Heredia": (10.020, -84.123),
    "Cartago": (9.864, -83.919),
    "Buenos Aires": (9.171, -83.334),
    "Aguirre": (9.431, -84.162),
    "Golfito": (8.642, -83.165),
    "Limón": (9.991, -83.036),
    "Orotina": (9.912, -84.523),
}


def parse_power_climatology(payload: dict[str, Any], zone: str) -> dict[str, Any]:
    parameter = payload.get("properties", {}).get("parameter", {}).get("T2M", {})
    monthly = [float(parameter[key]) for key in MONTH_KEYS]
    if len(monthly) != 12 or any(value <= -90 for value in monthly):
        raise ValueError("NASA POWER no devolvió una serie mensual válida.")
    latitude, longitude = CLIMATE_ZONES[zone]
    return {
        "zone": zone,
        "latitude": latitude,
        "longitude": longitude,
        "monthly_c": monthly,
        "annual_c": sum(monthly) / len(monthly),
        "source": "NASA POWER · MERRA-2 (T2M, punto de zona representativa)",
        "period": "Climatología multianual definida por NASA POWER",
    }


@lru_cache(maxsize=32)
def fetch_zone_climatology(zone: str, timeout: float = 12.0) -> dict[str, Any]:
    if zone not in CLIMATE_ZONES:
        raise ValueError(f"Zona climática desconocida: {zone}")
    latitude, longitude = CLIMATE_ZONES[zone]
    query = urlencode({
        "parameters": "T2M",
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "format": "JSON",
    })
    request = Request(
        f"https://power.larc.nasa.gov/api/temporal/climatology/point?{query}",
        headers={"User-Agent": "GDP-Pavimentos-Pro/1.1"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return parse_power_climatology(payload, zone)
