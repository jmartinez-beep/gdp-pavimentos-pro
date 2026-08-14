from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# VEHICLE_DECIMALS_AND_C4'
if MARKER in text:
    print('Decimales vehiculares y C4 ya integrados.')
    raise SystemExit(0)


def replace_once(old: str, new: str, label: str) -> None:
    global text
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: se esperaba 1 coincidencia y se encontraron {n}')
    text = text.replace(old, new, 1)

# 1) Añadir C4 a los valores por defecto sin asignar un factor camión universal.
old_defaults = '''        ["Camión C3", "Pesado", 1.40, 20],
        ["Tractocamión T3-S2", "Pesado", 2.20, 10],
'''
new_defaults = '''        ["Camión C3", "Pesado", 1.40, 20],
        ["Camión C4", "Pesado", 0.00, 0],
        ["Tractocamión T3-S2", "Pesado", 2.20, 10],
'''
replace_once(old_defaults, new_defaults, 'agregar C4 a VEHICLE_DEFAULTS')

# 2) Marcar bloque y asegurar C4 también al abrir proyectos guardados antiguos.
old_compat = '''    current.loc[current["Categoría"].eq("Pickup / carga liviana"), "Grupo de tránsito"] = "Carga liviana"

    vehicle_editor = current.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
'''
new_compat = '''    current.loc[current["Categoría"].eq("Pickup / carga liviana"), "Grupo de tránsito"] = "Carga liviana"

    # VEHICLE_DECIMALS_AND_C4
    # Compatibilidad con proyectos guardados antes de incorporar explícitamente la categoría C4.
    if not current["Categoría"].astype(str).str.strip().eq("Camión C4").any():
        c4 = pd.DataFrame([{
            "Categoría": "Camión C4",
            "Grupo de tránsito": "Pesado",
            "Factor camión": 0.0,
            "TPD": 0.0,
        }])
        c3_idx = current.index[current["Categoría"].astype(str).str.strip().eq("Camión C3")].tolist()
        insert_at = c3_idx[0] + 1 if c3_idx else len(current)
        current = pd.concat([current.iloc[:insert_at], c4, current.iloc[insert_at:]], ignore_index=True)
    current.loc[current["Categoría"].eq("Camión C4"), "Grupo de tránsito"] = "Pesado"

    vehicle_editor = current.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
'''
replace_once(old_compat, new_compat, 'compatibilidad C4')

# 3) Mantener TPD como decimal en vez de convertirlo a entero.
old_pre = '''    vehicle_editor["Cantidad diaria (veh/día)"] = pd.to_numeric(
        vehicle_editor["Cantidad diaria (veh/día)"], errors="coerce"
    ).fillna(0).astype(int)
'''
new_pre = '''    vehicle_editor["Cantidad diaria (veh/día)"] = pd.to_numeric(
        vehicle_editor["Cantidad diaria (veh/día)"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0).round(2)
'''
replace_once(old_pre, new_pre, 'TPD decimal antes del editor')

old_config = '''            "Cantidad diaria (veh/día)": st.column_config.NumberColumn(
                "Cantidad diaria (veh/día)",
                min_value=0,
                max_value=1_000_000,
                step=1,
                format="%d",
                help="Cantidad promedio de vehículos por día para esta categoría."
            ),
'''
new_config = '''            "Cantidad diaria (veh/día)": st.column_config.NumberColumn(
                "Cantidad diaria (veh/día)",
                min_value=0.0,
                max_value=1_000_000.0,
                step=0.01,
                format="%.2f",
                help="Cantidad promedio de vehículos por día para esta categoría. Admite hasta 2 decimales."
            ),
'''
replace_once(old_config, new_config, 'configurar editor a 2 decimales')

old_post = '''    edited_vehicles["Cantidad diaria (veh/día)"] = pd.to_numeric(
        edited_vehicles["Cantidad diaria (veh/día)"], errors="coerce"
    ).fillna(0).clip(lower=0).astype(int)
'''
new_post = '''    edited_vehicles["Cantidad diaria (veh/día)"] = pd.to_numeric(
        edited_vehicles["Cantidad diaria (veh/día)"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0).round(2)
'''
replace_once(old_post, new_post, 'conservar TPD decimal después del editor')

# 4) Mostrar totales con dos decimales para no ocultar fracciones ingresadas.
replace_once('    m1.metric("TPD total", f"{tpd_total:,.0f}")\n', '    m1.metric("TPD total", f"{tpd_total:,.2f}")\n', 'formato TPD total')
replace_once('    m2.metric("Vehículos pesados", f"{heavy_total:,.0f}", f"{heavy_pct:.2f}%")\n', '    m2.metric("Vehículos pesados", f"{heavy_total:,.2f}", f"{heavy_pct:.2f}%")\n', 'formato pesados')

APP.write_text(text, encoding='utf-8')
print('Cantidad vehicular con 2 decimales y categoría C4 integradas correctamente.')
