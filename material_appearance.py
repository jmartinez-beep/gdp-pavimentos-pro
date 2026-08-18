"""Semantic material appearance for the schematic GDP 3D viewer."""

from __future__ import annotations


def material_kind(name: str) -> str:
    normalized = str(name).lower()
    if "asf" in normalized or "tratamiento" in normalized or "superficie" in normalized:
        return "asphalt"
    if "base estabilizada" in normalized or "suelo cemento" in normalized:
        return "stabilized_base"
    if "subbase" in normalized:
        return "granular_subbase"
    if "base granular" in normalized:
        return "granular_base"
    if "mejorada" in normalized:
        return "improved_subgrade"
    return "subgrade"


def material_style(name: str) -> dict[str, object]:
    """Return deliberately distinct, non-photographic material palettes."""
    kind = material_kind(name)
    styles = {
        "asphalt": dict(
            palette=[[0.0,"#17191a"],[0.20,"#252829"],[0.45,"#343839"],[0.70,"#484c4c"],[0.90,"#606363"],[1.0,"#777976"]],
            seed=11, edge="#111415", rough=0.035,
        ),
        "granular_base": dict(
            palette=[[0.0,"#444b50"],[0.20,"#596268"],[0.45,"#737e83"],[0.70,"#919b9f"],[0.90,"#adb5b7"],[1.0,"#c8cecf"]],
            seed=23, edge="#30383d", rough=0.105,
        ),
        "stabilized_base": dict(
            palette=[[0.0,"#62635f"],[0.25,"#777872"],[0.50,"#8b8c84"],[0.75,"#a0a097"],[1.0,"#b8b7ab"]],
            seed=29, edge="#444641", rough=0.035,
        ),
        "granular_subbase": dict(
            palette=[[0.0,"#655b50"],[0.20,"#786c5e"],[0.45,"#918273"],[0.70,"#aa9a88"],[0.90,"#c0b19d"],[1.0,"#d4c8b6"]],
            seed=37, edge="#4b4239", rough=0.13,
        ),
        "improved_subgrade": dict(
            palette=[[0.0,"#51483e"],[0.25,"#655b4f"],[0.50,"#786d60"],[0.75,"#8c8071"],[1.0,"#a09483"]],
            seed=43, edge="#383129", rough=0.055,
        ),
        "subgrade": dict(
            palette=[[0.0,"#39281e"],[0.20,"#4a3528"],[0.45,"#5e4433"],[0.70,"#745743"],[0.90,"#896b55"],[1.0,"#9d8069"]],
            seed=51, edge="#271a14", rough=0.07,
        ),
    }
    return {**styles[kind], "kind": kind}


def material_description(name: str) -> str:
    return {
        "asphalt": "Matriz asfáltica con agregado fino",
        "granular_base": "Agregado triturado angular y denso",
        "stabilized_base": "Matriz cementada fina y uniforme",
        "granular_subbase": "Agregado heterogéneo gris-marrón",
        "improved_subgrade": "Suelo mejorado de textura fina",
        "subgrade": "Suelo natural fino y estratificado",
    }[material_kind(name)]
