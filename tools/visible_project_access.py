from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

replacements = [
    (
        '    layout="wide",\n)',
        '    layout="wide",\n    initial_sidebar_state="expanded",\n)'
    ),
    (
        '''    st.download_button(\n        "Descargar catálogo histórico (solo referencia)",\n        data=CATALOG_DEFAULT.to_csv(index=False).encode("utf-8-sig"),\n        file_name="catalogo_historico_no_normativo.csv",\n        mime="text/csv",\n        help="Archivo heredado conservado únicamente para compatibilidad y referencia; no alimenta la selección oficial del Tomo II.",\n    )\n\n# Selector principal de metodología\n''',
        '''    st.download_button(\n        "Descargar catálogo histórico (solo referencia)",\n        data=CATALOG_DEFAULT.to_csv(index=False).encode("utf-8-sig"),\n        file_name="catalogo_historico_no_normativo.csv",\n        mime="text/csv",\n        help="Archivo heredado conservado únicamente para compatibilidad y referencia; no alimenta la selección oficial del Tomo II.",\n    )\n\n# Acceso visible a cuenta y proyectos, aun cuando la barra lateral se haya colapsado manualmente.\nst.markdown("### 👤 Cuenta y proyectos")\nif int(user.get("id", 0)) > 0:\n    account_col, save_col = st.columns([3, 1])\n    with account_col:\n        st.success(\n            f"Sesión iniciada como **{user.get('display_name', user.get('username', 'Usuario'))}**. "\n            f"Proyecto de guardado actual: **{project_name_web or 'Sin nombre'}**. "\n            "La administración completa de proyectos también está disponible en la barra lateral **Mis proyectos**."\n        )\n    with save_col:\n        if st.button("💾 Guardar proyecto ahora", use_container_width=True, key="main_save_project"):\n            if project_name_web.strip():\n                save_project(int(user["id"]), project_name_web.strip(), _capture_session_state())\n                st.success("Proyecto guardado correctamente.")\n                st.rerun()\n            else:\n                st.warning("Indique un nombre para el proyecto en la barra lateral.")\nelse:\n    guest_col, login_col = st.columns([3, 1])\n    with guest_col:\n        st.warning(\n            "Está usando GDP Pavimentos Pro como **invitado**. Puede realizar cálculos, pero los proyectos no se guardan permanentemente. "\n            "Inicie sesión o cree una cuenta para activar **Mis proyectos**."\n        )\n    with login_col:\n        if st.button("🔐 Iniciar sesión / Crear cuenta", use_container_width=True, key="main_login_from_guest"):\n            st.session_state.clear()\n            st.rerun()\n\n# Selector principal de metodología\n'''
    ),
]

changed = 0
for old, new in replacements:
    if new in text:
        continue
    if old not in text:
        raise SystemExit(f'No se encontró un bloque esperado:\n{old[:220]}')
    text = text.replace(old, new, 1)
    changed += 1

path.write_text(text, encoding='utf-8')
print(f'Visibilidad de proyectos actualizada en {changed} bloque(s).')
