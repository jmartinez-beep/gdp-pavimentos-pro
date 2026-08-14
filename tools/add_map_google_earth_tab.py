from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# MAP_GOOGLE_EARTH_TAB'
if MARKER in text:
    print('Pestaña Mapa / Google Earth ya integrada.')
    raise SystemExit(0)


def replace_once(old: str, new: str, label: str) -> None:
    global text
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: se esperaba 1 coincidencia y se encontraron {n}')
    text = text.replace(old, new, 1)

# 1) Helper KML sin dependencias externas.
anchor = '''def money(value: float) -> str:\n    return f"₡{value:,.0f}".replace(",", " ")\n\n\n'''
helper_code = """# MAP_GOOGLE_EARTH_TAB
def _xml_escape(value) -> str:
    return (str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def project_point_kml(project_name: str, latitude: float, longitude: float, description: str = "") -> str:
    name = _xml_escape(project_name or "Proyecto GDP")
    desc = _xml_escape(description)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\\n'
        '  <Document>\\n'
        f'    <name>{name}</name>\\n'
        '    <Placemark>\\n'
        f'      <name>{name}</name>\\n'
        f'      <description>{desc}</description>\\n'
        '      <Point>\\n'
        f'        <coordinates>{float(longitude):.8f},{float(latitude):.8f},0</coordinates>\\n'
        '      </Point>\\n'
        '    </Placemark>\\n'
        '  </Document>\\n'
        '</kml>\\n'
    )


"""
replace_once(anchor, anchor + helper_code, 'insertar helper KML')

# 2) Agregar la pestaña 16.
old_tabs = '''pdash, p1, p2, p3, pclima, p4, pflex, pperf, pcompare, p5, pmaint, pdrain, pvalid, pcr2010, pexport, p6 = st.tabs([\n    "🏠 Dashboard", "1. Proyecto", "2. Tránsito", "3. Subrasante", "4. Clima", "5. Estructura",\n    "6. Diseño flexible", "7. Desempeño", "8. Comparación", "9. Costos", "10. Ciclo de vida", "11. Drenaje", "12. Validación", "13. Control CR-2020", "14. Exportación", "15. Informe"\n])\n'''
new_tabs = '''pdash, p1, p2, p3, pclima, p4, pflex, pperf, pcompare, p5, pmaint, pdrain, pvalid, pcr2010, pexport, p6, pmap = st.tabs([\n    "🏠 Dashboard", "1. Proyecto", "2. Tránsito", "3. Subrasante", "4. Clima", "5. Estructura",\n    "6. Diseño flexible", "7. Desempeño", "8. Comparación", "9. Costos", "10. Ciclo de vida", "11. Drenaje", "12. Validación", "13. Control CR-2020", "14. Exportación", "15. Informe", "16. Mapa / Google Earth"\n])\n'''
replace_once(old_tabs, new_tabs, 'agregar pestaña mapa')

# 3) Insertar contenido del mapa antes del Dashboard.
anchor_dash = '''with pdash:\n    # Dashboard profesional v0.9.1: una sola vista de control, similar al tablero de referencia.\n'''
map_block = '''with pmap:\n    st.subheader("Mapa del proyecto / Google Earth")\n    st.caption("Las coordenadas se toman automáticamente de la pestaña 1. Proyecto. No es necesario volver a digitarlas.")\n\n    map_lat = float(latitude)\n    map_lon = float(longitude)\n    map_e = float(crtm_easting)\n    map_n = float(crtm_northing)\n\n    mp1, mp2, mp3, mp4 = st.columns(4)\n    mp1.metric("Este CRTM05", f"{map_e:,.3f} m")\n    mp2.metric("Norte CRTM05", f"{map_n:,.3f} m")\n    mp3.metric("Latitud WGS84", f"{map_lat:.7f}°")\n    mp4.metric("Longitud WGS84", f"{map_lon:.7f}°")\n\n    if is_plausible_costa_rica_wgs84(map_lon, map_lat):\n        map_df = pd.DataFrame({\n            "lat": [map_lat], "lon": [map_lon],\n            "Proyecto": [project_name], "Ubicación": [location],\n        })\n        st.map(map_df, latitude="lat", longitude="lon", zoom=15)\n    else:\n        st.error("Las coordenadas actuales quedan fuera del entorno geográfico esperado de Costa Rica. Revise la pestaña Proyecto antes de abrir o exportar la ubicación.")\n\n    st.markdown("#### Abrir ubicación")\n    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={map_lat:.8f},{map_lon:.8f}"\n    gm1, gm2 = st.columns(2)\n    gm1.link_button("🌎 Abrir en Google Maps", google_maps_url, use_container_width=True)\n    gm2.markdown(\n        f"**Coordenadas para Google Earth:** `{map_lat:.8f}, {map_lon:.8f}`  \\n"\n        "Puede pegar estas coordenadas directamente en el buscador de Google Earth."\n    )\n\n    st.markdown("#### Exportar a Google Earth (KML)")\n    kml_description = (\n        f"Proyecto: {project_name} | Ubicación: {location} | Tomo activo: {active_tomo} | "\n        f"CRTM05 E={map_e:.3f} m, N={map_n:.3f} m"\n    )\n    kml_text = project_point_kml(project_name, map_lat, map_lon, kml_description)\n    safe_project_name = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(project_name)).strip('_') or 'Proyecto_GDP'\n    st.download_button(\n        "⬇️ Descargar punto KML para Google Earth",\n        data=kml_text.encode("utf-8"),\n        file_name=f"{safe_project_name}_ubicacion.kml",\n        mime="application/vnd.google-earth.kml+xml",\n        use_container_width=True,\n    )\n\n    st.markdown("#### Ficha geográfica")\n    geographic_record = pd.DataFrame([{\n        "Proyecto": project_name, "Ubicación": location, "Tomo": active_tomo,\n        "Sistema entrada": coordinate_system,\n        "Este CRTM05 (m)": map_e, "Norte CRTM05 (m)": map_n,\n        "Latitud WGS84": map_lat, "Longitud WGS84": map_lon,\n    }])\n    st.dataframe(geographic_record, use_container_width=True, hide_index=True)\n    st.session_state.project_map = {\n        "latitude": map_lat, "longitude": map_lon, "crtm_easting": map_e, "crtm_northing": map_n,\n        "google_maps_url": google_maps_url, "kml_filename": f"{safe_project_name}_ubicacion.kml",\n    }\n    st.info("El KML contiene el punto central del proyecto. En una siguiente ampliación se pueden agregar sondeos, inicio/fin, tramos homogéneos, puentes, alcantarillas y otras obras como geometrías independientes.")\n\n\n''' + anchor_dash
replace_once(anchor_dash, map_block, 'insertar contenido mapa')

# 4) Incorporar ficha geográfica al payload.
payload_anchor = '''        "asphalt_thickness_control": st.session_state.get("asphalt_thickness_control", {}),\n'''
payload_new = '''        "asphalt_thickness_control": st.session_state.get("asphalt_thickness_control", {}),\n        "project_map": st.session_state.get("project_map", {\n            "latitude": float(latitude), "longitude": float(longitude),\n            "crtm_easting": float(crtm_easting), "crtm_northing": float(crtm_northing),\n        }),\n'''
replace_once(payload_anchor, payload_new, 'agregar mapa al payload')

APP.write_text(text, encoding='utf-8')
print('Pestaña 16 Mapa / Google Earth integrada.')
