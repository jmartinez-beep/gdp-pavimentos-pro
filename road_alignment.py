from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving"


class RoadAlignmentError(RuntimeError):
    """Raised when a road-aligned route cannot be obtained or validated."""


@dataclass(frozen=True)
class RoadAlignment:
    coordinates: tuple[tuple[float, float], ...]
    distance_m: float
    duration_s: float


def _validated_waypoints(
    waypoints: Iterable[Sequence[float]],
) -> list[tuple[float, float]]:
    values = [(float(point[0]), float(point[1])) for point in waypoints]
    if not 2 <= len(values) <= 25:
        raise ValueError("Se requieren entre 2 y 25 puntos para ajustar el eje vial.")
    for longitude, latitude in values:
        if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
            raise ValueError("Hay coordenadas WGS84 fuera de rango.")
    return values


def road_route(
    waypoints: Iterable[Sequence[float]],
    *,
    timeout_s: float = 8.0,
    opener: Callable = urlopen,
) -> RoadAlignment:
    """Return a driving route snapped to the OpenStreetMap road network.

    Coordinates use GeoJSON order: ``(longitude, latitude)``.
    """
    points = _validated_waypoints(waypoints)
    coordinate_path = ";".join(f"{lon:.7f},{lat:.7f}" for lon, lat in points)
    query = urlencode({"overview": "full", "geometries": "geojson", "steps": "false"})
    request = Request(
        f"{OSRM_ROUTE_URL}/{coordinate_path}?{query}",
        headers={"User-Agent": "GDP-Pavimentos-Pro/1.1 (road-alignment)"},
    )
    try:
        with opener(request, timeout=float(timeout_s)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RoadAlignmentError("El servicio de ajuste vial no respondió.") from exc

    routes = payload.get("routes") if isinstance(payload, dict) else None
    if payload.get("code") != "Ok" or not routes:
        message = payload.get("message", "No se encontró una ruta entre los puntos.") if isinstance(payload, dict) else "Respuesta inválida del servicio de rutas."
        raise RoadAlignmentError(str(message))

    route = routes[0]
    geometry = route.get("geometry", {})
    coordinates = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
    try:
        resolved = tuple((float(point[0]), float(point[1])) for point in coordinates)
    except (TypeError, ValueError, IndexError) as exc:
        raise RoadAlignmentError("La geometría devuelta por el servicio no es válida.") from exc
    if len(resolved) < 2:
        raise RoadAlignmentError("La ruta ajustada no contiene suficientes vértices.")

    return RoadAlignment(
        coordinates=resolved,
        distance_m=float(route.get("distance", 0.0) or 0.0),
        duration_s=float(route.get("duration", 0.0) or 0.0),
    )
