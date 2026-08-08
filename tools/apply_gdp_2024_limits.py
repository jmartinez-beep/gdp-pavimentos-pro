from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

# Version
text = text.replace('GDP Pavimentos Pro v1.1 Web Ready', 'GDP Pavimentos Pro v1.1.2 Web Ready')
text = text.replace('GDP Pavimentos Pro 2024 — v1.1.1 Piloto Cloud', 'GDP Pavimentos Pro 2024 — v1.1.2 Piloto Cloud')

helper = r'''

def gdp_scope_alerts(active_tomo: str, tpd_total: float, heavy_pct: float, cbr: float,
                     esal: float, years: int) -> list[tuple[str, str]]:
    """Alertas de alcance basadas en GDP-2024 Tomos I y II.

    Devuelve pares (nivel, mensaje), donde nivel es success/info/warning/error.
    Estas verificaciones ayudan a evitar el uso del Tomo II fuera de su alcance y
    orientan la confiabilidad del Tomo I; no sustituyen el criterio profesional.
    """
    alerts: list[tuple[str, str]] = []

    if active_tomo == "Tomo II":
        # GDP-2024 Tomo II: guía simplificada de bajo volumen.
        if tpd_total > 3500:
            alerts.append(("error", f"Tomo II fuera de alcance: TPD = {tpd_total:,.0f} veh/día supera 3 500 veh/día. Utilice Tomo I o realice un diseño específico."))
        elif tpd_total <= 0:
            alerts.append(("error", "Tomo II: el TPD debe ser mayor que cero."))
        else:
            alerts.append(("success", f"TPD dentro del rango de aplicación del Tomo II: {tpd_total:,.0f} veh/día."))

        if heavy_pct > 15.0:
            alerts.append(("error", f"Tomo II fuera de alcance: vehículos pesados = {heavy_pct:.2f}% supera el máximo de 15%. Utilice Tomo I o diseño específico."))
        else:
            alerts.append(("success", f"Porcentaje de vehículos pesados dentro del límite del Tomo II: {heavy_pct:.2f}% ≤ 15%."))

        if cbr < 3.0:
            alerts.append(("error", f"Tomo II: CBR = {cbr:.2f}% es menor que 3%. La subrasante requiere mejoramiento, estabilización o sustitución antes de seleccionar una estructura del catálogo."))
        else:
            alerts.append(("success", f"CBR de subrasante compatible con el alcance simplificado: {cbr:.2f}% ≥ 3%."))

        if esal > 1_500_000:
            alerts.append(("error", f"Tomo II fuera de alcance: ESAL de diseño = {esal:,.0f} supera 1,5 millones. Se requiere diseño específico/Tomo I."))
        else:
            alerts.append(("success", f"ESAL dentro del alcance simplificado: {esal:,.0f} ≤ 1,5 millones."))

        if int(years) not in (6, 8, 10, 12):
            alerts.append(("warning", f"Tomo II: el catálogo GDP-2024 está tabulado directamente para períodos de 6, 8, 10 y 12 años. El período ingresado ({int(years)} años) no tiene selección tabulada directa; verifique o adopte un diseño específico."))
        else:
            alerts.append(("success", f"Período de diseño tabulado en el Tomo II: {int(years)} años."))

    else:  # Tomo I
        # Nivel jerárquico y confiabilidad típica según ESAL de diseño.
        if esal < 3_000_000:
            cat, conf = "Categoría 3", 75
            crack, rut = 35, 16
        elif esal <= 25_000_000:
            cat, conf = "Categoría 2", 85
            crack, rut = 20, 12
        else:
            cat, conf = "Categoría 1", 95
            crack, rut = 10, 10
        alerts.append(("info", f"Tomo I: {cat} por nivel de ESAL. Confiabilidad típica recomendada: {conf}%."))
        alerts.append(("info", f"Criterios de desempeño de referencia al final del período: área agrietada ≤ {crack}% y ahuellamiento total ≤ {rut} mm."))

        if int(years) < 5 or int(years) > 40:
            alerts.append(("warning", "Tomo I: revise el período de análisis respecto al tipo funcional de la ruta."))

    return alerts


def render_gdp_scope_alerts(active_tomo: str, tpd_total: float, heavy_pct: float,
                            cbr: float, esal: float, years: int) -> None:
    st.markdown("#### Verificación automática de alcance — GDP-2024")
    for level, msg in gdp_scope_alerts(active_tomo, tpd_total, heavy_pct, cbr, esal, years):
        getattr(st, level)(msg)
    st.caption("Control de alcance incorporado con base en GDP-2024. Las alertas no sustituyen la revisión integral de la guía ni el criterio del profesional responsable.")
'''

needle = '\ndef technical_validation(active_tomo: str, selected: Dict, exact_match: bool, esal: float, cbr: float, pavement_temp: float, drainage: dict) -> pd.DataFrame:\n'
if 'def gdp_scope_alerts(' not in text:
    if needle not in text:
        raise SystemExit('No se encontró el punto de inserción para las funciones de alerta.')
    text = text.replace(needle, helper + needle, 1)

metric_needle = '''    m5.metric("EEq de diseño", f"{esal:,.0f}", tclass)\n'''
alert_insert = '''    m5.metric("EEq de diseño", f"{esal:,.0f}", tclass)\n\n    render_gdp_scope_alerts(st.session_state.active_tomo, tpd_total, heavy_pct, cbr_design if 'cbr_design' in locals() else 0.0, esal, int(years))\n'''
# The traffic block occurs before the subgrade block in the current app, so cbr_design
# may not exist yet. We add a second definitive block after CBR is calculated instead.
if metric_needle in text and 'render_gdp_scope_alerts(st.session_state.active_tomo, tpd_total' not in text:
    # Do not insert here; leave metrics untouched.
    pass

cbr_needle = '''    x3.metric("Módulo resiliente estimado", f"{mr:.2f} MPa")\n'''
cbr_insert = '''    x3.metric("Módulo resiliente estimado", f"{mr:.2f} MPa")\n\n    render_gdp_scope_alerts(st.session_state.active_tomo, tpd_total, heavy_pct, cbr_design, esal, int(years))\n'''
if 'render_gdp_scope_alerts(st.session_state.active_tomo, tpd_total, heavy_pct, cbr_design, esal, int(years))' not in text:
    if cbr_needle not in text:
        raise SystemExit('No se encontró el bloque de métricas de subrasante.')
    text = text.replace(cbr_needle, cbr_insert, 1)

# Extend technical validation with core Tomo II scope checks.
validation_needle = '''    add("Subrasante", "CBR definido", cbr > 0, "Alta", f"CBR {cbr:.2f}%")\n'''
validation_insert = '''    add("Subrasante", "CBR definido", cbr > 0, "Alta", f"CBR {cbr:.2f}%")\n    if active_tomo == "Tomo II":\n        add("Alcance Tomo II", "ESAL ≤ 1,5 millones", esal <= 1_500_000, "Alta", f"{esal:,.0f} ESAL")\n        add("Alcance Tomo II", "CBR ≥ 3%", cbr >= 3.0, "Alta", f"CBR {cbr:.2f}%")\n'''
if '"ESAL ≤ 1,5 millones"' not in text:
    if validation_needle not in text:
        raise SystemExit('No se encontró el bloque de validación técnica.')
    text = text.replace(validation_needle, validation_insert, 1)

path.write_text(text, encoding='utf-8')
print('Parche GDP-2024 aplicado correctamente a app.py')
