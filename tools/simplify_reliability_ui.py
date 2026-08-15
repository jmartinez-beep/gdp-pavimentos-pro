from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")
old = '''            st.markdown("#### Confiabilidad y criterios de control")
            reliability_default = {3: 75.0, 2: 85.0, 1: 95.0}.get(int(tomo1_category), 75.0)
            rc1, rc2, rc3, rc4 = st.columns(4)
            reliability_pct = rc1.number_input("Confiabilidad del análisis (%)", min_value=50.0, max_value=99.9, value=float(reliability_default), step=1.0, key="design_reliability_pct")
            overall_standard_error = rc2.number_input("Error estándar global (control)", min_value=0.0, max_value=2.0, value=0.45, step=0.05, key="design_standard_error")
            initial_serviceability = rc3.number_input("Serviciabilidad inicial", min_value=0.0, max_value=5.0, value=4.2, step=0.1, key="design_initial_serviceability")
            terminal_serviceability = rc4.number_input("Serviciabilidad terminal", min_value=0.0, max_value=5.0, value=2.5, step=0.1, key="design_terminal_serviceability")
            st.session_state.design_reliability = {
                "reliability_pct": float(reliability_pct), "category_default_pct": float(reliability_default),
                "overall_standard_error": float(overall_standard_error), "initial_serviceability": float(initial_serviceability),
                "terminal_serviceability": float(terminal_serviceability),
            }
'''
new = '''            st.markdown("#### Índice de confiabilidad")
            reliability_default = {3: 75.0, 2: 85.0, 1: 95.0}.get(int(tomo1_category), 75.0)
            reliability_pct = st.number_input(
                "Índice de confiabilidad (%)",
                min_value=50.0,
                max_value=99.9,
                value=float(reliability_default),
                step=1.0,
                key="design_reliability_pct",
                help="Valor inicial según la categoría de diseño del Tomo I; puede ajustarse manualmente.",
            )
            # Parámetros auxiliares conservados internamente para compatibilidad con cálculos,
            # proyectos guardados y exportaciones; ya no se muestran en la interfaz principal.
            previous_reliability = st.session_state.get("design_reliability", {})
            overall_standard_error = float(previous_reliability.get("overall_standard_error", st.session_state.get("design_standard_error", 0.45)))
            initial_serviceability = float(previous_reliability.get("initial_serviceability", st.session_state.get("design_initial_serviceability", 4.2)))
            terminal_serviceability = float(previous_reliability.get("terminal_serviceability", st.session_state.get("design_terminal_serviceability", 2.5)))
            st.session_state.design_reliability = {
                "reliability_pct": float(reliability_pct), "category_default_pct": float(reliability_default),
                "overall_standard_error": float(overall_standard_error), "initial_serviceability": float(initial_serviceability),
                "terminal_serviceability": float(terminal_serviceability),
            }
'''
if old not in text:
    raise SystemExit("No se encontró el bloque esperado de confiabilidad; no se modificó app.py")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("Interfaz de confiabilidad simplificada correctamente.")
