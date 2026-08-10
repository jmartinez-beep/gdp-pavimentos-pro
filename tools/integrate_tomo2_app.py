from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        if new in text:
            print(f"{label}: already applied")
            return
        raise SystemExit(f"Could not find block: {label}")
    text = text.replace(old, new, 1)
    print(f"{label}: applied")


replace_once(
    "from web_storage import (authenticate, create_user, delete_project, list_projects, load_project, save_project)\n",
    "from web_storage import (authenticate, create_user, delete_project, list_projects, load_project, save_project)\nfrom gdp_tomo2_adapter import alternatives_for_app, selected_trace\n",
    "import adapter",
)

text = text.replace("GDP Pavimentos Pro v1.1.2 Web Ready", "GDP Pavimentos Pro v1.1.3 Web Ready")
text = text.replace("GDP Pavimentos Pro 2024 — v1.1.2 Piloto Cloud", "GDP Pavimentos Pro 2024 — v1.1.3 Piloto Cloud")

sidebar_start = '    st.markdown("### Configuración avanzada")\n'
sidebar_end = '\n# Selector principal de metodología\n'
if sidebar_start in text:
    a = text.index(sidebar_start)
    b = text.index(sidebar_end, a)
    replacement = '''    st.markdown("### Configuración normativa")
    st.success("Tomo II usa el catálogo oficial GDP-2024 integrado y trazable. No requiere cargar CSV externos.")
    st.caption("Las alternativas se seleccionan desde las Tablas 301-01 a 301-21 según TPD, porcentaje de pesados, CBR y período de diseño. Los períodos no tabulados no se interpolan.")
    st.download_button(
        "Descargar catálogo histórico (solo referencia)",
        data=CATALOG_DEFAULT.to_csv(index=False).encode("utf-8-sig"),
        file_name="catalogo_historico_no_normativo.csv",
        mime="text/csv",
        help="Archivo heredado conservado únicamente para compatibilidad y referencia; no alimenta la selección oficial del Tomo II.",
    )
'''
    text = text[:a] + replacement + text[b:]
elif "Tomo II usa el catálogo oficial GDP-2024 integrado" not in text:
    raise SystemExit("Could not find sidebar catalog block")

p4_start = "with p4:\n"
p4_end = "\n\nwith pflex:\n"
if p4_start in text:
    a = text.index(p4_start)
    b = text.index(p4_end, a)
    new_p4 = '''with p4:
    if st.session_state.active_tomo == "Tomo II":
        st.subheader("Catálogo oficial de estructuras — GDP-2024 Tomo II")
        st.caption("Selección directa desde las Tablas 301-01 a 301-21, sin interpolación y con trazabilidad por resultado.")

        options, tomo2_result = alternatives_for_app(
            tpd=float(tpd_total),
            heavy_pct=float(heavy_pct),
            cbr=float(cbr_design),
            period=int(years),
        )
        st.session_state.tomo2_options = options.copy()
        st.session_state.tomo2_result = tomo2_result
        exact_match = tomo2_result.get("status") == "ok" and not options.empty
        st.session_state.exact_match = exact_match

        st.markdown("### Resumen de entrada normativa")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("TPD", f"{tpd_total:,.0f} veh/día")
        r2.metric("Pesados", f"{heavy_pct:.2f}%")
        r3.metric("CBR", f"{cbr_design:.2f}%")
        r4.metric("Periodo", f"{int(years)} años")

        criteria = tomo2_result.get("criteria", [])
        if criteria:
            cdf = pd.DataFrame(criteria)
            st.dataframe(cdf, use_container_width=True, hide_index=True)

        status = tomo2_result.get("status")
        if status == "fuera_alcance":
            st.error("La combinación ingresada está fuera del alcance directo del catálogo Tomo II. No se emite ninguna alternativa normativa.")
        elif status == "sin_alternativa":
            st.warning("La combinación está dentro del alcance general, pero la celda correspondiente no asigna una alternativa estructural. Revise la tabla y el criterio indicado.")
        elif status == "ok":
            st.success(f"Se encontraron {len(options)} alternativa(s) oficiales para la combinación ingresada.")

        if tomo2_result.get("table"):
            st.info(f"Referencia de asignación: {tomo2_result.get('table')} · página {tomo2_result.get('page')} · {tomo2_result.get('source','GDP-2024 Tomo II')}")

        st.markdown("#### Estado climático del diseño")
        for level,msg in climate_checks:
            if level == "error": st.error(msg)
            elif level == "warning": st.warning(msg)
            else: st.success(msg)

        if not options.empty:
            label_map = {}
            for _, row in options.iterrows():
                esp = float(row["Carpeta_cm"]) + float(row["Base_cm"]) + float(row["Subbase_cm"])
                base_label = row.get("Base_tipo", "Base")
                label = f"{row['Código']} — {row['Superficie']} — {base_label} — {esp:.0f} cm"
                label_map[label] = str(row["Código"])

            selected_label = st.selectbox("Seleccione una alternativa oficial", list(label_map.keys()), key="official_tomo2_structure")
            selected_code = label_map[selected_label]
            selected_row = options[options["Código"].astype(str) == selected_code].iloc[0].to_dict()
            st.session_state.selected_row = selected_row
            total_thickness = float(selected_row["Carpeta_cm"]) + float(selected_row["Base_cm"]) + float(selected_row["Subbase_cm"])
            st.session_state.total_thickness = total_thickness

            st.markdown("### Paquete estructural seleccionado")
            k1, k2, k3 = st.columns(3)
            k1.metric("Código", selected_row["Código"])
            k2.metric("Tipo de superficie", selected_row["Superficie"])
            k3.metric("Espesor de capas", f"{total_thickness:.0f} cm")

            left, right = st.columns([0.9, 2.1], gap="large")
            with left:
                st.markdown("#### Capas")
                if float(selected_row["Carpeta_cm"]) > 0:
                    st.markdown(f'<div class="layer">Carpeta asfáltica<br><b>{float(selected_row["Carpeta_cm"]):.0f} cm</b></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="layer">{selected_row["Superficie"]}<br><b>Capa superficial</b></div>', unsafe_allow_html=True)
                if float(selected_row.get("Base_granular_cm", 0)) > 0:
                    st.markdown(f'<div class="layer">Base granular<br><b>{float(selected_row["Base_granular_cm"]):.0f} cm</b></div>', unsafe_allow_html=True)
                if float(selected_row.get("Base_estabilizada_cm", 0)) > 0:
                    st.markdown(f'<div class="layer">Base estabilizada<br><b>{float(selected_row["Base_estabilizada_cm"]):.0f} cm</b></div>', unsafe_allow_html=True)
                if float(selected_row["Subbase_cm"]) > 0:
                    st.markdown(f'<div class="layer">Subbase granular<br><b>{float(selected_row["Subbase_cm"]):.0f} cm</b></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="layer">Subrasante<br><b>CBR {cbr_design:.2f}%</b></div>', unsafe_allow_html=True)
                exploded_view = st.toggle("Vista explotada 3D", value=True, help="Separa las capas para identificarlas con mayor facilidad.")
                st.caption("Use el mouse para girar, acercar y desplazar el modelo.")

            with right:
                st.markdown("#### Modelo 3D interactivo")
                fig_3d = pavement_3d_figure(selected_row, sclass, cbr_design, exploded_view)
                render_rotating_3d(fig_3d, key="structure_view", height=700, auto_rotate=st.session_state.get("auto_rotate_3d", True))

            trace = selected_trace(selected_row)
            with st.expander("Trazabilidad GDP-2024 de la alternativa", expanded=True):
                trace_df = pd.DataFrame([
                    ["Fuente", trace.get("fuente", "")],
                    ["Decreto", trace.get("decreto", "")],
                    ["Definición de estructura", trace.get("definicion_estructura", "")],
                    ["Tabla de asignación", trace.get("asignacion", "")],
                    ["Criterio aplicado", trace.get("criterio", "")],
                    ["Celda original", trace.get("celda_original", "")],
                    ["Nota de extracción", trace.get("nota_extraccion", "")],
                ], columns=["Elemento", "Referencia"])
                st.dataframe(trace_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Descargar trazabilidad de la alternativa (CSV)",
                    trace_df.to_csv(index=False).encode("utf-8-sig"),
                    f"trazabilidad_{selected_row['Código']}.csv",
                    "text/csv",
                )
        else:
            selected_row = None
            st.session_state.selected_row = None
            st.session_state.total_thickness = 0.0
    else:
        st.subheader("Evaluación de estructura propuesta — Tomo I")
        st.info("El catálogo Tomo II no se utiliza cuando está activo Tomo I. Puede volver a Tomo II para seleccionar una estructura oficial o continuar con el diseño mecanístico-empírico preliminar.")
        selected_row = st.session_state.get("selected_row")
        if selected_row:
            st.caption(f"Estructura actualmente cargada: {selected_row.get('Código','')} — {selected_row.get('Superficie','')}")
        else:
            st.warning("No hay una estructura seleccionada. Active Tomo II para obtener una alternativa de catálogo o cargue una estructura mediante el flujo de diseño correspondiente.")
'''
    text = text[:a] + new_p4 + text[b:]
elif "Catálogo oficial de estructuras — GDP-2024 Tomo II" not in text:
    raise SystemExit("Could not find p4 block")

compare_start = "with pcompare:\n"
compare_end = "\nwith p5:\n"
if compare_start in text:
    a = text.index(compare_start)
    b = text.index(compare_end, a)
    new_compare = '''with pcompare:
    st.subheader("Comparación técnica y económica de alternativas")
    if active_tomo == "Tomo II":
        candidates = st.session_state.get("tomo2_options", pd.DataFrame()).copy()
        st.caption("Comparación limitada a las alternativas oficiales asignadas por la celda normativa vigente para el proyecto.")
    else:
        candidates = st.session_state.catalog.copy()
        st.caption("Comparación preliminar de referencia para Tomo I.")

    if candidates.empty:
        st.info("No hay alternativas compatibles disponibles para comparar.")
        st.session_state.alternatives_compare = pd.DataFrame()
    else:
        cp1,cp2,cp3=st.columns(3)
        surf_price=cp1.number_input("Precio referencial superficie (₡/m³)",0.0,value=95000.0,step=5000.0,key='cmp_surf')
        base_price=cp2.number_input("Precio referencial base (₡/m³)",0.0,value=28000.0,step=1000.0,key='cmp_base')
        sub_price=cp3.number_input("Precio referencial subbase (₡/m³)",0.0,value=22000.0,step=1000.0,key='cmp_sub')
        cmp_area=st.number_input("Área para comparación (m²)",1.0,value=900.0,step=50.0,key='cmp_area')
        candidates['Espesor_total_cm']=candidates[['Carpeta_cm','Base_cm','Subbase_cm']].sum(axis=1)
        candidates['Costo_inicial']=cmp_area*(candidates['Carpeta_cm']/100*surf_price+candidates['Base_cm']/100*base_price+candidates['Subbase_cm']/100*sub_price)
        candidates['Coincidencia']='Oficial GDP-2024' if active_tomo == "Tomo II" else 'Referencia'
        cmin=max(float(candidates['Costo_inicial'].min()),1.0); cmax=max(float(candidates['Costo_inicial'].max()),cmin)
        emin=max(float(candidates['Espesor_total_cm'].min()),1.0); emax=max(float(candidates['Espesor_total_cm'].max()),emin)
        candidates['Índice técnico-económico']=100-(60*(candidates['Costo_inicial']-cmin)/(cmax-cmin+1e-9)+40*(candidates['Espesor_total_cm']-emin)/(emax-emin+1e-9))
        base_cols=['Código','Superficie','Espesor_total_cm','Costo_inicial','Coincidencia','Índice técnico-económico']
        trace_cols=[c for c in ['Tabla_asignacion','Criterio_GDP'] if c in candidates.columns]
        show=candidates[base_cols+trace_cols].sort_values('Índice técnico-económico',ascending=False)
        st.dataframe(show.style.format({'Costo_inicial':'₡{:,.0f}','Espesor_total_cm':'{:.0f}'}),use_container_width=True,hide_index=True)
        st.bar_chart(show.set_index('Código')['Costo_inicial'])
        st.session_state.alternatives_compare=show
'''
    text = text[:a] + new_compare + text[b:]
elif "Comparación limitada a las alternativas oficiales" not in text:
    raise SystemExit("Could not find comparison block")

old_payload = '''        "active_tomo": active_tomo,
        "selected": selected_row,
        "flex_design": st.session_state.get("flex_design", {}),
'''
new_payload = '''        "active_tomo": active_tomo,
        "selected": selected_row,
        "gdp_tomo2": st.session_state.get("tomo2_result", {}) if active_tomo == "Tomo II" else {},
        "traceability": selected_trace(selected_row),
        "flex_design": st.session_state.get("flex_design", {}),
'''
replace_once(old_payload, new_payload, "report payload traceability")

old_validation = '''        st.dataframe(validation_df,use_container_width=True,hide_index=True)
        st.download_button("Descargar matriz de validación (CSV)",validation_df.to_csv(index=False).encode("utf-8-sig"),"matriz_validacion_gdp.csv","text/csv")
'''
new_validation = '''        st.dataframe(validation_df,use_container_width=True,hide_index=True)
        if active_tomo == "Tomo II":
            trace = selected_trace(selected_row)
            st.markdown("#### Referencia normativa de la selección")
            st.info(f"{trace.get('fuente','GDP-2024 Tomo II')} · {trace.get('asignacion','')} · {trace.get('criterio','')}")
        st.download_button("Descargar matriz de validación (CSV)",validation_df.to_csv(index=False).encode("utf-8-sig"),"matriz_validacion_gdp.csv","text/csv")
'''
replace_once(old_validation, new_validation, "validation traceability")

old_warning = '    st.warning("La aplicación no sustituye la memoria de cálculo firmada ni la verificación con las tablas completas y vigentes del GDP.")\n'
new_warning = '    st.warning("La aplicación no sustituye la memoria de cálculo firmada. En Tomo II la selección se obtiene de las tablas GDP-2024 integradas; aun así deben verificarse estudios, materiales, drenaje, condiciones particulares y criterio profesional responsable.")\n'
replace_once(old_warning, new_warning, "report warning")

APP.write_text(text, encoding="utf-8")
print("Integration patch completed")
