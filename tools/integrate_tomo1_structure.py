from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old = '''    else:
        st.subheader("Evaluación de estructura propuesta — Tomo I")
        st.info("El catálogo Tomo II no se utiliza cuando está activo Tomo I. Puede volver a Tomo II para seleccionar una estructura oficial o continuar con el diseño mecanístico-empírico preliminar.")
        selected_row = st.session_state.get("selected_row")
        if selected_row:
            st.caption(f"Estructura actualmente cargada: {selected_row.get('Código','')} — {selected_row.get('Superficie','')}")
        else:
            st.warning("No hay una estructura seleccionada. Active Tomo II para obtener una alternativa de catálogo o cargue una estructura mediante el flujo de diseño correspondiente.")
'''

new = '''    else:
        st.subheader("Estructura propuesta para evaluación — GDP-2024 Tomo I")
        st.info(
            "El Tomo I es una guía mecanístico-empírica para pavimentos flexibles y semirrígidos. "
            "En este modo GDP permite **definir una sección propuesta para evaluarla**, pero no la presenta como una alternativa de catálogo ni como diseño final aprobado. "
            "El cumplimiento debe sustentarse con la caracterización de tránsito, subrasante, clima, materiales y la evaluación de respuesta/desempeño aplicable del Tomo I."
        )
        st.caption(
            "Referencia normativa: GDP-2024 Tomo I — Guía mecanístico-empírica para el diseño de pavimentos flexibles y semirrígidos, "
            "oficializada mediante Decreto Ejecutivo 44762-MOPT."
        )

        previous_t1 = st.session_state.get("tomo1_structure", {})
        imported = st.session_state.get("selected_row") if st.session_state.get("selected_row") and not previous_t1 else None
        source_default = "Importada de Tomo II para evaluación" if imported else "Definida por el usuario"
        source = st.segmented_control(
            "Origen de la sección propuesta",
            ["Definida por el usuario", "Importada de Tomo II para evaluación"],
            default=source_default,
            key="tomo1_structure_source",
        ) or source_default

        import_row = imported if source.startswith("Importada") and imported else {}
        if source.startswith("Importada") and not import_row:
            st.warning("No hay una alternativa Tomo II disponible en la sesión. Se mantienen los valores editables de Tomo I.")

        dflt = previous_t1 or import_row
        t1_type = st.selectbox(
            "Tipo de pavimento a evaluar",
            ["Flexible", "Semirrígido"],
            index=0 if str(dflt.get("Tipo_TomoI", "Flexible")) != "Semirrígido" else 1,
            key="tomo1_pavement_type",
        )
        st.markdown("#### Espesores de la sección propuesta")
        e1, e2, e3, e4 = st.columns(4)
        asphalt_cm = e1.number_input(
            "Mezcla asfáltica (cm)", min_value=0.0, max_value=40.0,
            value=float(dflt.get("Carpeta_cm", 5.0) or 0.0), step=0.5, key="tomo1_asphalt_cm"
        )
        base_granular_cm = e2.number_input(
            "Base granular (cm)", min_value=0.0, max_value=80.0,
            value=float(dflt.get("Base_granular_cm", dflt.get("Base_cm", 20.0)) or 0.0) if float(dflt.get("Base_estabilizada_cm", 0) or 0) <= 0 else float(dflt.get("Base_granular_cm", 0) or 0),
            step=1.0, key="tomo1_base_granular_cm"
        )
        base_stabilized_cm = e3.number_input(
            "Base estabilizada (cm)", min_value=0.0, max_value=80.0,
            value=float(dflt.get("Base_estabilizada_cm", 0.0) or 0.0), step=1.0, key="tomo1_base_stabilized_cm"
        )
        subbase_cm = e4.number_input(
            "Subbase granular (cm)", min_value=0.0, max_value=100.0,
            value=float(dflt.get("Subbase_cm", 20.0) or 0.0), step=1.0, key="tomo1_subbase_cm"
        )
        i1, i2 = st.columns(2)
        improvement_cm = i1.number_input(
            "Mejoramiento de subrasante (cm, si aplica)", min_value=0.0, max_value=150.0,
            value=float(dflt.get("Mejoramiento_subrasante_cm", 0.0) or 0.0), step=1.0, key="tomo1_improvement_cm"
        )
        structure_id = i2.text_input(
            "Identificador de la sección", value=str(dflt.get("Código", "T1-PROP-01") or "T1-PROP-01"), key="tomo1_structure_id"
        )

        base_total_cm = float(base_granular_cm + base_stabilized_cm)
        total_thickness = float(asphalt_cm + base_total_cm + subbase_cm + improvement_cm)
        proposed = {
            "Código": structure_id.strip() or "T1-PROP-01",
            "Superficie": "Carpeta asfáltica" if asphalt_cm > 0 else "Superficie propuesta",
            "Tipo_TomoI": t1_type,
            "Origen_TomoI": source,
            "Carpeta_cm": float(asphalt_cm),
            "Base_cm": base_total_cm,
            "Base_granular_cm": float(base_granular_cm),
            "Base_estabilizada_cm": float(base_stabilized_cm),
            "Subbase_cm": float(subbase_cm),
            "Mejoramiento_subrasante_cm": float(improvement_cm),
            "Base_tipo": "Estabilizada" if base_stabilized_cm > 0 and base_granular_cm <= 0 else ("Mixta" if base_stabilized_cm > 0 and base_granular_cm > 0 else "Granular"),
            "Fuente": "GDP-2024 Tomo I — sección propuesta para evaluación mecanístico-empírica",
        }
        st.session_state.tomo1_structure = proposed
        st.session_state.selected_row = proposed
        st.session_state.total_thickness = total_thickness
        selected_row = proposed

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Carpeta", f"{asphalt_cm:.1f} cm")
        m2.metric("Base total", f"{base_total_cm:.1f} cm")
        m3.metric("Subbase", f"{subbase_cm:.1f} cm")
        m4.metric("Sección modelada", f"{total_thickness:.1f} cm")

        if asphalt_cm <= 0:
            st.warning("Para una evaluación de pavimento flexible/semirrígido en este flujo debe documentarse la capa superficial correspondiente. El valor actual no se interpreta como una solución final.")
        if base_total_cm <= 0 and subbase_cm <= 0:
            st.warning("La sección no contiene base ni subbase. Revise la configuración antes de utilizar los módulos de análisis.")
        if t1_type == "Semirrígido" and base_stabilized_cm <= 0:
            st.warning("Se seleccionó pavimento semirrígido, pero no se definió una base estabilizada. Revise la estructura y la caracterización de materiales conforme al Tomo I.")

        st.markdown("#### Control de información para evaluación Tomo I")
        c1, c2, c3, c4 = st.columns(4)
        c1.success(f"Tránsito: EEq = {esal:,.0f}")
        c2.success(f"Subrasante: CBR = {cbr_design:.2f}%")
        if temp_data_confirmed:
            c3.success("Clima: fuente documentada")
        else:
            c3.warning("Clima: falta documentar fuente")
        if master_curve_confirmed:
            c4.success("Materiales: respuesta térmica documentada")
        else:
            c4.warning("Materiales: caracterización incompleta")
        st.warning(
            "**Estado:** sección propuesta para evaluación. GDP no declara conformidad final del Tomo I con estos espesores por sí solos; "
            "la aceptación requiere completar las verificaciones mecanístico-empíricas y la trazabilidad de entradas aplicables."
        )

        left, right = st.columns([0.9, 2.1], gap="large")
        with left:
            st.markdown("#### Visor técnico")
            exploded_t1 = st.toggle("Vista explotada 3D", value=True, key="tomo1_gdp3d_exploded")
            scale_t1 = st.selectbox("Escala vertical", ["Real (×1)", "Exagerada ×2", "Exagerada ×5"], index=0, key="tomo1_gdp3d_vertical_scale")
            vertical_t1 = {"Real (×1)":1.0, "Exagerada ×2":2.0, "Exagerada ×5":5.0}[scale_t1]
            view_t1 = st.selectbox("Modo de corte", ["Completa", "Media calzada", "Corte transversal", "Corte longitudinal"], key="tomo1_gdp3d_view_mode")
            layers_t1 = [x["name"] for x in _structure_layers_3d(selected_row, sclass, cbr_design)]
            highlight_t1 = st.selectbox("Resaltar capa", ["Todas"] + layers_t1, key="tomo1_gdp3d_selected_layer")
            if vertical_t1 > 1:
                st.warning(f"Exageración vertical ×{vertical_t1:g}; las cotas mantienen los espesores reales ingresados.")
            st.caption("La subrasante se representa como medio semiinfinito. El mejoramiento, cuando se ingresa, se muestra como una capa diferenciada.")
        with right:
            st.markdown("#### Visor estructural 3D v2 — Tomo I")
            fig_t1 = pavement_3d_figure(selected_row, sclass, cbr_design, exploded_t1, vertical_t1, view_t1, highlight_t1)
            render_rotating_3d(fig_t1, key="tomo1_structure_view", height=700, auto_rotate=st.session_state.get("auto_rotate_3d", True))

        st.info(
            "La estructura activa queda enlazada con **6. Diseño flexible** y **7. Desempeño**. "
            "En la pestaña 7 se habilita nuevamente el **Modelo 3D del deterioro del pavimento** para la sección propuesta."
        )
'''

if old not in s:
    raise SystemExit('No se encontró el bloque Tomo I esperado')
s = s.replace(old, new, 1)

# Aclarar que el 3D de deterioro depende de la estructura activa y evitar que quede silencioso.
old_perf_else = '''    else: st.info("Seleccione una estructura para activar el monitoreo de deterioro.")'''
new_perf_else = '''    else:
        st.info("Defina una estructura activa en **5. Estructura** para habilitar las curvas y el **Modelo 3D del deterioro del pavimento**.")'''
if old_perf_else in s:
    s = s.replace(old_perf_else, new_perf_else, 1)

p.write_text(s, encoding='utf-8')
print('Integración Tomo I + 3D deterioro aplicada correctamente')
