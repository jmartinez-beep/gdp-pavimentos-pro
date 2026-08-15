from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''            st.markdown("#### Índice de confiabilidad")
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
'''

new = '''            st.markdown("#### Confiabilidad y serviciabilidad")
            reliability_default = {3: 75.0, 2: 85.0, 1: 95.0}.get(int(tomo1_category), 75.0)
            serviceability_default = 2.0 if float(tpd_total) < 500.0 else 2.5
            previous_reliability = st.session_state.get("design_reliability", {})
            rc1, rc2 = st.columns(2)
            reliability_pct = rc1.number_input(
                "Índice de confiabilidad (%)",
                min_value=50.0,
                max_value=99.9,
                value=float(reliability_default),
                step=1.0,
                key="design_reliability_pct",
                help="Valor inicial según la categoría de diseño del Tomo I; puede ajustarse manualmente.",
            )
            terminal_serviceability = rc2.number_input(
                "Índice de serviciabilidad",
                min_value=0.0,
                max_value=5.0,
                value=float(serviceability_default),
                step=0.1,
                key="design_terminal_serviceability_visible",
                help="Valor inicial según TPDA de la Tabla 204-03: 2,0 para TPDA menor a 500 y 2,5 para TPDA de 500 o más. Puede ajustarse manualmente.",
            )
            # Parámetros auxiliares conservados internamente para compatibilidad con cálculos,
            # proyectos guardados y exportaciones; solo confiabilidad y serviciabilidad se muestran.
            overall_standard_error = float(previous_reliability.get("overall_standard_error", st.session_state.get("design_standard_error", 0.45)))
            initial_serviceability = float(previous_reliability.get("initial_serviceability", st.session_state.get("design_initial_serviceability", 4.2)))
'''

if old not in text:
    raise SystemExit('No se encontró el bloque esperado de confiabilidad; no se modificó app.py')

text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('Índice de serviciabilidad visible agregado correctamente.')
