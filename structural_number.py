from __future__ import annotations


DEFAULT_LAYER_COEFFICIENTS = {
    "asphalt": 0.44,
    "granular_base": 0.14,
    "stabilized_base": 0.20,
    "granular_subbase": 0.10,
}


def structural_number_breakdown(
    *,
    asphalt_in: float,
    granular_base_in: float,
    stabilized_base_in: float,
    granular_subbase_in: float,
    a1: float = DEFAULT_LAYER_COEFFICIENTS["asphalt"],
    a_granular_base: float = DEFAULT_LAYER_COEFFICIENTS["granular_base"],
    a_stabilized_base: float = DEFAULT_LAYER_COEFFICIENTS["stabilized_base"],
    a_granular_subbase: float = DEFAULT_LAYER_COEFFICIENTS["granular_subbase"],
    m_granular_base: float = 1.0,
    m_stabilized_base: float = 1.0,
    m_granular_subbase: float = 1.0,
) -> dict[str, float]:
    """Calcula el aporte SN independiente de cada capa, con espesores en pulgadas."""
    sn_asphalt = float(a1) * max(float(asphalt_in), 0.0)
    sn_granular_base = (
        float(a_granular_base)
        * float(m_granular_base)
        * max(float(granular_base_in), 0.0)
    )
    sn_stabilized_base = (
        float(a_stabilized_base)
        * float(m_stabilized_base)
        * max(float(stabilized_base_in), 0.0)
    )
    sn_granular_subbase = (
        float(a_granular_subbase)
        * float(m_granular_subbase)
        * max(float(granular_subbase_in), 0.0)
    )
    return {
        "asphalt": sn_asphalt,
        "granular_base": sn_granular_base,
        "stabilized_base": sn_stabilized_base,
        "granular_subbase": sn_granular_subbase,
        "total": sn_asphalt + sn_granular_base + sn_stabilized_base + sn_granular_subbase,
    }
