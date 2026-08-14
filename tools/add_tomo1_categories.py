from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: se esperaba 1 coincidencia y se encontraron {count}")
    text = text.replace(old, new, 1)


# 1) Clasificación jerárquica automática según GDP-2024 Tomo I, Tabla 102-01.
anchor = '''def traffic_class(esal: float) -> str:\n    for label, low, high in TRAFFIC_RANGES:\n        if low <= esal < high:\n            return label\n    if esal >= 1_000_000:\n        return ">T5"\n    return "U1"\n\n\n'''
insert = anchor + '''def tomo1_design_category(esal: float) -> int:\n    """GDP-2024 Tomo I, Tabla 102-01: categoría jerárquica por ESAL de diseño."""\n    esal = float(esal or 0.0)\n    if esal < 3_000_000:\n        return 3\n    if esal <= 25_000_000:\n        return 2\n    return 1\n\n\ndef tomo1_design_category_label(esal: float) -> str:\n    return f"Categoría {tomo1_design_category(esal)}"\n\n\n'''
replace_once(anchor, insert, "insertar función de categoría Tomo I")

# 2) Calcular la categoría junto al ESAL y mostrarla automáticamente en Tránsito.
replace_once(
    '''    tclass = traffic_class(esal)\n\n    m1, m2, m3, m4, m5 = st.columns(5)''',
    '''    tclass = traffic_class(esal)\n    tomo1_category = tomo1_design_category(esal)\n\n    m1, m2, m3, m4, m5 = st.columns(5)''',
    "calcular categoría Tomo I",
)
replace_once(
    '''    m5.metric("EEq de diseño", f"{esal:,.0f}", tclass)\n\n    st.latex''',
    '''    m5.metric("EEq de diseño", f"{esal:,.0f}", tclass if st.session_state.active_tomo == "Tomo II" else f"Categoría {tomo1_category}")\n\n    if st.session_state.active_tomo == "Tomo I":\n        if tomo1_category == 3:\n            category_rule = "ESAL < 3 millones"\n        elif tomo1_category == 2:\n            category_rule = "3 millones ≤ ESAL ≤ 25 millones"\n        else:\n            category_rule = "ESAL > 25 millones"\n        st.success(\n            f"**Clasificación automática Tomo I: Categoría {tomo1_category}** · {category_rule}. "\n            "Referencia: GDP-2024 Tomo I, Tabla 102-01."\n        )\n\n    st.latex''',
    "mostrar categoría en Tránsito",
)

# 3) Eliminar selección manual de categoría en Clima; se deriva del ESAL.
replace_once(
    '''        analysis_category = st.selectbox("Categoría de análisis del Tomo I", [1,2,3], index=2)''',
    '''        analysis_category = tomo1_design_category(esal)\n        if st.session_state.active_tomo == "Tomo I":\n            st.metric(\n                "Categoría de análisis del Tomo I",\n                f"Categoría {analysis_category}",\n                help="Asignación automática según ESAL de diseño y Tabla 102-01 de la GDP-2024 Tomo I.",\n            )\n        else:\n            st.caption("La categoría jerárquica 1–3 corresponde al Tomo I y se calcula automáticamente a partir del ESAL.")''',
    "automatizar categoría en Clima",
)

# 4) Mostrar categoría en el control de información del Tomo I.
replace_once(
    '''        c1.success(f"Tránsito: EEq = {esal:,.0f}")''',
    '''        c1.success(f"Tránsito: EEq = {esal:,.0f} · Categoría {tomo1_category}")''',
    "mostrar categoría en Estructura Tomo I",
)

# 5) Dashboard: Tomo I usa Categoría 1/2/3; Tomo II conserva su clase de tránsito.
replace_once(
    '''        (k1,"Clasificación de tránsito",tclass,f"ESAL: {esal:,.2e}<br>TPD: {tpd_total:,.0f} veh/día","#218cff"),''',
    '''        (k1,\n         "Categoría de diseño" if dash_tomo == "Tomo I" else "Clasificación de tránsito",\n         f"Categoría {tomo1_category}" if dash_tomo == "Tomo I" else tclass,\n         (f"ESAL: {esal:,.2e}<br>Tabla 102-01" if dash_tomo == "Tomo I" else f"ESAL: {esal:,.2e}<br>TPD: {tpd_total:,.0f} veh/día"),\n         "#218cff"),''',
    "actualizar KPI del Dashboard",
)

# 6) Payload/exportaciones: guardar explícitamente la categoría Tomo I.
replace_once(
    '''            "class": tclass,\n        },''',
    '''            "class": tclass,\n            "design_category": tomo1_category,\n            "design_category_label": f"Categoría {tomo1_category}",\n        },''',
    "guardar categoría en payload",
)
replace_once(
    '''    props={"tomo":active_tomo,"traffic":tclass,"subgrade":sclass,"cbr":cbr_design,"esal":esal,"structure":selected_row.get('Código','') if selected_row else ''}''',
    '''    props={"tomo":active_tomo,"traffic":tclass,"design_category":f"Categoría {tomo1_category}" if active_tomo == "Tomo I" else "No aplica","subgrade":sclass,"cbr":cbr_design,"esal":esal,"structure":selected_row.get('Código','') if selected_row else ''}''',
    "agregar categoría a GeoJSON",
)

# 7) Informe HTML: reportar categoría del Tomo I y evitar tratarla como una 'Opción'.
replace_once(
    '''    costs = payload.get("costs", {})\n\n    structure_html = "<p>No se seleccionó una estructura.</p>"''',
    '''    costs = payload.get("costs", {})\n    active_tomo = payload.get("active_tomo", "Tomo II")\n    design_category = int(traffic.get("design_category", tomo1_design_category(float(traffic.get("esal", 0.0)))))\n    traffic_class_html = (\n        f"<tr><th>Categoría de diseño Tomo I</th><td>Categoría {design_category}</td></tr>"\n        if active_tomo == "Tomo I"\n        else f"<tr><th>Rango</th><td>{traffic['class']}</td></tr>"\n    )\n    structure_context_html = (\n        f"<tr><th>Categoría de diseño</th><td>Categoría {design_category}</td></tr>"\n        if active_tomo == "Tomo I"\n        else f"<tr><th>Opción</th><td>{selected.get('Opción', 'Estructura seleccionada') if selected else 'Estructura seleccionada'}</td></tr>"\n    )\n\n    structure_html = "<p>No se seleccionó una estructura.</p>"''',
    "preparar categoría para informe HTML",
)
replace_once(
    '''          <tr><th>Opción</th><td>{selected.get('Opción', 'Estructura seleccionada')}</td></tr>''',
    '''          {structure_context_html}''',
    "reemplazar Opción por contexto normativo",
)
replace_once(
    '''<tr><th>Ejes equivalentes</th><td>{traffic['esal']:,.0f}</td></tr>\n<tr><th>Rango</th><td>{traffic['class']}</td></tr>''',
    '''<tr><th>Ejes equivalentes</th><td>{traffic['esal']:,.0f}</td></tr>\n{traffic_class_html}''',
    "mostrar categoría en tabla de tránsito HTML",
)

# 8) PDF: incluir la categoría jerárquica cuando el Tomo I está activo.
replace_once(
    '''["Subrasante", payload['subgrade']['class']]]\n    climate = payload.get("climate", {})''',
    '''["Subrasante", payload['subgrade']['class']]]\n    if payload.get("active_tomo") == "Tomo I":\n        pdf_category = payload["traffic"].get("design_category", tomo1_design_category(float(payload["traffic"].get("esal", 0.0))))\n        rows.insert(8, ["Categoría de diseño Tomo I", f"Categoría {pdf_category}"])\n    climate = payload.get("climate", {})''',
    "agregar categoría al PDF",
)

# 9) Resumen del Informe: usar la jerarquía Tomo I cuando corresponda.
replace_once(
    '''    st.markdown("#### Resumen")\n    st.write(\n        f"Para el proyecto **{project_name}**, se estimaron **{esal:,.0f} ejes equivalentes**, "\n        f"correspondientes al rango **{tclass}**. La subrasante presenta un CBR de diseño de "''',
    '''    st.markdown("#### Resumen")\n    classification_summary = f"Categoría {tomo1_category} (Tabla 102-01)" if active_tomo == "Tomo I" else f"rango {tclass}"\n    st.write(\n        f"Para el proyecto **{project_name}**, se estimaron **{esal:,.0f} ejes equivalentes**, "\n        f"correspondientes a **{classification_summary}**. La subrasante presenta un CBR de diseño de "''',
    "actualizar resumen del Informe",
)

APP.write_text(text, encoding="utf-8")
print("Clasificación automática de categorías Tomo I aplicada correctamente.")