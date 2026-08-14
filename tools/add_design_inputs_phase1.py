from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

MARKER = "# DESIGN_DATA_PHASE1"
if MARKER in text:
    print("Fase 1 de datos de diseño ya aplicada; no hay cambios.")
    raise SystemExit(0)


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: se esperaba 1 coincidencia y se encontraron {count}")
    text = text.replace(old, new, 1)


# 1) Geometría y datos funcionales del proyecto.
replace_once(
'''        road_type = st.selectbox("Tipo de vía", ["Camino de bajo volumen", "Urbanización", "Vía local", "Otro"])
        pavement_type = st.selectbox("Tipo de pavimento", ["Flexible", "Semirrígido", "Por definir"])

    st.markdown("### Ubicación geográfica y conversión de coordenadas")''',
'''        road_type = st.selectbox("Tipo de vía", ["Camino de bajo volumen", "Urbanización", "Vía local", "Otro"])
        pavement_type = st.selectbox("Tipo de pavimento", ["Flexible", "Semirrígido", "Por definir"])

    # DESIGN_DATA_PHASE1
    st.markdown("### Geometría y configuración funcional del tramo")
    g1, g2, g3, g4 = st.columns(4)
    project_length_m = g1.number_input("Longitud de diseño (m)", min_value=1.0, value=150.0, step=10.0, key="project_design_length")
    lane_width_m = g2.number_input("Ancho de carril (m)", min_value=2.0, max_value=6.0, value=3.0, step=0.1, key="project_lane_width")
    number_lanes = g3.number_input("Número de carriles", min_value=1, max_value=12, value=2, step=1, key="project_number_lanes")
    traffic_directions = g4.selectbox("Sentidos de circulación", ["Dos sentidos", "Un sentido"], key="project_traffic_directions")
    g5, g6, g7, g8 = st.columns(4)
    shoulder_width_m = g5.number_input("Espaldón por lado (m)", min_value=0.0, max_value=5.0, value=0.0, step=0.25, key="project_shoulder_width")
    project_cross_slope_pct = g6.number_input("Pendiente transversal (%)", min_value=0.0, max_value=15.0, value=2.0, step=0.1, key="project_cross_slope")
    project_long_slope_pct = g7.number_input("Pendiente longitudinal media (%)", min_value=-20.0, max_value=20.0, value=0.0, step=0.1, key="project_long_slope")
    functional_class = g8.selectbox("Condición funcional", ["Nueva construcción", "Reconstrucción", "Rehabilitación", "Evaluación preliminar"], key="project_functional_condition")
    project_width_m = float(lane_width_m) * int(number_lanes) + 2.0 * float(shoulder_width_m)
    st.caption(f"Ancho geométrico de referencia calculado: {project_width_m:.2f} m. Estos datos se usan como trazabilidad y como valores iniciales en costos/exportación.")
    st.session_state.project_geometry = {
        "length_m": float(project_length_m), "lane_width_m": float(lane_width_m),
        "number_lanes": int(number_lanes), "traffic_directions": traffic_directions,
        "shoulder_width_m": float(shoulder_width_m), "paved_reference_width_m": float(project_width_m),
        "cross_slope_pct": float(project_cross_slope_pct), "longitudinal_slope_pct": float(project_long_slope_pct),
        "functional_condition": functional_class,
    }

    st.markdown("### Ubicación geográfica y conversión de coordenadas")''',
"agregar geometría del proyecto",
)

# 2) Caracterización geotécnica y selección del Mr de diseño.
replace_once(
'''    sclass = subgrade_class(cbr_design)
    mr = resilient_modulus(cbr_design)
    x1, x2, x3 = st.columns(3)
    x1.metric("CBR de diseño", f"{cbr_design:.2f}%")
    x2.metric("Rango de subrasante", sclass)
    x3.metric("Módulo resiliente estimado", f"{mr:.2f} MPa")

    render_gdp_scope_alerts''',
'''    sclass = subgrade_class(cbr_design)
    mr_estimated = resilient_modulus(cbr_design)

    st.markdown("#### Caracterización geotécnica complementaria")
    sg1, sg2, sg3, sg4 = st.columns(4)
    soil_sucs = sg1.text_input("Clasificación SUCS", value="", key="subgrade_sucs")
    soil_aashto = sg2.text_input("Clasificación AASHTO", value="", key="subgrade_aashto")
    liquid_limit = sg3.number_input("Límite líquido LL (%)", min_value=0.0, max_value=150.0, value=0.0, step=1.0, key="subgrade_ll")
    plasticity_index = sg4.number_input("Índice plástico IP (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="subgrade_pi")
    sg5, sg6, sg7, sg8 = st.columns(4)
    natural_moisture = sg5.number_input("Humedad natural (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="subgrade_moisture")
    max_dry_density = sg6.number_input("Densidad seca máxima (kg/m³)", min_value=0.0, max_value=3000.0, value=0.0, step=10.0, key="subgrade_mdd")
    subgrade_water_table = sg7.number_input("Nivel freático investigado (m)", min_value=0.0, max_value=50.0, value=2.0, step=0.1, key="subgrade_water_table")
    mr_source = sg8.selectbox("Fuente del módulo resiliente", ["Estimado a partir del CBR", "Ensayo de laboratorio/campo", "Valor documentado del proyecto"], key="subgrade_mr_source")
    measured_mr = st.number_input("Módulo resiliente documentado Mr (MPa, 0 = usar estimación por CBR)", min_value=0.0, max_value=2000.0, value=0.0, step=1.0, key="subgrade_measured_mr")
    mr = float(measured_mr) if measured_mr > 0 and mr_source != "Estimado a partir del CBR" else float(mr_estimated)

    x1, x2, x3, x4 = st.columns(4)
    x1.metric("CBR de diseño", f"{cbr_design:.2f}%")
    x2.metric("Rango de subrasante", sclass)
    x3.metric("Mr estimado por CBR", f"{mr_estimated:.2f} MPa")
    x4.metric("Mr usado en diseño", f"{mr:.2f} MPa")
    st.session_state.subgrade_details = {
        "sucs": soil_sucs, "aashto": soil_aashto, "liquid_limit_pct": float(liquid_limit),
        "plasticity_index_pct": float(plasticity_index), "natural_moisture_pct": float(natural_moisture),
        "max_dry_density_kg_m3": float(max_dry_density), "water_table_m": float(subgrade_water_table),
        "mr_estimated_mpa": float(mr_estimated), "mr_design_mpa": float(mr), "mr_source": mr_source,
    }
    if measured_mr <= 0 and mr_source != "Estimado a partir del CBR":
        st.warning("Se indicó una fuente documentada de Mr, pero no se ingresó el valor. Se mantiene temporalmente la estimación por CBR.")

    render_gdp_scope_alerts''',
"ampliar subrasante",
)

# 3) Propiedades de materiales del Tomo I, almacenadas junto con la sección propuesta.
replace_once(
'''        st.session_state.tomo1_structure = proposed
        st.session_state.selected_row = proposed
        st.session_state.total_thickness = total_thickness
        selected_row = proposed

        m1, m2, m3, m4 = st.columns(4)''',
'''        st.session_state.tomo1_structure = proposed
        st.session_state.selected_row = proposed
        st.session_state.total_thickness = total_thickness
        selected_row = proposed

        st.markdown("#### Propiedades de materiales para la evaluación Tomo I")
        st.caption("Registre propiedades representativas y su fuente. Estos valores quedan trazables en el expediente; no sustituyen ensayos ni calibración mecanístico-empírica.")
        mt1, mt2, mt3, mt4 = st.columns(4)
        asphalt_dynamic_modulus = mt1.number_input("Módulo dinámico de mezcla E* de referencia (MPa)", min_value=0.0, max_value=50000.0, value=3500.0, step=100.0, key="mat_asphalt_e")
        asphalt_poisson = mt2.number_input("Poisson mezcla asfáltica", min_value=0.10, max_value=0.49, value=0.35, step=0.01, key="mat_asphalt_nu")
        base_mr = mt3.number_input("Mr base granular (MPa)", min_value=0.0, max_value=2000.0, value=200.0, step=10.0, key="mat_base_mr")
        subbase_mr = mt4.number_input("Mr subbase (MPa)", min_value=0.0, max_value=1500.0, value=120.0, step=10.0, key="mat_subbase_mr")
        mt5, mt6, mt7 = st.columns(3)
        stabilized_modulus = mt5.number_input("Módulo base estabilizada (MPa)", min_value=0.0, max_value=50000.0, value=3000.0 if base_stabilized_cm > 0 else 0.0, step=100.0, key="mat_stabilized_e")
        stabilized_strength = mt6.number_input("Resistencia de referencia base estabilizada (MPa)", min_value=0.0, max_value=50.0, value=3.5 if base_stabilized_cm > 0 else 0.0, step=0.1, key="mat_stabilized_strength")
        material_source = mt7.text_input("Fuente / informe de materiales", value="", key="mat_source")
        material_notes = st.text_area("Notas de caracterización de materiales", value="", height=80, key="mat_notes")
        st.session_state.design_materials = {
            "asphalt_dynamic_modulus_mpa": float(asphalt_dynamic_modulus), "asphalt_poisson": float(asphalt_poisson),
            "base_mr_mpa": float(base_mr), "subbase_mr_mpa": float(subbase_mr),
            "stabilized_modulus_mpa": float(stabilized_modulus), "stabilized_strength_mpa": float(stabilized_strength),
            "source": material_source, "notes": material_notes, "master_curve_confirmed": bool(master_curve_confirmed),
        }
        if tomo1_category in (1, 2) and not master_curve_confirmed:
            st.warning("Categorías 1 y 2: complete la caracterización térmica/dinámica de la mezcla antes de emitir el diseño como definitivo.")
        if t1_type == "Semirrígido" and base_stabilized_cm > 0 and stabilized_modulus <= 0:
            st.error("La base estabilizada requiere un módulo documentado para la evaluación estructural.")

        m1, m2, m3, m4 = st.columns(4)''',
"agregar propiedades de materiales",
)

# 4) Confiabilidad y parámetros de control en Diseño flexible.
replace_once(
'''    if selected_row:
        f1,f2,f3,f4 = st.columns(4)''',
'''    if selected_row:
        st.markdown("#### Confiabilidad y criterios de control")
        reliability_default = {3: 75.0, 2: 85.0, 1: 95.0}.get(int(tomo1_category), 75.0)
        rc1, rc2, rc3, rc4 = st.columns(4)
        reliability_pct = rc1.number_input("Confiabilidad del análisis (%)", min_value=50.0, max_value=99.9, value=float(reliability_default), step=1.0, key="design_reliability")
        overall_standard_error = rc2.number_input("Error estándar global (control)", min_value=0.0, max_value=2.0, value=0.45, step=0.05, key="design_standard_error")
        initial_serviceability = rc3.number_input("Serviciabilidad inicial", min_value=0.0, max_value=5.0, value=4.2, step=0.1, key="design_initial_serviceability")
        terminal_serviceability = rc4.number_input("Serviciabilidad terminal", min_value=0.0, max_value=5.0, value=2.5, step=0.1, key="design_terminal_serviceability")
        st.session_state.design_reliability = {
            "reliability_pct": float(reliability_pct), "category_default_pct": float(reliability_default),
            "overall_standard_error": float(overall_standard_error), "initial_serviceability": float(initial_serviceability),
            "terminal_serviceability": float(terminal_serviceability),
        }
        if reliability_pct < reliability_default:
            st.warning(f"La confiabilidad ingresada ({reliability_pct:.0f}%) es menor al valor de control preliminar asociado a Categoría {tomo1_category} ({reliability_default:.0f}%). Documente la justificación.")

        f1,f2,f3,f4 = st.columns(4)''',
"agregar confiabilidad",
)

# 5) Guardar confiabilidad dentro del diseño flexible.
replace_once(
'''        st.session_state.flex_design={"a1":a1,"a2":a2,"a3":a3,"m2":m2,"m3":m3,"sn":sn_total}''',
'''        st.session_state.flex_design={"a1":a1,"a2":a2,"a3":a3,"m2":m2,"m3":m3,"sn":sn_total,"reliability_pct":reliability_pct,"overall_standard_error":overall_standard_error,"initial_serviceability":initial_serviceability,"terminal_serviceability":terminal_serviceability}''',
"guardar confiabilidad en diseño flexible",
)

# 6) Sincronizar costos con la geometría definida en Proyecto.
replace_once(
'''        length_m = st.number_input("Longitud (m)", min_value=1.0, value=150.0, step=10.0)
    with q2:
        width_m = st.number_input("Ancho pavimentado (m)", min_value=1.0, value=6.0, step=0.5)''',
'''        length_m = st.number_input("Longitud (m)", min_value=1.0, value=float(project_length_m), step=10.0)
    with q2:
        width_m = st.number_input("Ancho pavimentado (m)", min_value=1.0, value=float(project_width_m), step=0.5)''',
"sincronizar geometría con costos",
)

# 7) Ampliar validación técnica con datos de geometría, materiales y confiabilidad.
replace_once(
'''def technical_validation(active_tomo: str, selected: Dict, exact_match: bool, esal: float, cbr: float, pavement_temp: float, drainage: dict) -> pd.DataFrame:
    """Matriz trazable de validación. No reemplaza la revisión profesional."""
    checks = []''',
'''def technical_validation(active_tomo: str, selected: Dict, exact_match: bool, esal: float, cbr: float, pavement_temp: float, drainage: dict,
                         geometry: dict | None = None, subgrade_details: dict | None = None,
                         materials: dict | None = None, reliability: dict | None = None) -> pd.DataFrame:
    """Matriz trazable de validación. No reemplaza la revisión profesional."""
    geometry = geometry or {}
    subgrade_details = subgrade_details or {}
    materials = materials or {}
    reliability = reliability or {}
    checks = []''',
"ampliar firma de validación",
)
replace_once(
'''    add("Alcance", "Metodología seleccionada", active_tomo in ("Tomo I","Tomo II"), "Alta", active_tomo)
    add("Catálogo", "Coincidencia exacta tránsito-subrasante", bool(exact_match), "Alta", f"Código {selected.get('Código','—')}")
    add("Tránsito", "ESAL mayor que cero", esal > 0, "Alta", f"{esal:,.0f} ESAL")
    add("Subrasante", "CBR definido", cbr > 0, "Alta", f"CBR {cbr:.2f}%")''',
'''    add("Alcance", "Metodología seleccionada", active_tomo in ("Tomo I","Tomo II"), "Alta", active_tomo)
    if active_tomo == "Tomo II":
        add("Catálogo", "Coincidencia exacta tránsito-subrasante", bool(exact_match), "Alta", f"Código {selected.get('Código','—')}")
    else:
        add("Jerarquía Tomo I", "Categoría de diseño definida por ESAL", esal > 0, "Alta", f"Categoría {tomo1_design_category(esal)}")
    add("Tránsito", "ESAL mayor que cero", esal > 0, "Alta", f"{esal:,.0f} ESAL")
    add("Geometría", "Longitud y ancho de referencia definidos", float(geometry.get("length_m",0) or 0) > 0 and float(geometry.get("paved_reference_width_m",0) or 0) > 0, "Media", f"L={geometry.get('length_m','—')} m · B={geometry.get('paved_reference_width_m','—')} m")
    add("Subrasante", "CBR definido", cbr > 0, "Alta", f"CBR {cbr:.2f}%")
    add("Subrasante", "Fuente de Mr documentada", bool(subgrade_details.get("mr_source")), "Media", str(subgrade_details.get("mr_source","Sin definir")))
    if active_tomo == "Tomo I":
        add("Materiales", "Módulo de mezcla asfáltica registrado", float(materials.get("asphalt_dynamic_modulus_mpa",0) or 0) > 0, "Alta", f"E*={float(materials.get('asphalt_dynamic_modulus_mpa',0) or 0):.0f} MPa")
        add("Materiales", "Fuente de caracterización documentada", bool(str(materials.get("source","")).strip()), "Media", str(materials.get("source","Sin definir")))
        add("Confiabilidad", "Parámetro de confiabilidad definido", float(reliability.get("reliability_pct",0) or 0) >= 50, "Alta", f"R={float(reliability.get('reliability_pct',0) or 0):.0f}%")''',
"agregar verificaciones de diseño",
)
replace_once(
'''        validation_df = technical_validation(active_tomo, selected_row, exact_match, esal, cbr_design, tp_ltpp, st.session_state.get("drainage", {}))''',
'''        validation_df = technical_validation(
            active_tomo, selected_row, exact_match, esal, cbr_design, tp_ltpp,
            st.session_state.get("drainage", {}), st.session_state.get("project_geometry", {}),
            st.session_state.get("subgrade_details", {}), st.session_state.get("design_materials", {}),
            st.session_state.get("design_reliability", {}),
        )''',
"pasar nuevos datos a validación",
)

# 8) Exportación Excel: hojas adicionales.
replace_once(
'''        pd.DataFrame([payload["subgrade"]]).to_excel(writer, sheet_name="Subrasante", index=False)
        climate_payload = dict(payload.get("climate", {}))''',
'''        pd.DataFrame([payload["subgrade"]]).to_excel(writer, sheet_name="Subrasante", index=False)
        pd.DataFrame([payload.get("geometry", {})]).to_excel(writer, sheet_name="Geometria", index=False)
        pd.DataFrame([payload.get("materials", {})]).to_excel(writer, sheet_name="Materiales", index=False)
        pd.DataFrame([payload.get("reliability", {})]).to_excel(writer, sheet_name="Confiabilidad", index=False)
        climate_payload = dict(payload.get("climate", {}))''',
"agregar hojas de diseño a Excel",
)

# 9) Payload completo para trazabilidad.
replace_once(
'''            "pavement_type": pavement_type,
            "coordinate_system_input": coordinate_system,''',
'''            "pavement_type": pavement_type,
            "length_m": float(project_length_m),
            "lane_width_m": float(lane_width_m),
            "number_lanes": int(number_lanes),
            "traffic_directions": traffic_directions,
            "shoulder_width_m": float(shoulder_width_m),
            "paved_reference_width_m": float(project_width_m),
            "cross_slope_pct": float(project_cross_slope_pct),
            "longitudinal_slope_pct": float(project_long_slope_pct),
            "functional_condition": functional_class,
            "coordinate_system_input": coordinate_system,''',
"agregar geometría al proyecto exportado",
)
replace_once(
'''        "subgrade": {"cbr": cbr_design, "class": sclass, "mr": mr},
        "climate": {''',
'''        "subgrade": {"cbr": cbr_design, "class": sclass, "mr": mr, **st.session_state.get("subgrade_details", {})},
        "geometry": st.session_state.get("project_geometry", {}),
        "materials": st.session_state.get("design_materials", {}) if active_tomo == "Tomo I" else {},
        "reliability": st.session_state.get("design_reliability", {}) if active_tomo == "Tomo I" else {},
        "climate": {''',
"ampliar payload de diseño",
)

# 10) Informe HTML: secciones de geometría, subrasante ampliada, materiales y confiabilidad.
replace_once(
'''    subgrade = payload["subgrade"]
    selected = payload.get("selected")
    costs = payload.get("costs", {})''',
'''    subgrade = payload["subgrade"]
    selected = payload.get("selected")
    geometry = payload.get("geometry", {})
    materials = payload.get("materials", {})
    reliability = payload.get("reliability", {})
    costs = payload.get("costs", {})''',
"leer nuevos datos en informe HTML",
)
replace_once(
'''<h2>1. Parámetros de tránsito</h2>''',
'''<h2>0. Geometría y configuración del proyecto</h2>
<table>
<tr><th>Longitud de diseño</th><td>{geometry.get('length_m', 0):,.1f} m</td></tr>
<tr><th>Ancho de referencia</th><td>{geometry.get('paved_reference_width_m', 0):,.2f} m</td></tr>
<tr><th>Número de carriles</th><td>{geometry.get('number_lanes', 0)}</td></tr>
<tr><th>Sentidos</th><td>{geometry.get('traffic_directions', '')}</td></tr>
<tr><th>Pendiente transversal</th><td>{geometry.get('cross_slope_pct', 0):.2f}%</td></tr>
<tr><th>Pendiente longitudinal media</th><td>{geometry.get('longitudinal_slope_pct', 0):.2f}%</td></tr>
</table>

<h2>1. Parámetros de tránsito</h2>''',
"agregar geometría al informe HTML",
)
replace_once(
'''<tr><th>Módulo resiliente estimado</th><td>{subgrade['mr']:.2f} MPa</td></tr>
</table>

<h2>3. Estructura seleccionada</h2>''',
'''<tr><th>Módulo resiliente de diseño</th><td>{subgrade['mr']:.2f} MPa</td></tr>
<tr><th>Fuente de Mr</th><td>{subgrade.get('mr_source','')}</td></tr>
<tr><th>SUCS</th><td>{subgrade.get('sucs','')}</td></tr>
<tr><th>AASHTO</th><td>{subgrade.get('aashto','')}</td></tr>
<tr><th>LL / IP</th><td>{subgrade.get('liquid_limit_pct',0):.1f}% / {subgrade.get('plasticity_index_pct',0):.1f}%</td></tr>
</table>

<h2>3. Estructura seleccionada</h2>''',
"ampliar subrasante en informe HTML",
)
replace_once(
'''<h2>4. Estimación económica</h2>''',
'''<h2>4. Materiales y confiabilidad</h2>
<table>
<tr><th>E* mezcla asfáltica</th><td>{materials.get('asphalt_dynamic_modulus_mpa',0):,.0f} MPa</td></tr>
<tr><th>Mr base granular</th><td>{materials.get('base_mr_mpa',0):,.0f} MPa</td></tr>
<tr><th>Mr subbase</th><td>{materials.get('subbase_mr_mpa',0):,.0f} MPa</td></tr>
<tr><th>Módulo base estabilizada</th><td>{materials.get('stabilized_modulus_mpa',0):,.0f} MPa</td></tr>
<tr><th>Fuente de materiales</th><td>{materials.get('source','')}</td></tr>
<tr><th>Confiabilidad</th><td>{reliability.get('reliability_pct',0):.1f}%</td></tr>
</table>

<h2>5. Estimación económica</h2>''',
"agregar materiales al informe HTML",
)

# 11) PDF: incorporar variables críticas adicionales.
replace_once(
'''    rows += [
        ["Clima - modo", str(climate.get("input_mode", ""))],''',
'''    geometry = payload.get("geometry", {})
    materials = payload.get("materials", {})
    reliability = payload.get("reliability", {})
    rows += [
        ["Longitud de diseño", f"{geometry.get('length_m', 0):,.1f} m"],
        ["Ancho de referencia", f"{geometry.get('paved_reference_width_m', 0):,.2f} m"],
        ["Fuente Mr subrasante", str(payload.get("subgrade", {}).get("mr_source", ""))],
        ["E* mezcla asfáltica", f"{materials.get('asphalt_dynamic_modulus_mpa',0):,.0f} MPa"],
        ["Confiabilidad", f"{reliability.get('reliability_pct',0):.1f}%"],
        ["Clima - modo", str(climate.get("input_mode", ""))],''',
"agregar datos críticos al PDF",
)

# 12) Resumen final usa Mr de diseño y evidencia la categoría/propiedades.
replace_once(
'''        f"**{cbr_design:.2f}%**, clasificación **{sclass}**, y un módulo resiliente estimado de "
        f"**{mr:.2f} MPa**."
    )''',
'''        f"**{cbr_design:.2f}%**, clasificación **{sclass}**, y un módulo resiliente de diseño de "
        f"**{mr:.2f} MPa**. "
        f"La geometría de referencia es **{project_length_m:,.0f} m × {project_width_m:.2f} m**."
    )''',
"actualizar resumen final",
)

APP.write_text(text, encoding="utf-8")
print("Fase 1 de datos prioritarios de diseño aplicada correctamente.")
