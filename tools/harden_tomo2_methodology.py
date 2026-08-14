from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# TOMO2_METHODOLOGY_HARDENING'
if MARKER in text:
    print('Blindaje Tomo II ya aplicado.')
    raise SystemExit(0)


def replace_once(old: str, new: str, label: str) -> None:
    global text
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: se esperaba 1 coincidencia y se encontraron {n}')
    text = text.replace(old, new, 1)

# 1) Importar las clasificaciones normativas reales del motor Tomo II.
old_import = 'from gdp_tomo2_adapter import alternatives_for_app, selected_trace\n'
new_import = old_import + 'from gdp_tomo2 import classify_tpd, classify_cbr, classify_heavy_pct\n'
replace_once(old_import, new_import, 'importar clasificadores Tomo II')

# 2) Marcador de la migración junto a las funciones de tránsito.
marker_anchor = 'TRAFFIC_RANGES = [\n'
replace_once(marker_anchor, MARKER + '\n' + marker_anchor, 'insertar marcador')

# 3) Periodo: Tomo II solo 6/8/10/12; Tomo I conserva 1-40 años.
old_years = '''    with a:
        years = st.number_input("Periodo de diseño (años)", min_value=1, max_value=40, value=10)
'''
new_years = '''    with a:
        if st.session_state.active_tomo == "Tomo II":
            years = st.selectbox(
                "Periodo de diseño Tomo II (años)", [6, 8, 10, 12], index=2,
                key="tomo2_design_period",
                help="GDP-2024 Tomo II: selección directa de catálogo para 6, 8, 10 o 12 años, sin interpolación."
            )
        else:
            years = st.number_input("Periodo de diseño (años)", min_value=1, max_value=40, value=10, key="tomo1_design_period")
'''
replace_once(old_years, new_years, 'restringir periodo Tomo II')

# 4) No mostrar U1-T5 como clasificación Tomo II. Mostrar categorías normativas TPD/pesados.
old_metrics = '''    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("TPD total", f"{tpd_total:,.0f}")
    m2.metric("Vehículos pesados", f"{heavy_total:,.0f}", f"{heavy_pct:.2f}%")
    m3.metric("Ejes equivalentes diarios", f"{weighted_daily:,.2f}")
    m4.metric("Factor de crecimiento G", f"{gf:,.3f}")
    m5.metric("EEq de diseño", f"{esal:,.0f}", tclass if st.session_state.active_tomo == "Tomo II" else f"Categoría {tomo1_category}")

    if st.session_state.active_tomo == "Tomo I":
'''
new_metrics = '''    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("TPD total", f"{tpd_total:,.0f}")
    m2.metric("Vehículos pesados", f"{heavy_total:,.0f}", f"{heavy_pct:.2f}%")
    m3.metric("Ejes equivalentes diarios", f"{weighted_daily:,.2f}")
    m4.metric("Factor de crecimiento G", f"{gf:,.3f}")
    m5.metric("EEq acumulado", f"{esal:,.0f}", "Dato complementario Tomo II" if st.session_state.active_tomo == "Tomo II" else f"Categoría {tomo1_category}")

    if st.session_state.active_tomo == "Tomo II":
        tomo2_tpd_category = classify_tpd(tpd_total)
        tomo2_heavy_category = classify_heavy_pct(heavy_pct)
        t21, t22, t23 = st.columns(3)
        t21.metric("Categoría TPD — Tomo II", tomo2_tpd_category or "Fuera de alcance")
        t22.metric("Categoría pesados — Tomo II", f"P{tomo2_heavy_category}%" if tomo2_heavy_category else "Fuera de alcance")
        t23.metric("Periodo de catálogo", f"{int(years)} años")
        if tomo2_tpd_category is None:
            st.error("Tomo II: TPD fuera del alcance directo del catálogo (máximo 3500 veh/día en el motor normativo).")
        if tomo2_heavy_category is None:
            st.error("Tomo II: porcentaje de vehículos pesados fuera del alcance directo del catálogo (máximo 15%).")
        st.info("En Tomo II, las categorías normativas visibles son TPD, porcentaje de pesados, CBR y período. La clase U1–T5 por ESAL no se usa para seleccionar el catálogo.")

    if st.session_state.active_tomo == "Tomo I":
'''
replace_once(old_metrics, new_metrics, 'mostrar categorías normativas Tomo II')

# 5) Subrasante: separar S1-S4 auxiliar de categoría normativa CBR 3/4/6/9/11.
old_sclass = '''    sclass = subgrade_class(cbr_design)
    mr_estimated = resilient_modulus(cbr_design)
'''
new_sclass = '''    sclass = subgrade_class(cbr_design)
    mr_estimated = resilient_modulus(cbr_design)
    if st.session_state.active_tomo == "Tomo II":
        tomo2_cbr_category = classify_cbr(cbr_design)
        sgc1, sgc2 = st.columns(2)
        sgc1.metric("Categoría normativa CBR — Tomo II", f"CBR {tomo2_cbr_category}%" if tomo2_cbr_category is not None else "Fuera de alcance")
        sgc2.metric("Clase geotécnica auxiliar", sclass, help="S1–S4 se conserva para visualización y análisis interno; no sustituye la categoría CBR del catálogo Tomo II.")
        if tomo2_cbr_category is None:
            st.error("Tomo II: CBR < 3% queda fuera del alcance directo del catálogo.")
        else:
            st.info("Para la selección Tomo II se utiliza la categoría CBR 3/4/6/9/11 del motor normativo. S1–S4 es una clasificación auxiliar de la aplicación.")
'''
replace_once(old_sclass, new_sclass, 'separar clase geotécnica de categoría Tomo II')

# 6) Blindar Diseño flexible: Tomo II no ejecuta AASHTO-93 ni optimización.
start = text.index('with pflex:\n')
end = text.index('\nwith pperf:', start)
old_block = text[start:end]
body = old_block[len('with pflex:\n'):]
indented = ''.join(('    ' + line if line.strip() else line) for line in body.splitlines(True))
new_block = '''with pflex:
    if active_tomo == "Tomo II":
        st.subheader("Diseño estructural complementario — Tomo II")
        st.success("La estructura activa proviene del catálogo oficial GDP-2024 Tomo II y conserva sus espesores de la alternativa seleccionada.")
        st.info("AASHTO-93, SN, optimización libre de espesores y cribado mecanístico pertenecen al flujo complementario/Tomo I y están bloqueados en este modo para no alterar silenciosamente la alternativa normativa del catálogo.")
        if selected_row:
            t2sum = pd.DataFrame([
                ["Código", selected_row.get("Código", "")],
                ["Superficie", selected_row.get("Superficie", "")],
                ["Carpeta (cm)", selected_row.get("Carpeta_cm", 0)],
                ["Base granular (cm)", selected_row.get("Base_granular_cm", 0)],
                ["Base estabilizada (cm)", selected_row.get("Base_estabilizada_cm", 0)],
                ["Subbase (cm)", selected_row.get("Subbase_cm", 0)],
                ["Tabla de asignación", selected_row.get("Tabla_asignacion", "")],
            ], columns=["Elemento", "Valor"])
            st.dataframe(t2sum, use_container_width=True, hide_index=True)
            st.caption("Para un análisis mecanístico adicional, cambie explícitamente a Tomo I e importe esta estructura para evaluación. Esa evaluación no modifica la condición original de alternativa Tomo II.")
        else:
            st.warning("Seleccione primero una alternativa oficial en 5. Estructura.")
    else:
''' + indented
text = text[:start] + new_block + text[end:]

# 7) Blindar Desempeño: no ejecutar curvas mecanísticas preliminares en Tomo II.
start = text.index('with pperf:\n')
end = text.index('\nwith pcompare:', start)
old_block = text[start:end]
body = old_block[len('with pperf:\n'):]
indented = ''.join(('    ' + line if line.strip() else line) for line in body.splitlines(True))
new_block = '''with pperf:
    if active_tomo == "Tomo II":
        st.subheader("Desempeño y conservación — Tomo II")
        st.info("El Tomo II selecciona estructuras por catálogo. Las curvas mecanístico-empíricas de fatiga/ahuellamiento no forman parte del flujo normativo simplificado y se mantienen desactivadas en este modo.")
        if selected_row:
            st.success(f"Alternativa oficial activa: {selected_row.get('Código','')} · {selected_row.get('Superficie','')}")
            st.caption("Use Costos, Ciclo de vida, Drenaje, Control CR-2020 e Informe para la evaluación complementaria. Si requiere respuesta mecanística, cambie a Tomo I e importe la sección explícitamente.")
        else:
            st.warning("Seleccione una alternativa oficial para continuar.")
    else:
''' + indented
text = text[:start] + new_block + text[end:]

# 8) Payload: exponer categorías normativas Tomo II y evitar etiquetar U/T auxiliar como clase oficial.
old_payload = '''            "class": tclass,
            "design_category": tomo1_category,
            "design_category_label": f"Categoría {tomo1_category}",
'''
new_payload = '''            "class": tclass if active_tomo == "Tomo I" else "No aplica como categoría normativa Tomo II",
            "tomo2_tpd_category": classify_tpd(tpd_total) if active_tomo == "Tomo II" else None,
            "tomo2_heavy_category": classify_heavy_pct(heavy_pct) if active_tomo == "Tomo II" else None,
            "tomo2_cbr_category": classify_cbr(cbr_design) if active_tomo == "Tomo II" else None,
            "tomo2_period_years": int(years) if active_tomo == "Tomo II" else None,
            "design_category": tomo1_category if active_tomo == "Tomo I" else None,
            "design_category_label": f"Categoría {tomo1_category}" if active_tomo == "Tomo I" else "No aplica",
'''
replace_once(old_payload, new_payload, 'actualizar payload Tomo II')

APP.write_text(text, encoding='utf-8')
print('Blindaje metodológico Tomo II aplicado.')
