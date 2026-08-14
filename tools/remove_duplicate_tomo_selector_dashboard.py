from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# SINGLE_TOMO_SELECTOR_DASHBOARD'
if MARKER in text:
    print('Selector duplicado del Dashboard ya eliminado.')
    raise SystemExit(0)

old = '''with pdash:\n    # Dashboard profesional v0.9.1: una sola vista de control, similar al tablero de referencia.\n    heavy_pct_dash = (heavy_total / tpd_total * 100.0) if tpd_total else 0.0\n    selected_dash = selected_row or st.session_state.get("selected_row")\n    selected_total = float(st.session_state.get("total_thickness", total_thickness or 0.0))\n\n    # Encabezado superior\n    hleft, hcenter, hright = st.columns([1.0, 2.2, 1.15], gap="small")\n    with hleft:\n        st.markdown("<div class='panel-card'><div class='panel-title'>Normativa activa</div>", unsafe_allow_html=True)\n        dash_tomo = st.segmented_control("", ["Tomo I", "Tomo II"], default=st.session_state.active_tomo, key="dash_tomo_selector", label_visibility="collapsed") or st.session_state.active_tomo\n        st.session_state.active_tomo = dash_tomo\n        st.markdown("</div>", unsafe_allow_html=True)\n'''

new = '''with pdash:\n    # Dashboard profesional v0.9.1: una sola vista de control, similar al tablero de referencia.\n    # SINGLE_TOMO_SELECTOR_DASHBOARD\n    heavy_pct_dash = (heavy_total / tpd_total * 100.0) if tpd_total else 0.0\n    selected_dash = selected_row or st.session_state.get("selected_row")\n    selected_total = float(st.session_state.get("total_thickness", total_thickness or 0.0))\n    dash_tomo = active_tomo\n\n    # Encabezado superior\n    hleft, hcenter, hright = st.columns([1.0, 2.2, 1.15], gap="small")\n    with hleft:\n        tomo_label = "Tomo I" if dash_tomo == "Tomo I" else "Tomo II"\n        tomo_method = "Diseño mecanístico-empírico" if dash_tomo == "Tomo I" else "Catálogo simplificado"\n        tomo_icon = "📗" if dash_tomo == "Tomo I" else "📘"\n        st.markdown(\n            f"<div class='panel-card'><div class='panel-title'>Normativa activa</div>"\n            f"<div style='font-size:1.45rem;font-weight:900;color:#fff'>{tomo_icon} {tomo_label}</div>"\n            f"<div style='color:#9eb3c8;margin-top:5px'>{tomo_method}</div></div>",\n            unsafe_allow_html=True,\n        )\n'''

count = text.count(old)
if count != 1:
    raise RuntimeError(f'No se encontró exactamente una vez el selector duplicado del Dashboard; coincidencias={count}')
text = text.replace(old, new, 1)

if 'key="dash_tomo_selector"' in text:
    raise RuntimeError('El widget dash_tomo_selector todavía existe después de la migración.')

APP.write_text(text, encoding='utf-8')
print('Selector duplicado eliminado; Dashboard sincronizado con el selector principal.')
