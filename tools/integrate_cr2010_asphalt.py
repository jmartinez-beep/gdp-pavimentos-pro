from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if new in text:
        return
    if old not in text:
        raise SystemExit(f'No se encontró el bloque esperado: {label}')
    text = text.replace(old, new, 1)


replace_once(
    'from climate_tools import MONTHS_ES, monthly_climate_table, monthly_summary, representative_temperature\n',
    'from climate_tools import MONTHS_ES, monthly_climate_table, monthly_summary, representative_temperature\nfrom cr2010_asphalt import render_asphalt_cr2010_checklist\n',
    'import checklist CR-2010',
)

replace_once(
    '''pdash, p1, p2, p3, pclima, p4, pflex, pperf, pcompare, p5, pmaint, pdrain, pvalid, pexport, p6 = st.tabs([\n    "🏠 Dashboard", "1. Proyecto", "2. Tránsito", "3. Subrasante", "4. Clima", "5. Estructura",\n    "6. Diseño flexible", "7. Desempeño", "8. Comparación", "9. Costos", "10. Ciclo de vida", "11. Drenaje", "12. Validación", "13. Exportación", "14. Informe"\n])\n''',
    '''pdash, p1, p2, p3, pclima, p4, pflex, pperf, pcompare, p5, pmaint, pdrain, pvalid, pcr2010, pexport, p6 = st.tabs([\n    "🏠 Dashboard", "1. Proyecto", "2. Tránsito", "3. Subrasante", "4. Clima", "5. Estructura",\n    "6. Diseño flexible", "7. Desempeño", "8. Comparación", "9. Costos", "10. Ciclo de vida", "11. Drenaje", "12. Validación", "13. Control CR-2010", "14. Exportación", "15. Informe"\n])\n''',
    'pestañas',
)

replace_once(
    '''    else:\n        st.info("Seleccione una estructura para ejecutar la validación.")\n\nwith pexport:\n''',
    '''    else:\n        st.info("Seleccione una estructura para ejecutar la validación.")\n\nwith pcr2010:\n    asphalt_cr2010_result = render_asphalt_cr2010_checklist(project_name)\n\nwith pexport:\n''',
    'pestaña control CR-2010',
)

replace_once(
    '''        pd.DataFrame([payload.get("climate", {})]).to_excel(writer, sheet_name="Clima", index=False)\n        alternatives_df.to_excel(writer, sheet_name="Alternativas", index=False)\n''',
    '''        pd.DataFrame([payload.get("climate", {})]).to_excel(writer, sheet_name="Clima", index=False)\n        asphalt_control = payload.get("asphalt_cr2010", {})\n        if asphalt_control:\n            pd.DataFrame([{k:v for k,v in asphalt_control.items() if k != "checks"}]).to_excel(writer, sheet_name="Control_CR2010", index=False)\n            pd.DataFrame(asphalt_control.get("checks", [])).to_excel(writer, sheet_name="Checklist_CR2010", index=False)\n        alternatives_df.to_excel(writer, sheet_name="Alternativas", index=False)\n''',
    'exportación Excel CR-2010',
)

replace_once(
    '''    if payload.get('selected'):\n        rows += [["Estructura", str(payload['selected'].get('Código',''))], ["Superficie", str(payload['selected'].get('Superficie',''))]]\n''',
    '''    if payload.get('selected'):\n        rows += [["Estructura", str(payload['selected'].get('Código',''))], ["Superficie", str(payload['selected'].get('Superficie',''))]]\n    asphalt_control = payload.get("asphalt_cr2010", {})\n    if asphalt_control:\n        rows += [\n            ["Control CR-2010 asfaltos", f"{asphalt_control.get('compliant', 0)}/{asphalt_control.get('total_applicable', 0)} controles"],\n            ["Cumplimiento CR-2010", f"{asphalt_control.get('compliance_pct', 0):.0f}%"],\n            ["No conformidades críticas", str(asphalt_control.get('critical_nonconformities', 0))],\n        ]\n''',
    'resumen PDF CR-2010',
)

replace_once(
    '''        "drainage": st.session_state.get("drainage", {}),\n        "lifecycle_npv": st.session_state.get("lifecycle_npv", 0.0),\n''',
    '''        "drainage": st.session_state.get("drainage", {}),\n        "asphalt_cr2010": st.session_state.get("asphalt_cr2010_checklist", {}),\n        "lifecycle_npv": st.session_state.get("lifecycle_npv", 0.0),\n''',
    'payload CR-2010',
)

replace_once(
    '''        c1,c2,c3=st.columns(3)\n        c1.checkbox("Datos de tránsito revisados",key="qa_traffic")\n        c2.checkbox("Ensayos de subrasante respaldados",key="qa_subgrade")\n        c3.checkbox("Drenaje y clima documentados",key="qa_climate")\n        if all(st.session_state.get(k,False) for k in ("qa_traffic","qa_subgrade","qa_climate")) and n_ok>=n_total-1:\n''',
    '''        c1,c2,c3,c4=st.columns(4)\n        c1.checkbox("Datos de tránsito revisados",key="qa_traffic")\n        c2.checkbox("Ensayos de subrasante respaldados",key="qa_subgrade")\n        c3.checkbox("Drenaje y clima documentados",key="qa_climate")\n        asphalt_state = st.session_state.get("asphalt_cr2010_checklist", {})\n        asphalt_ready = bool(asphalt_state) and int(asphalt_state.get("critical_nonconformities", 0)) == 0\n        c4.checkbox("Control asfáltico CR-2010 revisado", value=asphalt_ready, key="qa_asphalt_cr2010")\n        if all(st.session_state.get(k,False) for k in ("qa_traffic","qa_subgrade","qa_climate","qa_asphalt_cr2010")) and n_ok>=n_total-1:\n''',
    'control de emisión CR-2010',
)

path.write_text(text, encoding='utf-8')
print('Checklist CR-2010 integrado en app.py')
