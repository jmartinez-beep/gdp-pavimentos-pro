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
    'from gdp_tomo2_adapter import alternatives_for_app, selected_trace\n',
    'from gdp_tomo2_adapter import alternatives_for_app, selected_trace\nfrom geo_cr import crtm05_to_wgs84, wgs84_to_crtm05, is_plausible_costa_rica_wgs84\n',
    'import geo_cr',
)

old_project = '''with p1:\n    c1, c2 = st.columns(2)\n    with c1:\n        project_name = st.text_input("Nombre del proyecto", "Proyecto vial")\n        location = st.text_input("Ubicación", "Costa Rica")\n        engineer = st.text_input("Profesional responsable", "")\n    with c2:\n        project_date = st.date_input("Fecha", date.today())\n        road_type = st.selectbox("Tipo de vía", ["Camino de bajo volumen", "Urbanización", "Vía local", "Otro"])\n        pavement_type = st.selectbox("Tipo de pavimento", ["Flexible", "Semirrígido", "Por definir"])\n        latitude = st.number_input("Latitud del proyecto (grados decimales)", min_value=-90.0, max_value=90.0, value=9.93, step=0.01, format="%.4f")\n    st.caption("Los datos se incorporan automáticamente en el informe descargable.")\n'''

new_project = '''with p1:\n    c1, c2 = st.columns(2)\n    with c1:\n        project_name = st.text_input("Nombre del proyecto", "Proyecto vial")\n        location = st.text_input("Ubicación", "Costa Rica")\n        engineer = st.text_input("Profesional responsable", "")\n    with c2:\n        project_date = st.date_input("Fecha", date.today())\n        road_type = st.selectbox("Tipo de vía", ["Camino de bajo volumen", "Urbanización", "Vía local", "Otro"])\n        pavement_type = st.selectbox("Tipo de pavimento", ["Flexible", "Semirrígido", "Por definir"])\n\n    st.markdown("### Ubicación geográfica y conversión de coordenadas")\n    st.caption("CRTM05 se procesa como EPSG:5367 y WGS84 como EPSG:4326 mediante PROJ/pyproj. La conversión se actualiza automáticamente al cambiar los valores.")\n    coordinate_system = st.segmented_control(\n        "Sistema de coordenadas de entrada",\n        ["CRTM05 (EPSG:5367)", "WGS84 (EPSG:4326)"],\n        default="CRTM05 (EPSG:5367)",\n        key="project_coordinate_system",\n    ) or "CRTM05 (EPSG:5367)"\n\n    if coordinate_system.startswith("CRTM05"):\n        gc1, gc2 = st.columns(2)\n        crtm_easting = gc1.number_input(\n            "Este CRTM05 (m)", value=500000.0, step=1.0, format="%.3f", key="project_crtm_easting"\n        )\n        crtm_northing = gc2.number_input(\n            "Norte CRTM05 (m)", value=1100000.0, step=1.0, format="%.3f", key="project_crtm_northing"\n        )\n        longitude, latitude = crtm05_to_wgs84(crtm_easting, crtm_northing)\n        st.success(\n            f"Conversión automática WGS84 → Latitud **{latitude:.7f}°**, Longitud **{longitude:.7f}°**"\n        )\n    else:\n        gc1, gc2 = st.columns(2)\n        latitude = gc1.number_input(\n            "Latitud WGS84 (°)", min_value=-90.0, max_value=90.0, value=9.93, step=0.000001, format="%.7f", key="project_wgs84_latitude"\n        )\n        longitude = gc2.number_input(\n            "Longitud WGS84 (°)", min_value=-180.0, max_value=180.0, value=-84.10, step=0.000001, format="%.7f", key="project_wgs84_longitude"\n        )\n        crtm_easting, crtm_northing = wgs84_to_crtm05(longitude, latitude)\n        st.info(\n            f"Equivalente CRTM05 → Este **{crtm_easting:,.3f} m**, Norte **{crtm_northing:,.3f} m**"\n        )\n\n    if not is_plausible_costa_rica_wgs84(longitude, latitude):\n        st.warning("La coordenada convertida queda fuera del entorno geográfico amplio de Costa Rica. Revise sistema, Este/Norte o latitud/longitud antes de continuar.")\n\n    loc1, loc2, loc3, loc4 = st.columns(4)\n    loc1.metric("Este CRTM05", f"{crtm_easting:,.3f} m")\n    loc2.metric("Norte CRTM05", f"{crtm_northing:,.3f} m")\n    loc3.metric("Latitud WGS84", f"{latitude:.7f}°")\n    loc4.metric("Longitud WGS84", f"{longitude:.7f}°")\n    st.map(pd.DataFrame({"lat": [latitude], "lon": [longitude]}), latitude="lat", longitude="lon", zoom=10)\n    st.caption("Las coordenadas CRTM05 y WGS84 quedan incluidas en el estado guardado del proyecto y en las exportaciones.")\n'''
replace_once(old_project, new_project, 'pestaña Proyecto')

old_export = '''    ex1,ex2,ex3=st.columns(3)\n    start_e=ex1.number_input("Este inicial",value=500000.0,step=10.0)\n    start_n=ex2.number_input("Norte inicial",value=1100000.0,step=10.0)\n    azimuth=ex3.number_input("Azimut del eje (°)",0.0,360.0,value=90.0,step=1.0)\n    ex4,ex5,ex6=st.columns(3)\n    export_length=ex4.number_input("Longitud de eje (m)",1.0,value=float(length_m if 'length_m' in locals() else 150.0),step=10.0)\n    interval=ex5.number_input("Intervalo de puntos (m)",1.0,value=10.0,step=1.0)\n    elevation=ex6.number_input("Elevación de referencia (m)",value=100.0,step=0.1)\n    lon1,lat1,lon2,lat2=st.columns(4)\n    start_lon=lon1.number_input("Longitud inicial QGIS",-180.0,180.0,value=-84.10,format='%.6f')\n    start_lat=lat1.number_input("Latitud inicial QGIS",-90.0,90.0,value=9.93,format='%.6f')\n    end_lon=lon2.number_input("Longitud final QGIS",-180.0,180.0,value=-84.09,format='%.6f')\n    end_lat=lat2.number_input("Latitud final QGIS",-90.0,90.0,value=9.93,format='%.6f')\n'''

new_export = '''    st.info("Los valores iniciales se toman automáticamente de la ubicación definida en **1. Proyecto**. Puede modificarlos aquí si la exportación corresponde a otro punto del eje.")\n    ex1,ex2,ex3=st.columns(3)\n    start_e=ex1.number_input("Este inicial CRTM05",value=float(crtm_easting),step=10.0,format="%.3f")\n    start_n=ex2.number_input("Norte inicial CRTM05",value=float(crtm_northing),step=10.0,format="%.3f")\n    azimuth=ex3.number_input("Azimut del eje (°)",0.0,360.0,value=90.0,step=1.0)\n    ex4,ex5,ex6=st.columns(3)\n    export_length=ex4.number_input("Longitud de eje (m)",1.0,value=float(length_m if 'length_m' in locals() else 150.0),step=10.0)\n    interval=ex5.number_input("Intervalo de puntos (m)",1.0,value=10.0,step=1.0)\n    elevation=ex6.number_input("Elevación de referencia (m)",value=100.0,step=0.1)\n    lon1,lat1,lon2,lat2=st.columns(4)\n    start_lon=lon1.number_input("Longitud inicial QGIS (WGS84)",-180.0,180.0,value=float(longitude),format='%.7f')\n    start_lat=lat1.number_input("Latitud inicial QGIS (WGS84)",-90.0,90.0,value=float(latitude),format='%.7f')\n    end_lon=lon2.number_input("Longitud final QGIS (WGS84)",-180.0,180.0,value=float(longitude + 0.001),format='%.7f')\n    end_lat=lat2.number_input("Latitud final QGIS (WGS84)",-90.0,90.0,value=float(latitude),format='%.7f')\n'''
replace_once(old_export, new_export, 'exportación geográfica')

old_payload = '''            "road_type": road_type,\n            "pavement_type": pavement_type,\n        },\n'''
new_payload = '''            "road_type": road_type,\n            "pavement_type": pavement_type,\n            "coordinate_system_input": coordinate_system,\n            "crtm05_epsg": 5367,\n            "crtm05_easting_m": crtm_easting,\n            "crtm05_northing_m": crtm_northing,\n            "wgs84_epsg": 4326,\n            "latitude": latitude,\n            "longitude": longitude,\n        },\n'''
replace_once(old_payload, new_payload, 'payload de proyecto')

old_html = '''<b>Ubicación:</b> {project['location']}<br>\n<b>Fecha:</b> {project['date']}<br>\n<b>Responsable:</b> {project['engineer']}</p>\n'''
new_html = '''<b>Ubicación:</b> {project['location']}<br>\n<b>CRTM05 (EPSG:5367):</b> E {project.get('crtm05_easting_m', 0):,.3f} m · N {project.get('crtm05_northing_m', 0):,.3f} m<br>\n<b>WGS84 (EPSG:4326):</b> {project.get('latitude', 0):.7f}°, {project.get('longitude', 0):.7f}°<br>\n<b>Fecha:</b> {project['date']}<br>\n<b>Responsable:</b> {project['engineer']}</p>\n'''
replace_once(old_html, new_html, 'coordenadas en HTML')

old_pdf_intro = '''    story.append(Paragraph(f"Proyecto: {payload['project']['name']} — {payload['project']['location']}", styles["Normal"]))\n    story.append(Spacer(1,12))\n'''
new_pdf_intro = '''    story.append(Paragraph(f"Proyecto: {payload['project']['name']} — {payload['project']['location']}", styles["Normal"]))\n    story.append(Paragraph(\n        f"CRTM05 EPSG:5367: E {payload['project'].get('crtm05_easting_m', 0):,.3f} m, "\n        f"N {payload['project'].get('crtm05_northing_m', 0):,.3f} m · "\n        f"WGS84 EPSG:4326: {payload['project'].get('latitude', 0):.7f}°, {payload['project'].get('longitude', 0):.7f}°",\n        styles["Normal"],\n    ))\n    story.append(Spacer(1,12))\n'''
replace_once(old_pdf_intro, new_pdf_intro, 'coordenadas en PDF')

path.write_text(text, encoding='utf-8')
print('Integración CRTM05/WGS84 aplicada correctamente.')
