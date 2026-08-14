from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# ADVANCED_DESIGN_CONTROLS_6_7_8_9_10_11_16_18_20'
if MARKER in text:
    print('Controles avanzados ya integrados.')
    raise SystemExit(0)


def replace_once(old: str, new: str, label: str) -> None:
    global text
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: se esperaba una coincidencia y se encontraron {n}')
    text = text.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Helpers: materiales, interfaces, base estabilizada, restricciones, escenarios.
# -----------------------------------------------------------------------------
anchor = "# AASHTO93_LAYER_CONTROLS\n"
helpers = '''# ADVANCED_DESIGN_CONTROLS_6_7_8_9_10_11_16_18_20

def stabilized_base_screening_model(modulus_mpa: float, strength_mpa: float, thickness_cm: float,
                                    shrinkage_risk: str, interface_condition: str) -> dict:
    """Caracterización propia de base estabilizada para control/cribado.

    No sustituye una función de transferencia calibrada. Resume rigidez, resistencia,
    esbeltez, contracción e interfaz para decidir si la capa requiere revisión específica.
    """
    e = max(float(modulus_mpa), 0.0)
    r = max(float(strength_mpa), 0.0)
    h = max(float(thickness_cm), 0.0)
    rigidity_index = e * (h / 10.0) ** 3 if h > 0 else 0.0
    risk_score = {'Bajo': 0.8, 'Medio': 1.0, 'Alto': 1.25}.get(str(shrinkage_risk), 1.0)
    interface_factor = {'Adherida': 1.0, 'Parcialmente adherida': 1.10, 'Deslizante': 1.25}.get(str(interface_condition), 1.0)
    return {
        'modulus_mpa': e, 'strength_mpa': r, 'thickness_cm': h,
        'rigidity_index': rigidity_index,
        'shrinkage_risk': shrinkage_risk,
        'interface_condition': interface_condition,
        'screening_penalty_factor': risk_score * interface_factor,
        'status': 'Caracterizada' if h > 0 and e > 0 and r > 0 else 'Incompleta',
        'note': 'Modelo propio de caracterización/cribado; requiere verificación estructural y de fisuración reflejada.'
    }


def construction_constraints_check(structure: dict, constraints: dict) -> dict:
    ac = float(structure.get('Carpeta_cm', 0) or 0)
    base = float(structure.get('Base_cm', 0) or 0)
    subbase = float(structure.get('Subbase_cm', 0) or 0)
    inc = max(float(constraints.get('increment_cm', 0.5) or 0.5), 0.1)
    checks = {
        'carpeta_min': ac >= float(constraints.get('asphalt_min_cm', 0) or 0),
        'carpeta_max': ac <= float(constraints.get('asphalt_max_cm', 999) or 999),
        'base_min': base >= float(constraints.get('base_min_cm', 0) or 0),
        'subbase_min': subbase >= float(constraints.get('subbase_min_cm', 0) or 0),
        'incremento_carpeta': abs(ac / inc - round(ac / inc)) < 1e-6,
        'incremento_base': abs(base / inc - round(base / inc)) < 1e-6,
        'incremento_subbase': abs(subbase / inc - round(subbase / inc)) < 1e-6,
    }
    return {'complies': all(checks.values()), 'checks': checks, 'increment_cm': inc}


def optimize_structure_with_constraints(base_structure: dict, materials: dict, subgrade_mr_mpa: float,
                                        axle_load_kn: float, tire_pressure_kpa: float, tires_per_axle: int,
                                        allowable_eps_t: float, allowable_eps_v: float, reliability_pct: float,
                                        log_sigma: float, area_m2: float, prices: dict, constraints: dict,
                                        max_increment_cm: float = 10.0) -> pd.DataFrame:
    """Optimización discreta de cribado con restricciones constructivas obligatorias."""
    rows = []
    step = max(float(constraints.get('increment_cm', 1.0) or 1.0), 0.5)
    incs = []
    x = 0.0
    while x <= float(max_increment_cm) + 1e-9:
        incs.append(round(x, 6)); x += step
    ac0 = float(base_structure.get('Carpeta_cm', 0) or 0)
    bg0 = float(base_structure.get('Base_granular_cm', base_structure.get('Base_cm', 0)) or 0)
    bs0 = float(base_structure.get('Base_estabilizada_cm', 0) or 0)
    sb0 = float(base_structure.get('Subbase_cm', 0) or 0)
    rel_mult = reliability_multiplier(reliability_pct, log_sigma)
    for da in incs:
        for db in incs:
            for ds in incs:
                s = dict(base_structure)
                s['Carpeta_cm'] = ac0 + da
                s['Base_granular_cm'] = bg0 + db
                s['Base_estabilizada_cm'] = bs0
                s['Base_cm'] = bg0 + db + bs0
                s['Subbase_cm'] = sb0 + ds
                cc = construction_constraints_check(s, constraints)
                if not cc['complies']:
                    continue
                resp = mechanistic_screening_response(s, materials, subgrade_mr_mpa, axle_load_kn, tire_pressure_kpa, tires_per_axle)
                fu = resp['asphalt_tensile_microstrain_screening'] / max(float(allowable_eps_t), 1e-6) * rel_mult
                ru = resp['subgrade_vertical_microstrain_screening'] / max(float(allowable_eps_v), 1e-6) * rel_mult
                cost = float(area_m2) * (
                    s['Carpeta_cm']/100.0*float(prices.get('surface',0)) +
                    s['Base_cm']/100.0*float(prices.get('base',0)) +
                    s['Subbase_cm']/100.0*float(prices.get('subbase',0))
                )
                rows.append({
                    'Código': f"OPT-{len(rows)+1:04d}", 'Carpeta_cm': s['Carpeta_cm'],
                    'Base_cm': s['Base_cm'], 'Subbase_cm': s['Subbase_cm'],
                    'Espesor_total_cm': s['Carpeta_cm']+s['Base_cm']+s['Subbase_cm'],
                    'Utilización_fatiga_diseño': fu, 'Utilización_ahuellamiento_diseño': ru,
                    'Máxima_utilización': max(fu,ru), 'Cumple_cribado': 'Sí' if max(fu,ru)<=1.0 else 'No',
                    'Cumple_constructivo': 'Sí', 'Costo_inicial': cost,
                })
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out['Cumple_num'] = out['Cumple_cribado'].eq('Sí').astype(int)
    return out.sort_values(['Cumple_num','Costo_inicial','Máxima_utilización','Espesor_total_cm'], ascending=[False,True,True,True]).drop(columns=['Cumple_num']).reset_index(drop=True)


def engineering_readiness_score(payload: dict) -> tuple[int, list[dict]]:
    mats = payload.get('materials', {}) or {}
    mech = payload.get('mechanistic_screening', {}) or {}
    interfaces = payload.get('layer_interfaces', {}) or {}
    constraints = payload.get('construction_constraints', {}) or {}
    climate = payload.get('climate_material', {}) or {}
    items = [
        ('Tránsito y categoría', float(payload.get('traffic',{}).get('esal',0) or 0)>0, 12),
        ('Subrasante Mr documentado/estimado', float(payload.get('subgrade',{}).get('mr',0) or 0)>0, 10),
        ('Granulares caracterizados', bool(mats.get('granular_quality')), 12),
        ('Modelo granular k1-k2-k3', bool(mats.get('granular_model')), 8),
        ('Mezcla E* documentada', float(mats.get('asphalt_dynamic_modulus_mpa',0) or 0)>0, 10),
        ('Curva maestra/clima', bool(climate), 10),
        ('Interfaces documentadas', bool(interfaces), 8),
        ('Restricciones constructivas', bool(constraints), 8),
        ('Respuesta mecanística ejecutada', bool(mech), 12),
        ('Fuente de materiales', bool(str(mats.get('source','')).strip()), 10),
    ]
    score = sum(w for _,ok,w in items if ok)
    detail = [{'Componente':n,'Estado':'Completo' if ok else 'Pendiente','Peso':w} for n,ok,w in items]
    return int(min(score,100)), detail


def scenario_comparison_table(base_esal: float, base_mr: float, base_temp: float, selected: dict,
                              materials: dict, axle_load_kn: float, tire_pressure_kpa: float,
                              tires_per_axle: int, allowable_eps_t: float, allowable_eps_v: float) -> pd.DataFrame:
    scenarios = [
        ('Conservador', 1.25, 0.80, 5.0),
        ('Esperado', 1.00, 1.00, 0.0),
        ('Optimista', 0.85, 1.15, -3.0),
    ]
    rows = []
    for name, traffic_factor, mr_factor, temp_delta in scenarios:
        mr_s = max(float(base_mr)*mr_factor, 1.0)
        esal_s = max(float(base_esal)*traffic_factor, 1.0)
        resp = mechanistic_screening_response(selected, materials, mr_s, axle_load_kn, tire_pressure_kpa, tires_per_axle)
        fu = resp['asphalt_tensile_microstrain_screening']/max(float(allowable_eps_t),1e-6)
        ru = resp['subgrade_vertical_microstrain_screening']/max(float(allowable_eps_v),1e-6)
        rows.append({'Escenario':name,'Factor_tránsito':traffic_factor,'ESAL':esal_s,'Factor_Mr':mr_factor,
                     'Mr_subrasante_MPa':mr_s,'Temperatura_pavimento_C':float(base_temp)+temp_delta,
                     'Utilización_fatiga':fu,'Utilización_ahuellamiento':ru,'Máxima_utilización':max(fu,ru),
                     'Estado':'Cumple cribado' if max(fu,ru)<=1.0 else 'Revisar'})
    return pd.DataFrame(rows)

'''
replace_once(anchor, helpers + anchor, 'insertar helpers avanzados')

# -----------------------------------------------------------------------------
# 6, 7 y 8: materiales completos, base estabilizada e interfaces.
# -----------------------------------------------------------------------------
anchor_material = '''        st.markdown("##### Modelo constitutivo para arenas / bases / subbases granulares")
'''
material_block = '''        st.markdown("##### Calidad y procedencia de materiales granulares")
        qg1, qg2, qg3, qg4 = st.columns(4)
        granular_aashto = qg1.text_input("Clasificación AASHTO del granular", value="", key='granular_aashto')
        granular_sucs = qg2.text_input("Clasificación SUCS del granular", value="", key='granular_sucs')
        granular_ll = qg3.number_input("LL granular (%)", min_value=0.0, max_value=150.0, value=0.0, step=1.0, key='granular_ll')
        granular_pi = qg4.number_input("IP granular (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key='granular_pi')
        qg5, qg6, qg7, qg8 = st.columns(4)
        granular_moisture = qg5.number_input("Humedad granular (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key='granular_moisture')
        granular_density = qg6.number_input("Densidad seca granular (kg/m³)", min_value=0.0, max_value=3000.0, value=0.0, step=10.0, key='granular_density')
        granular_cbr = qg7.number_input("CBR del granular (%)", min_value=0.0, max_value=200.0, value=80.0, step=1.0, key='granular_cbr_full')
        granular_data_origin = qg8.selectbox("Origen de propiedades", ["Ensayo medido", "Informe del proyecto", "Estimado", "Asumido"], key='granular_origin')
        st.session_state.granular_quality = {
            'aashto': granular_aashto, 'sucs': granular_sucs, 'll_pct': granular_ll, 'pi_pct': granular_pi,
            'moisture_pct': granular_moisture, 'dry_density_kg_m3': granular_density, 'cbr_pct': granular_cbr,
            'data_origin': granular_data_origin,
        }

''' + anchor_material
replace_once(anchor_material, material_block, 'agregar caracterización granular completa')

anchor_before_state = '''        st.session_state.design_materials = {
'''
advanced_material = '''        st.markdown("##### Modelo específico de base estabilizada e interfaces")
        ib1, ib2, ib3 = st.columns(3)
        interface_ac_base = ib1.selectbox("Interfaz carpeta / base", ["Adherida", "Parcialmente adherida", "Deslizante"], key='interface_ac_base')
        interface_base_subbase = ib2.selectbox("Interfaz base / subbase", ["Adherida", "Parcialmente adherida", "Deslizante"], key='interface_base_subbase')
        interface_subbase_subgrade = ib3.selectbox("Interfaz subbase / subrasante", ["Adherida", "Parcialmente adherida", "Deslizante"], index=1, key='interface_subbase_subgrade')
        st.session_state.layer_interfaces = {
            'asphalt_base': interface_ac_base, 'base_subbase': interface_base_subbase,
            'subbase_subgrade': interface_subbase_subgrade,
            'solver_status': 'Documentadas; el cribado actual solo las usa como factor de revisión. El solver multicapa futuro deberá imponerlas matemáticamente.'
        }
        stabilized_shrinkage = st.selectbox("Riesgo de contracción de base estabilizada", ["Bajo", "Medio", "Alto"], index=1, key='stabilized_shrinkage')
        stabilized_model = stabilized_base_screening_model(stabilized_modulus, stabilized_strength, base_stabilized_cm, stabilized_shrinkage, interface_ac_base)
        st.session_state.stabilized_base_model = stabilized_model
        if base_stabilized_cm > 0:
            sbm1, sbm2, sbm3 = st.columns(3)
            sbm1.metric("Índice de rigidez estabilizada", f"{stabilized_model['rigidity_index']:,.0f}")
            sbm2.metric("Factor contracción/interfaz", f"{stabilized_model['screening_penalty_factor']:.2f}")
            sbm3.metric("Estado", stabilized_model['status'])
            st.caption("La base estabilizada se trata como material propio para trazabilidad de rigidez, resistencia, contracción e interfaz; no como simple sustitución de una base granular.")

''' + anchor_before_state
replace_once(anchor_before_state, advanced_material, 'agregar base estabilizada e interfaces')

# Extend design_materials with quality/provenance and stabilized model.
old_fragment = '''            "granular_model": {'material':granular_type,'k1':granular_k1,'k2':granular_k2,'k3':granular_k3,'theta_kpa':theta_kpa,'tau_oct_kpa':tau_oct_kpa,'pa_kpa':pa_kpa,'mr_calculated_mpa':granular_mr_calc,'application':granular_apply_note},
            "stabilized_modulus_mpa": float(stabilized_modulus), "stabilized_strength_mpa": float(stabilized_strength),
'''
new_fragment = '''            "granular_model": {'material':granular_type,'k1':granular_k1,'k2':granular_k2,'k3':granular_k3,'theta_kpa':theta_kpa,'tau_oct_kpa':tau_oct_kpa,'pa_kpa':pa_kpa,'mr_calculated_mpa':granular_mr_calc,'application':granular_apply_note},
            "granular_quality": st.session_state.get('granular_quality', {}),
            "layer_interfaces": st.session_state.get('layer_interfaces', {}),
            "stabilized_base_model": st.session_state.get('stabilized_base_model', {}),
            "stabilized_modulus_mpa": float(stabilized_modulus), "stabilized_strength_mpa": float(stabilized_strength),
'''
replace_once(old_fragment, new_fragment, 'extender materiales')

# -----------------------------------------------------------------------------
# 9, 10 y 11: restricciones constructivas + optimizador discreto.
# -----------------------------------------------------------------------------
old_opt_header = '''        st.markdown("#### Diseño iterativo automático — candidatos de cribado")
        st.caption("Explora incrementos discretos de carpeta/base/subbase y descarta primero candidatos que no cumplen el cribado a confiabilidad. No reemplaza la optimización del solver multicapa definitivo.")
'''
new_opt_header = '''        st.markdown("#### Restricciones constructivas y optimización automática")
        st.caption("El optimizador solo evalúa combinaciones que respetan los límites constructivos documentados. Continúa siendo un cribado hasta disponer del solver multicapa definitivo.")
        cc1, cc2, cc3, cc4 = st.columns(4)
        constr_asphalt_min = cc1.number_input("Carpeta mínima para optimizador (cm)", min_value=0.0, max_value=40.0, value=float(st.session_state.get('asphalt_thickness_control',{}).get('min_cm',5.0)), step=0.5, key='constr_asphalt_min')
        constr_asphalt_max = cc2.number_input("Carpeta máxima para optimizador (cm)", min_value=0.0, max_value=80.0, value=float(st.session_state.get('asphalt_thickness_control',{}).get('max_cm',20.0)), step=0.5, key='constr_asphalt_max')
        constr_base_min = cc3.number_input("Base mínima (cm)", min_value=0.0, max_value=100.0, value=15.0, step=1.0, key='constr_base_min')
        constr_subbase_min = cc4.number_input("Subbase mínima (cm)", min_value=0.0, max_value=120.0, value=15.0, step=1.0, key='constr_subbase_min')
        cc5, cc6 = st.columns(2)
        constr_increment = cc5.selectbox("Incremento constructivo de espesores (cm)", [0.5, 1.0, 2.0], index=1, key='constr_increment')
        constr_source = cc6.text_input("Fuente / criterio constructivo", value="Criterio del proyecto — documentar", key='constr_source')
        construction_constraints = {
            'asphalt_min_cm': float(constr_asphalt_min), 'asphalt_max_cm': float(constr_asphalt_max),
            'base_min_cm': float(constr_base_min), 'subbase_min_cm': float(constr_subbase_min),
            'increment_cm': float(constr_increment), 'source': constr_source,
        }
        st.session_state.construction_constraints = construction_constraints
        current_cc = construction_constraints_check(selected_row, construction_constraints)
        if current_cc['complies']:
            st.success("La sección activa satisface las restricciones constructivas configuradas.")
        else:
            failed = [k for k,v in current_cc['checks'].items() if not v]
            st.warning("La sección activa incumple restricciones constructivas: " + ", ".join(failed))

        st.markdown("#### Diseño iterativo automático — candidatos restringidos")
'''
replace_once(old_opt_header, new_opt_header, 'reemplazar encabezado optimización')

old_button = '''        if st.button("Generar candidatos de diseño", key="run_screening_optimization"):
            opt_df = optimize_screening_structure(
                selected_row, materials_for_response, mr, axle_load_kn, tire_pressure_kpa, int(tires_per_axle),
                allowable_eps_t, allowable_eps_v, reliability_pct, response_log_sigma, opt_area,
                {'surface': opt_surface_price, 'base': opt_base_price, 'subbase': opt_subbase_price}, int(opt_max_inc)
            )
            st.session_state.optimization_candidates = opt_df
'''
new_button = '''        if st.button("Generar candidatos de diseño", key="run_screening_optimization"):
            opt_df = optimize_structure_with_constraints(
                selected_row, materials_for_response, mr, axle_load_kn, tire_pressure_kpa, int(tires_per_axle),
                allowable_eps_t, allowable_eps_v, reliability_pct, response_log_sigma, opt_area,
                {'surface': opt_surface_price, 'base': opt_base_price, 'subbase': opt_subbase_price},
                construction_constraints, float(opt_max_inc)
            )
            st.session_state.optimization_candidates = opt_df
'''
replace_once(old_button, new_button, 'cambiar optimizador')

# -----------------------------------------------------------------------------
# 20: comparador de escenarios dentro de Comparación.
# -----------------------------------------------------------------------------
anchor_compare_end = '''            st.session_state.alternatives_compare = show

with p5:
'''
scenario_block = '''            st.session_state.alternatives_compare = show

        st.markdown("#### Comparador de escenarios — sensibilidad estructural")
        st.caption("Compara un escenario conservador, esperado y optimista variando tránsito y soporte. Es análisis de sensibilidad, no sustitución de un estudio probabilístico.")
        scenario_mech = st.session_state.get('mechanistic_screening', {})
        if selected_row and scenario_mech:
            scenario_df = scenario_comparison_table(
                esal, mr, tp_ltpp, selected_row, st.session_state.get('design_materials', {}),
                float(scenario_mech.get('axle_load_kn',80.0)), float(scenario_mech.get('tire_pressure_kpa',700.0)),
                int(scenario_mech.get('tires_per_axle',4)), float(scenario_mech.get('allowable_asphalt_tensile_microstrain',200.0)),
                float(scenario_mech.get('allowable_subgrade_vertical_microstrain',500.0))
            )
            st.session_state.scenario_comparison = scenario_df
            st.dataframe(scenario_df, use_container_width=True, hide_index=True)
            sc_fig = go.Figure()
            sc_fig.add_trace(go.Bar(name='Fatiga', x=scenario_df['Escenario'], y=scenario_df['Utilización_fatiga']))
            sc_fig.add_trace(go.Bar(name='Ahuellamiento', x=scenario_df['Escenario'], y=scenario_df['Utilización_ahuellamiento']))
            sc_fig.update_layout(barmode='group', height=330, yaxis_title='Utilización', title='Sensibilidad por escenario')
            st.plotly_chart(sc_fig, use_container_width=True, config={'displaylogo': False})
        else:
            st.info("Ejecute primero la respuesta mecanística en Diseño flexible para habilitar escenarios.")

with p5:
'''
replace_once(anchor_compare_end, scenario_block, 'agregar escenarios')

# -----------------------------------------------------------------------------
# 16: indicador de madurez técnica en Validación.
# -----------------------------------------------------------------------------
anchor_validation = '''        st.markdown("#### Matriz de evidencia normativa")
'''
validation_extra = '''        readiness_payload = {
            'traffic': {'esal': esal}, 'subgrade': {'mr': mr},
            'materials': st.session_state.get('design_materials', {}),
            'mechanistic_screening': st.session_state.get('mechanistic_screening', {}),
            'layer_interfaces': st.session_state.get('layer_interfaces', {}),
            'construction_constraints': st.session_state.get('construction_constraints', {}),
            'climate_material': st.session_state.get('climate_material', {}),
        }
        readiness_score, readiness_detail = engineering_readiness_score(readiness_payload)
        st.markdown("#### Índice de madurez técnica del diseño")
        rd1, rd2 = st.columns([1,3])
        rd1.metric("Madurez técnica", f"{readiness_score}%")
        rd2.dataframe(pd.DataFrame(readiness_detail), use_container_width=True, hide_index=True)
        st.session_state.engineering_readiness = {'score': readiness_score, 'detail': readiness_detail}

''' + anchor_validation
replace_once(anchor_validation, validation_extra, 'agregar madurez técnica')

# -----------------------------------------------------------------------------
# 18: payload, Excel e informe auditable.
# -----------------------------------------------------------------------------
anchor_payload = '''        "asphalt_thickness_control": st.session_state.get("asphalt_thickness_control", {}),
        "mechanistic_screening": st.session_state.get("mechanistic_screening", {}) if active_tomo == "Tomo I" else {},
'''
new_payload = '''        "asphalt_thickness_control": st.session_state.get("asphalt_thickness_control", {}),
        "granular_quality": st.session_state.get("granular_quality", {}),
        "layer_interfaces": st.session_state.get("layer_interfaces", {}),
        "stabilized_base_model": st.session_state.get("stabilized_base_model", {}),
        "construction_constraints": st.session_state.get("construction_constraints", {}),
        "engineering_readiness": st.session_state.get("engineering_readiness", {}),
        "scenario_comparison": st.session_state.get("scenario_comparison", pd.DataFrame()).to_dict(orient="records") if isinstance(st.session_state.get("scenario_comparison", pd.DataFrame()), pd.DataFrame) else [],
        "mechanistic_screening": st.session_state.get("mechanistic_screening", {}) if active_tomo == "Tomo I" else {},
'''
replace_once(anchor_payload, new_payload, 'extender payload')

anchor_quality = '''    quality_score, quality_detail = design_data_quality_score(payload)
    st.markdown("#### Estado profesional del expediente")
'''
new_quality = '''    quality_score, quality_detail = design_data_quality_score(payload)
    readiness_score, readiness_detail = engineering_readiness_score(payload)
    st.markdown("#### Estado profesional del expediente")
'''
replace_once(anchor_quality, new_quality, 'calcular madurez en informe')

old_metrics = '''    qi1, qi2, qi3 = st.columns(3)
    qi1.metric("Calidad documental", f"{quality_score}%")
    qi2.metric("Tramos homogéneos", f"{len(payload.get('homogeneous_segments', []))}")
    qi3.metric("Candidatos optimizados", f"{len(payload.get('optimization_candidates', []))}")
'''
new_metrics = '''    qi1, qi2, qi3, qi4 = st.columns(4)
    qi1.metric("Calidad documental", f"{quality_score}%")
    qi2.metric("Madurez técnica", f"{readiness_score}%")
    qi3.metric("Tramos homogéneos", f"{len(payload.get('homogeneous_segments', []))}")
    qi4.metric("Candidatos optimizados", f"{len(payload.get('optimization_candidates', []))}")
'''
replace_once(old_metrics, new_metrics, 'ampliar métricas informe')

anchor_after_detail = '''    st.dataframe(pd.DataFrame(quality_detail), use_container_width=True, hide_index=True)
'''
audit_ui = anchor_after_detail + '''    st.markdown("#### Registro de cálculo auditable")
    audit_rows = [
        {'Etapa':'Tránsito','Ecuación / método':'EEq = 365·Σ(TPDᵢ·FCᵢ)·FD·FCarril·G','Resultado':f"{esal:,.0f} ESAL",'Estado':'Calculado'},
        {'Etapa':'AASHTO-93','Ecuación / método':'SN = a1D1 + a2m2D2 + a3m3D3','Resultado':f"SN={float(st.session_state.get('flex_design',{}).get('sn',0)):.2f}",'Estado':'Preliminar'},
        {'Etapa':'Granulares','Ecuación / método':'Mr=k1·Pa·(θ/Pa)^k2·(τoct/Pa+1)^k3','Resultado':f"Mr={float(payload.get('materials',{}).get('granular_model',{}).get('mr_calculated_mpa',0)):.1f} MPa",'Estado':'Configurable/documentado'},
        {'Etapa':'Clima / mezcla','Ecuación / método':'WLF + curva maestra E*','Resultado':f"E*={float(payload.get('climate_material',{}).get('effective_modulus_mpa',0)):.0f} MPa",'Estado':'Según parámetros documentados'},
        {'Etapa':'Respuesta estructural','Ecuación / método':str(payload.get('mechanistic_screening',{}).get('method','No ejecutado')),'Resultado':f"Umax={max(float(payload.get('mechanistic_screening',{}).get('fatigue_utilization_design',0) or 0),float(payload.get('mechanistic_screening',{}).get('rutting_utilization_design',0) or 0)):.2f}",'Estado':'Cribado'},
        {'Etapa':'Restricciones constructivas','Ecuación / método':'Mínimos/máximos + incremento constructivo','Resultado':str(payload.get('construction_constraints',{})),'Estado':'Criterio documentado del proyecto'},
    ]
    st.session_state.calculation_audit = audit_rows
    st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
'''
replace_once(anchor_after_detail, audit_ui, 'agregar registro auditable')

# Excel sheets: anchor known from previous integration.
anchor_excel = '''        pd.DataFrame(payload.get("normative_evidence", [])).to_excel(writer, sheet_name="Evidencia_normativa", index=False)
'''
excel_extra = anchor_excel + '''        pd.DataFrame([payload.get("granular_quality", {})]).to_excel(writer, sheet_name="Granulares_calidad", index=False)
        pd.DataFrame([payload.get("layer_interfaces", {})]).to_excel(writer, sheet_name="Interfaces", index=False)
        pd.DataFrame([payload.get("stabilized_base_model", {})]).to_excel(writer, sheet_name="Base_estabilizada", index=False)
        pd.DataFrame([payload.get("construction_constraints", {})]).to_excel(writer, sheet_name="Restricciones", index=False)
        pd.DataFrame(payload.get("scenario_comparison", [])).to_excel(writer, sheet_name="Escenarios", index=False)
'''
replace_once(anchor_excel, excel_extra, 'ampliar Excel')

APP.write_text(text, encoding='utf-8')
print('Puntos 6,7,8,9,10,11,16,18 y 20 integrados.')
