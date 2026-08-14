from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# NORMATIVE_EVIDENCE_MATRIX'
if MARKER in text:
    print('Matriz normativa ya aplicada.')
    raise SystemExit(0)


def replace_once(old, new, label):
    global text
    c = text.count(old)
    if c != 1:
        raise RuntimeError(f'{label}: se esperaba 1 coincidencia y se encontraron {c}')
    text = text.replace(old, new, 1)

# 1) Registro normativo explícito.
anchor = "CR2020_GRANULAR_QUALITY_REFERENCE = (\n    'CR-2020: Sección 301 Subbases y bases granulares + Subsección 703.05 Agregado para capas de subbase y base'\n)\n\n"
insert = anchor + """# NORMATIVE_EVIDENCE_MATRIX
NORMATIVE_SOURCES = {
    'GDP2024_TOMO_I': {
        'document': 'GDP-2024 Tomo I — Guía mecanística empírica para el diseño de pavimentos flexibles y semirrígidos',
        'authority': 'MOPT',
        'decree': '44762-MOPT',
        'status': 'Oficial y vigente',
        'url': 'https://repositorio.mopt.go.cr/items/0b5becde-1d3b-47b2-b66a-118727ac6058',
    },
    'CR2020': {
        'document': 'CR-2020 — Manual de Especificaciones Generales para la Construcción de Carreteras, Caminos y Puentes',
        'authority': 'MOPT',
        'decree': '43397-MOPT',
        'status': 'Oficial y vigente',
        'url': 'https://repositorio.mopt.go.cr/items/e2dc2d1b-643a-4b14-814c-ecd3e1f12491',
    },
}


def normative_evidence_table() -> pd.DataFrame:
    return pd.DataFrame([
        {
            'Control': 'Categoría jerárquica Tomo I por ESAL',
            'Documento': 'GDP-2024 Tomo I', 'Referencia': 'Tabla 102-01',
            'Estado': 'Verificado en la aplicación', 'Automático': 'Sí',
        },
        {
            'Control': 'CBR mínimo base granular',
            'Documento': 'CR-2020', 'Referencia': 'Sección 301 / Subsección 703.05',
            'Estado': 'Control fijo incorporado', 'Automático': 'Sí',
        },
        {
            'Control': 'CBR mínimo subbase granular',
            'Documento': 'CR-2020', 'Referencia': 'Sección 301 / Subsección 703.05',
            'Estado': 'Control fijo incorporado', 'Automático': 'Sí',
        },
        {
            'Control': 'Clasificación climática A/B',
            'Documento': 'GDP-2024 Tomo I', 'Referencia': 'Tabla/sección exacta pendiente de evidencia textual',
            'Estado': 'No declarar conformidad normativa', 'Automático': 'No',
        },
        {
            'Control': 'Rango de espesor de carpeta asfáltica',
            'Documento': 'GDP-2024 / CR-2020', 'Referencia': 'Diseño, fórmula de trabajo y criterio específico del proyecto',
            'Estado': 'No existe un rango universal bloqueado en la app', 'Automático': 'Solo con criterio documentado',
        },
    ])

"""
replace_once(anchor, insert, 'insertar registro normativo')

# 2) Reemplazar clima A/B arbitrario por modo documentado.
old = '''        st.markdown("#### Clasificación climática A / B — criterio de proyecto, pendiente de tabla normativa exacta")
        st.warning("No se ha fijado un umbral A/B como requisito GDP universal. La clasificación permanece como **criterio de proyecto** hasta vincular la tabla/sección oficial exacta; no se usa para declarar conformidad normativa.")
        cl1, cl2, cl3 = st.columns(3)
        climate_ab_threshold = cl1.number_input("Umbral térmico A/B (°C)", min_value=-10.0, max_value=80.0, value=32.0, step=0.5, key='climate_ab_threshold')
        climate_ab_orientation = cl2.selectbox("Regla A/B", ['A ≤ umbral; B > umbral', 'B ≤ umbral; A > umbral'], key='climate_ab_orientation')
        climate_ab_source = cl3.text_input("Fuente / tabla del criterio A/B", value="Pendiente de documentar", key='climate_ab_source')
        climate_ab = climate_ab_from_threshold(tp_ltpp, climate_ab_threshold, climate_ab_orientation)
        st.metric("Clasificación climática", f"Clima {climate_ab}", f"Tpav LTPP = {tp_ltpp:.1f} °C")
'''
new = '''        st.markdown("#### Clasificación climática A / B — control documental")
        st.warning("El repositorio oficial confirma el GDP-2024 Tomo I, pero la tabla/regla A-B exacta no está incorporada como evidencia textual en esta versión. Por seguridad, GDP Pavimentos Pro **no calcula A/B desde un umbral inventado** ni usa A/B para declarar conformidad.")
        cl1, cl2, cl3 = st.columns(3)
        climate_ab = cl1.selectbox("Clase climática documentada", ["Sin definir", "A", "B"], key='climate_ab_documented')
        climate_ab_source = cl2.text_input("Tabla / sección / informe que respalda A/B", value="", key='climate_ab_source')
        climate_ab_verified = cl3.checkbox("He verificado la clasificación contra el documento aplicable", value=False, key='climate_ab_verified')
        climate_ab_ready = climate_ab in ("A", "B") and bool(climate_ab_source.strip()) and bool(climate_ab_verified)
        if climate_ab_ready:
            st.success(f"Clima {climate_ab} registrado como dato documentado · fuente: {climate_ab_source}")
        else:
            st.info("Clasificación A/B no habilitada como criterio de decisión. Complete clase, referencia y verificación documental.")
'''
replace_once(old, new, 'bloquear clasificación A/B no verificada')

# 3) Ajustar payload climático para el nuevo modelo documental.
old_payload = "'climate_class_ab': climate_ab, 'climate_ab_threshold_c': float(climate_ab_threshold),\n            'climate_ab_rule': climate_ab_orientation, 'climate_ab_source': climate_ab_source,"
new_payload = "'climate_class_ab': climate_ab if climate_ab_ready else 'Sin definir', 'climate_ab_source': climate_ab_source,\n            'climate_ab_verified': bool(climate_ab_verified), 'climate_ab_normative_ready': bool(climate_ab_ready),"
replace_once(old_payload, new_payload, 'actualizar payload A/B')

# 4) Hacer que el control de carpeta solo emita CUMPLE si la fuente está documentada.
old_th = '''        asphalt_thickness_ok = float(asphalt_min_cm) <= float(asphalt_cm) <= float(asphalt_max_cm) if asphalt_max_cm >= asphalt_min_cm else False
        if asphalt_thickness_ok:
            st.success(f"Carpeta {asphalt_cm:.1f} cm: dentro del rango configurado {asphalt_min_cm:.1f}–{asphalt_max_cm:.1f} cm.")
        else:
            st.error(f"Carpeta {asphalt_cm:.1f} cm: fuera del rango configurado {asphalt_min_cm:.1f}–{asphalt_max_cm:.1f} cm. Revise criterio y estructura.")
        st.session_state.asphalt_thickness_control = {'asphalt_cm':float(asphalt_cm),'min_cm':float(asphalt_min_cm),'max_cm':float(asphalt_max_cm),'complies':bool(asphalt_thickness_ok),'source':thickness_source}
'''
new_th = '''        asphalt_range_numerically_ok = float(asphalt_min_cm) <= float(asphalt_cm) <= float(asphalt_max_cm) if asphalt_max_cm >= asphalt_min_cm else False
        asphalt_source_ready = bool(str(thickness_source).strip()) and str(thickness_source).strip().lower() not in ('pendiente de documentar', 'pendiente')
        asphalt_thickness_ok = bool(asphalt_range_numerically_ok and asphalt_source_ready)
        if not asphalt_source_ready:
            st.warning("Rango calculado solo como criterio de proyecto: falta documentar la fuente. No se declara cumplimiento normativo.")
        elif asphalt_thickness_ok:
            st.success(f"Carpeta {asphalt_cm:.1f} cm: cumple el rango documentado del proyecto {asphalt_min_cm:.1f}–{asphalt_max_cm:.1f} cm · {thickness_source}.")
        else:
            st.error(f"Carpeta {asphalt_cm:.1f} cm: fuera del rango documentado {asphalt_min_cm:.1f}–{asphalt_max_cm:.1f} cm. Revise criterio y estructura.")
        st.session_state.asphalt_thickness_control = {'asphalt_cm':float(asphalt_cm),'min_cm':float(asphalt_min_cm),'max_cm':float(asphalt_max_cm),'numerically_within_range':bool(asphalt_range_numerically_ok),'source_ready':bool(asphalt_source_ready),'complies':bool(asphalt_thickness_ok),'source':thickness_source,'status':'Cumple criterio documentado' if asphalt_thickness_ok else ('Pendiente fuente' if not asphalt_source_ready else 'No cumple')}
'''
replace_once(old_th, new_th, 'endurecer control de espesor')

# 5) Añadir matriz normativa en Validación antes de controles de emisión.
anchor_val = '''        st.download_button("Descargar matriz de validación (CSV)",validation_df.to_csv(index=False).encode("utf-8-sig"),"matriz_validacion_gdp.csv","text/csv")
        st.markdown("#### Controles de emisión")
'''
new_val = '''        st.download_button("Descargar matriz de validación (CSV)",validation_df.to_csv(index=False).encode("utf-8-sig"),"matriz_validacion_gdp.csv","text/csv")
        st.markdown("#### Matriz de evidencia normativa")
        st.dataframe(normative_evidence_table(), use_container_width=True, hide_index=True)
        st.caption("Fuentes oficiales de referencia: GDP-2024 Tomo I — Decreto 44762-MOPT; CR-2020 — Decreto 43397-MOPT. Los controles sin tabla/sección exacta incorporada no pueden declarar cumplimiento automático.")
        st.markdown("#### Controles de emisión")
'''
replace_once(anchor_val, new_val, 'agregar matriz normativa a validación')

# 6) Añadir estado normativo al payload/exportación.
anchor_payload = '''        "reliability": st.session_state.get("design_reliability", {}) if active_tomo == "Tomo I" else {},
        "mechanistic_screening": st.session_state.get("mechanistic_screening", {}) if active_tomo == "Tomo I" else {},
'''
new_payload2 = '''        "reliability": st.session_state.get("design_reliability", {}) if active_tomo == "Tomo I" else {},
        "normative_evidence": normative_evidence_table().to_dict(orient="records"),
        "asphalt_thickness_control": st.session_state.get("asphalt_thickness_control", {}),
        "mechanistic_screening": st.session_state.get("mechanistic_screening", {}) if active_tomo == "Tomo I" else {},
'''
replace_once(anchor_payload, new_payload2, 'agregar evidencia normativa al payload')

# 7) Excel con hoja de evidencia normativa.
anchor_excel = '''        pd.DataFrame([payload.get("reliability", {})]).to_excel(writer, sheet_name="Confiabilidad", index=False)
'''
new_excel = '''        pd.DataFrame([payload.get("reliability", {})]).to_excel(writer, sheet_name="Confiabilidad", index=False)
        pd.DataFrame(payload.get("normative_evidence", [])).to_excel(writer, sheet_name="Evidencia_normativa", index=False)
'''
replace_once(anchor_excel, new_excel, 'agregar evidencia normativa a Excel')

APP.write_text(text, encoding='utf-8')
print('Matriz normativa y bloqueo de criterios no verificados aplicados correctamente.')
