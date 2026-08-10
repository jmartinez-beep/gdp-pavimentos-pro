from __future__ import annotations

from functools import lru_cache
from typing import Tuple

from pyproj import CRS, Transformer

CRTM05_EPSG = 5367
WGS84_EPSG = 4326


@lru_cache(maxsize=2)
def _transformer(source_epsg: int, target_epsg: int) -> Transformer:
    """Crea y reutiliza transformadores PROJ usando siempre orden x/y."""
    return Transformer.from_crs(
        CRS.from_epsg(source_epsg),
        CRS.from_epsg(target_epsg),
        always_xy=True,
    )


def crtm05_to_wgs84(easting: float, northing: float) -> Tuple[float, float]:
    """Convierte CRTM05 (EPSG:5367) a WGS84 (EPSG:4326).

    Retorna (longitud, latitud) en grados decimales.
    """
    lon, lat = _transformer(CRTM05_EPSG, WGS84_EPSG).transform(float(easting), float(northing))
    return float(lon), float(lat)


def wgs84_to_crtm05(longitude: float, latitude: float) -> Tuple[float, float]:
    """Conversión inversa para validación y compatibilidad futura.

    Retorna (Este, Norte) en metros CRTM05.
    """
    easting, northing = _transformer(WGS84_EPSG, CRTM05_EPSG).transform(float(longitude), float(latitude))
    return float(easting), float(northing)


def is_plausible_costa_rica_wgs84(longitude: float, latitude: float) -> bool:
    """Control amplio para detectar errores evidentes de digitación, no un límite legal."""
    return -86.2 <= float(longitude) <= -82.3 and 8.0 <= float(latitude) <= 11.3
