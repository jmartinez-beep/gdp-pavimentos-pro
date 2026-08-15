from pathlib import Path

p = Path('app.py')
s = p.read_text(encoding='utf-8')

old_controls = '''            f1,f2,f3,f4 = st.columns(4)
            a1 = f1.number_input("Coeficiente estructural carpeta a1", min_value=0.01, max_value=1.0, value=0.44, step=0.01, key="aashto_a1")
            a2 = f2.number_input("Coeficiente estructural base a2", min_value=0.01, max_value=1.0, value=0.14, step=0.01, key="aashto_a2")
            a3 = f3.number_input("Coeficiente estructural subbase a3", min_value=0.01, max_value=1.0, value=0.11, step=0.01, key="aashto_a3")
            m2 = f4.number_input("Coeficiente drenaje base m2", min_value=0.4, max_value=1.4, value=1.00, step=0.05, key="aashto_m2")
            m3 = st.number_input("Coeficiente drenaje subbase m3", min_value=0.4, max_value=1.4, value=1.00, step=0.05, key="aashto_m3")

            d1=float(selected_row['Carpeta_cm'])/2.54; d2=float(selected_row['Base_cm'])/2.54; d3=float(selected_row['Subbase_cm'])/2.54
            sn1=a1*d1; sn2=a2*m2*d2; sn3=a3*m3*d3; sn_total=sn1+sn2+sn3
            sn_cum1 = sn1; sn_cum2 = sn1 + sn2; sn_cum3 = sn_total
'''

new_controls = '''            f1,f2,f3,f4 = st.columns(4)
            a1 = f1.number_input("Coeficiente estructural carpeta a1", min_value=0.01, max_value=1.0, value=0.44, step=0.01, key="aashto_a1")
            a2 = f2.number_input("Coeficiente estructural base granular a2", min_value=0.01, max_value=1.0, value=0.14, step=0.01, key="aashto_a2")
            a_be = f3.number_input(
                "Coeficiente estructural base estabilizada aBE",
                min_value=0.01, max_value=1.0, value=0.20, step=0.01, key="aashto_a_be",
                help="Coeficiente independiente para la base estabilizada. El valor 0.20 es preliminar y debe sustituirse por el valor documentado/calibrado del proyecto cuando esté disponible."
            )
            a3 = f4.number_input("Coeficiente estructural subbase a3", min_value=0.01, max_value=1.0, value=0.11, step=0.01, key="aashto_a3")
            g1,g2,g3 = st.columns(3)
            m2 = g1.number_input("Coeficiente drenaje base granular m2", min_value=0.4, max_value=1.4, value=1.00, step=0.05, key="aashto_m2")
            m_be = g2.number_input(
                "Factor de ajuste base estabilizada mBE", min_value=0.4, max_value=1.4, value=1.00, step=0.05, key="aashto_m_be",
                help="Factor de ajuste separado para la base estabilizada; no se interpreta automáticamente como coeficiente de drenaje de una capa granular."
            )
            m3 = g3.number_input("Coeficiente drenaje subbase m3", min_value=0.4, max_value=1.4, value=1.00, step=0.05, key="aashto_m3")

            d1 = float(selected_row.get('Carpeta_cm', 0.0) or 0.0) / 2.54
            d_bg = float(selected_row.get('Base_granular_cm', 0.0) or 0.0) / 2.54
            d_be = float(selected_row.get('Base_estabilizada_cm', 0.0) or 0.0) / 2.54
            if d_bg <= 0 and d_be <= 0:
                d_bg = float(selected_row.get('Base_cm', 0.0) or 0.0) / 2.54
            d3 = float(selected_row.get('Subbase_cm', 0.0) or 0.0) / 2.54

            sn1 = a1 * d1
            sn_bg = a2 * m2 * d_bg
            sn_be = a_be * m_be * d_be
            sn3 = a3 * m3 * d3
            sn_total = sn1 + sn_bg + sn_be + sn3
            sn_cum1 = sn1
            sn_cum_bg = sn1 + sn_bg
            sn_cum_be = sn1 + sn_bg + sn_be
            sn_cum3 = sn_total

            material_t1 = st.session_state.get('tomo1_materials', {})
            be_modulus = float(material_t1.get('base_stabilized_modulus_mpa', material_t1.get('stabilized_base_modulus_mpa', 0.0)) or 0.0)
            be_strength = float(material_t1.get('base_stabilized_strength_mpa', material_t1.get('stabilized_base_strength_mpa', 0.0)) or 0.0)
            if d_be > 0:
                if be_modulus <= 0 or be_strength <= 0:
                    st.warning("La sección incluye base estabilizada. Documente su módulo y resistencia de referencia en 5. Estructura antes de considerar definitivo el coeficiente aBE.")
                st.info(
                    f"Base estabilizada activa: {d_be*2.54:.1f} cm · aBE={a_be:.2f} · mBE={m_be:.2f}. "
                    "Su aporte SN se calcula por separado de la base granular."
                )
'''

if old_controls not in s:
    raise SystemExit('No se encontró el bloque de controles/cálculo AASHTO esperado')
s = s.replace(old_controls, new_controls, 1)

old_state = '''            st.session_state.aashto93_design = {**aashto_result, 'sn_provided': sn_total, 'complies': bool(aashto_complies),
                'a1':a1,'a2':a2,'a3':a3,'m2':m2,'m3':m3,'D1_in':d1,'D2_in':d2,'D3_in':d3,
                'SN1_contribution':sn1,'SN2_contribution':sn2,'SN3_contribution':sn3,
                'SN_cumulative_1':sn_cum1,'SN_cumulative_2':sn_cum2,'SN_cumulative_3':sn_cum3, **layer_residuals}
'''
new_state = '''            st.session_state.aashto93_design = {**aashto_result, 'sn_provided': sn_total, 'complies': bool(aashto_complies),
                'a1':a1,'a2':a2,'aBE':a_be,'a3':a3,'m2':m2,'mBE':m_be,'m3':m3,
                'D1_in':d1,'D2_granular_in':d_bg,'D2_stabilized_in':d_be,'D3_in':d3,
                'SN1_contribution':sn1,'SN_base_granular_contribution':sn_bg,'SN_base_stabilized_contribution':sn_be,'SN3_contribution':sn3,
                'SN_cumulative_1':sn_cum1,'SN_cumulative_base_granular':sn_cum_bg,'SN_cumulative_base_stabilized':sn_cum_be,'SN_cumulative_3':sn_cum3}
'''
if old_state not in s:
    raise SystemExit('No se encontró el bloque de estado AASHTO esperado')
s = s.replace(old_state, new_state, 1)

old_residual = '''            layer_residuals = residual_layer_thicknesses(sn_required, a1, a2, a3, m2, m3, d1, d2)
'''
new_residual = '''            # El despeje residual clásico se conserva únicamente para la ruta granular.
            # La base estabilizada se trata como capa independiente y no se fuerza dentro de a2.
            layer_residuals = residual_layer_thicknesses(sn_required, a1, a2, a3, m2, m3, d1, d_bg)
'''
if old_residual in s:
    s = s.replace(old_residual, new_residual, 1)

old_table = '''            layer_table = pd.DataFrame([
                ['Carpeta asfáltica','D1',d1,d1*2.54,'a1',a1,1.0,sn1,sn_cum1],
                ['Base','D2',d2,d2*2.54,'a2',a2,m2,sn2,sn_cum2],
                ['Subbase','D3',d3,d3*2.54,'a3',a3,m3,sn3,sn_cum3],
            ], columns=['Capa','Espesor','D (in)','D (cm)','Coeficiente','aᵢ','mᵢ','Aporte SN','SN acumulado'])
            st.dataframe(layer_table, use_container_width=True, hide_index=True)
            st.latex(r"SN=a_1D_1+a_2m_2D_2+a_3m_3D_3")
            st.write(f"**SN1 = a1·D1 = {a1:.3f}×{d1:.3f} = {sn1:.3f}**")
            st.write(f"**SN2 (aporte base) = a2·m2·D2 = {a2:.3f}×{m2:.3f}×{d2:.3f} = {sn2:.3f}**")
            st.write(f"**SN3 (aporte subbase) = a3·m3·D3 = {a3:.3f}×{m3:.3f}×{d3:.3f} = {sn3:.3f}**")
'''
new_table = '''            layer_rows = [
                ['Carpeta asfáltica','D1',d1,d1*2.54,'a1',a1,1.0,sn1,sn_cum1],
            ]
            if d_bg > 0:
                layer_rows.append(['Base granular','DBG',d_bg,d_bg*2.54,'a2',a2,m2,sn_bg,sn_cum_bg])
            if d_be > 0:
                layer_rows.append(['Base estabilizada','DBE',d_be,d_be*2.54,'aBE',a_be,m_be,sn_be,sn_cum_be])
            layer_rows.append(['Subbase','D3',d3,d3*2.54,'a3',a3,m3,sn3,sn_cum3])
            layer_table = pd.DataFrame(layer_rows, columns=['Capa','Espesor','D (in)','D (cm)','Coeficiente','aᵢ','mᵢ','Aporte SN','SN acumulado'])
            st.dataframe(layer_table, use_container_width=True, hide_index=True)
            st.latex(r"SN=a_1D_1+a_{BG}m_{BG}D_{BG}+a_{BE}m_{BE}D_{BE}+a_3m_3D_3")
            st.write(f"**SN carpeta = {a1:.3f}×{d1:.3f} = {sn1:.3f}**")
            if d_bg > 0:
                st.write(f"**SN base granular = {a2:.3f}×{m2:.3f}×{d_bg:.3f} = {sn_bg:.3f}**")
            if d_be > 0:
                st.write(f"**SN base estabilizada = {a_be:.3f}×{m_be:.3f}×{d_be:.3f} = {sn_be:.3f}**")
            st.write(f"**SN subbase = {a3:.3f}×{m3:.3f}×{d3:.3f} = {sn3:.3f}**")
'''
if old_table not in s:
    raise SystemExit('No se encontró la tabla AASHTO esperada')
s = s.replace(old_table, new_table, 1)

old_flex = '''            st.session_state.flex_design={"a1":a1,"a2":a2,"a3":a3,"m2":m2,"m3":m3,"sn":sn_total,"reliability_pct":reliability_pct,"overall_standard_error":overall_standard_error,"initial_serviceability":initial_serviceability,"terminal_serviceability":terminal_serviceability,"mechanistic_screening":st.session_state.get("mechanistic_screening",{})}
'''
new_flex = '''            st.session_state.flex_design={"a1":a1,"a2":a2,"aBE":a_be,"a3":a3,"m2":m2,"mBE":m_be,"m3":m3,"sn":sn_total,"reliability_pct":reliability_pct,"overall_standard_error":overall_standard_error,"initial_serviceability":initial_serviceability,"terminal_serviceability":terminal_serviceability,"mechanistic_screening":st.session_state.get("mechanistic_screening",{})}
'''
if old_flex not in s:
    raise SystemExit('No se encontró flex_design esperado')
s = s.replace(old_flex, new_flex, 1)

p.write_text(s, encoding='utf-8')
print('SN de base granular y base estabilizada separado correctamente')
