from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old_defaults = '''VEHICLE_DEFAULTS = pd.DataFrame(
    [
        ["Vehículos livianos", 0.0001, 800],
        ["Buses", 0.65, 20],
        ["Camión C2", 0.80, 35],
        ["Camión C3", 1.40, 20],
        ["Tractocamión T3-S2", 2.20, 10],
        ["Otros pesados", 1.00, 5],
    ],
    columns=["Categoría", "Factor camión", "TPD"],
)
'''
new_defaults = '''VEHICLE_DEFAULTS = pd.DataFrame(
    [
        ["Automóviles / vehículos livianos", "Liviano", 0.0001, 800],
        ["Pickup / carga liviana", "Carga liviana", 0.0000, 0],
        ["Buses", "Pesado", 0.65, 20],
        ["Camión C2", "Pesado", 0.80, 35],
        ["Camión C3", "Pesado", 1.40, 20],
        ["Tractocamión T3-S2", "Pesado", 2.20, 10],
        ["Otros pesados", "Pesado", 1.00, 5],
    ],
    columns=["Categoría", "Grupo de tránsito", "Factor camión", "TPD"],
)
'''
if old_defaults not in s:
    raise SystemExit('No se encontró VEHICLE_DEFAULTS esperado')
s = s.replace(old_defaults, new_defaults, 1)

old_current = '''    current = st.session_state.vehicles.copy()
    vehicle_editor = current.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
        ["Categoría", "Cantidad diaria (veh/día)", "Factor camión"]
    ]
'''
new_current = '''    current = st.session_state.vehicles.copy()

    # Compatibilidad con proyectos guardados antes de separar pickup/carga liviana.
    if "Grupo de tránsito" not in current.columns:
        current["Grupo de tránsito"] = current["Categoría"].astype(str).map(
            lambda x: "Liviano" if x.strip().lower() == "vehículos livianos" else "Pesado"
        )
    current["Categoría"] = current["Categoría"].replace({"Vehículos livianos": "Automóviles / vehículos livianos"})
    current.loc[current["Categoría"].eq("Automóviles / vehículos livianos"), "Grupo de tránsito"] = "Liviano"
    if not current["Categoría"].astype(str).eq("Pickup / carga liviana").any():
        pickup = pd.DataFrame([{
            "Categoría": "Pickup / carga liviana",
            "Grupo de tránsito": "Carga liviana",
            "Factor camión": 0.0,
            "TPD": 0,
        }])
        current = pd.concat([current.iloc[:1], pickup, current.iloc[1:]], ignore_index=True)
    current.loc[current["Categoría"].eq("Pickup / carga liviana"), "Grupo de tránsito"] = "Carga liviana"

    vehicle_editor = current.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
        ["Categoría", "Grupo de tránsito", "Cantidad diaria (veh/día)", "Factor camión"]
    ]
'''
if old_current not in s:
    raise SystemExit('No se encontró bloque current esperado')
s = s.replace(old_current, new_current, 1)

old_config = '''            "Cantidad diaria (veh/día)": st.column_config.NumberColumn(
                "Cantidad diaria (veh/día)",
                min_value=0,
                max_value=1_000_000,
                step=1,
                format="%d",
                help="Cantidad promedio de vehículos por día para esta categoría."
            ),
            "Factor camión": st.column_config.NumberColumn(
'''
new_config = '''            "Grupo de tránsito": st.column_config.TextColumn(
                "Grupo de tránsito",
                disabled=True,
                help="Clasificación usada para separar tránsito liviano, carga liviana y vehículos pesados. Solo el grupo Pesado entra en el porcentaje de pesados del Tomo II."
            ),
            "Cantidad diaria (veh/día)": st.column_config.NumberColumn(
                "Cantidad diaria (veh/día)",
                min_value=0,
                max_value=1_000_000,
                step=1,
                format="%d",
                help="Cantidad promedio de vehículos por día para esta categoría."
            ),
            "Factor camión": st.column_config.NumberColumn(
'''
if old_config not in s:
    raise SystemExit('No se encontró column_config esperado')
s = s.replace(old_config, new_config, 1)

old_vehicles = '''    vehicles = edited_vehicles.rename(columns={"Cantidad diaria (veh/día)": "TPD"})[
        ["Categoría", "Factor camión", "TPD"]
    ]
'''
new_vehicles = '''    vehicles = edited_vehicles.rename(columns={"Cantidad diaria (veh/día)": "TPD"})[
        ["Categoría", "Grupo de tránsito", "Factor camión", "TPD"]
    ]
'''
if old_vehicles not in s:
    raise SystemExit('No se encontró construcción vehicles esperada')
s = s.replace(old_vehicles, new_vehicles, 1)

old_summary = '''    summary_vehicles = vehicles.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
        ["Categoría", "Cantidad diaria (veh/día)", "Factor camión"]
    ]
'''
new_summary = '''    summary_vehicles = vehicles.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
        ["Categoría", "Grupo de tránsito", "Cantidad diaria (veh/día)", "Factor camión"]
    ]
'''
if old_summary not in s:
    raise SystemExit('No se encontró summary esperado')
s = s.replace(old_summary, new_summary, 1)

old_heavy = '''    heavy_mask = vehicles["Categoría"].str.lower().ne("vehículos livianos")
    heavy_total = float(vehicles.loc[heavy_mask, "TPD"].sum())
'''
new_heavy = '''    heavy_mask = vehicles["Grupo de tránsito"].astype(str).str.strip().str.lower().eq("pesado")
    heavy_total = float(vehicles.loc[heavy_mask, "TPD"].sum())
'''
if old_heavy not in s:
    raise SystemExit('No se encontró heavy_mask esperado')
s = s.replace(old_heavy, new_heavy, 1)

old_info = '''        "Ingrese el conteo diario en la columna **Cantidad diaria (veh/día)**. "
        "El **Factor camión** es un parámetro técnico independiente utilizado para convertir cada categoría a ejes equivalentes."
'''
new_info = '''        "Ingrese el conteo diario en la columna **Cantidad diaria (veh/día)**. "
        "Se separan **automóviles**, **pickup/carga liviana** y **vehículos pesados**. "
        "El **Factor camión** es un parámetro técnico independiente utilizado para convertir cada categoría a ejes equivalentes; para pickup/carga liviana debe usarse el valor documentado por el estudio o proyecto."
'''
if old_info not in s:
    raise SystemExit('No se encontró texto informativo esperado')
s = s.replace(old_info, new_info, 1)

old_expander = '''            "- **Factor camión:** parámetro técnico de equivalencia de carga; no representa una cantidad de vehículos.\\n"
            "- El cálculo de ejes equivalentes combina ambos valores, pero se mantienen separados para evitar errores de digitación."
'''
new_expander = '''            "- **Factor camión:** parámetro técnico de equivalencia de carga; no representa una cantidad de vehículos.\\n"
            "- **Grupo de tránsito:** controla la clasificación para el porcentaje de pesados del Tomo II. Pickup/carga liviana no se suma automáticamente como vehículo pesado.\\n"
            "- El cálculo de ejes equivalentes usa el factor individual de cada fila; no se asigna un factor normativo universal a pickup/carga liviana."
'''
if old_expander not in s:
    raise SystemExit('No se encontró expander esperado')
s = s.replace(old_expander, new_expander, 1)

p.write_text(s, encoding='utf-8')
print('Integración de pickup/carga liviana aplicada correctamente')
