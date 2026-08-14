from pathlib import Path
import re

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# VERIFIED_CR2020_MATERIAL_THRESHOLDS'
if MARKER in text:
    print('Umbrales CR-2020 ya integrados.')
    raise SystemExit(0)

# 1) Insertar constantes verificadas de calidad de materiales granulares.
anchor = "# CLIMATE_GRANULAR_MASTER_CURVE_PHASE\n"
if anchor not in text:
    raise RuntimeError('No se encontró el bloque de clima/granulares vigente.')
constants = anchor + """# VERIFIED_CR2020_MATERIAL_THRESHOLDS
CR2020_BASE_CBR_MIN_PCT = 80.0
CR2020_SUBBASE_CBR_MIN_PCT = 30.0
CR2020_GRANULAR_QUALITY_REFERENCE = (
    'CR-2020: Sección 301 Subbases y bases granulares + Subsección 703.05 Agregado para capas de subbase y base'
)

"""
text = text.replace(anchor, constants, 1)

# 2) Sustituir los campos editables de CBR mínimo por umbrales fijos trazables.
pattern = re.compile(
    r'''        cb1, cb2, cb3, cb4 = st\.columns\(4\)\n'''
    r'''        base_cbr = cb1\.number_input\("CBR material de base \(%\)".*?\n'''
    r'''        base_cbr_min = cb2\.number_input\("CBR mínimo exigido a base \(%\)".*?\n'''
    r'''        subbase_cbr = cb3\.number_input\("CBR material de subbase \(%\)".*?\n'''
    r'''        subbase_cbr_min = cb4\.number_input\("CBR mínimo exigido a subbase \(%\)".*?\n''',
    re.S,
)
replacement = '''        cb1, cb2, cb3, cb4 = st.columns(4)
        base_cbr = cb1.number_input("CBR material de base (%)", min_value=0.0, max_value=200.0, value=80.0, step=1.0, key="base_material_cbr")
        cb2.metric("CBR mínimo base — CR-2020", f"{CR2020_BASE_CBR_MIN_PCT:.0f}%", help=CR2020_GRANULAR_QUALITY_REFERENCE)
        subbase_cbr = cb3.number_input("CBR material de subbase (%)", min_value=0.0, max_value=200.0, value=30.0, step=1.0, key="subbase_material_cbr")
        cb4.metric("CBR mínimo subbase — CR-2020", f"{CR2020_SUBBASE_CBR_MIN_PCT:.0f}%", help=CR2020_GRANULAR_QUALITY_REFERENCE)
        base_cbr_min = CR2020_BASE_CBR_MIN_PCT
        subbase_cbr_min = CR2020_SUBBASE_CBR_MIN_PCT
'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError(f'No se pudo sustituir el bloque CBR mínimo; coincidencias={count}')

# 3) Añadir referencia visible inmediatamente después del encabezado de control granular.
old_caption = '        st.markdown("##### Control de calidad CBR de materiales granulares")\n'
new_caption = old_caption + '''        st.caption("Criterios incorporados como control fijo de calidad: base granular CBR ≥ 80% y subbase granular CBR ≥ 30%. Referencia de aplicación: CR-2020 Sección 301 y Subsección 703.05. Verifique además graduación, plasticidad y demás requisitos de la especificación vigente.")
'''
if old_caption not in text:
    raise RuntimeError('No se encontró encabezado de control CBR granular.')
text = text.replace(old_caption, new_caption, 1)

# 4) Reforzar trazabilidad en el estado guardado.
text = text.replace(
    "'base_cbr_min_pct':base_cbr_min,'subbase_cbr_pct':subbase_cbr,'subbase_cbr_min_pct':subbase_cbr_min,",
    "'base_cbr_min_pct':base_cbr_min,'subbase_cbr_pct':subbase_cbr,'subbase_cbr_min_pct':subbase_cbr_min,'reference':CR2020_GRANULAR_QUALITY_REFERENCE,'threshold_source':'CR-2020',",
    1,
) if "'base_cbr_min_pct':base_cbr_min,'subbase_cbr_pct':subbase_cbr,'subbase_cbr_min_pct':subbase_cbr_min," in text else text

# 5) Aclarar que A/B no es todavía regla normativa fija: evitar falsa conformidad.
text = text.replace(
    '        st.markdown("#### Clasificación climática A / B — criterio documentado")\n',
    '        st.markdown("#### Clasificación climática A / B — criterio de proyecto, pendiente de tabla normativa exacta")\n',
    1,
)
text = text.replace(
    '        st.warning("La clasificación A/B queda operativa como **criterio configurable**. Antes de usarla como clasificación normativa, documente la tabla/umbral GDP aplicable al proyecto.")\n',
    '        st.warning("No se ha fijado un umbral A/B como requisito GDP universal. La clasificación permanece como **criterio de proyecto** hasta vincular la tabla/sección oficial exacta; no se usa para declarar conformidad normativa.")\n',
    1,
)

# 6) Aclarar el control de carpeta: CR-2020 lo vincula a diseño/fórmula/NMAS, no a un rango universal único.
text = text.replace(
    '        st.markdown("##### Verificación de espesor de carpeta asfáltica")\n',
    '        st.markdown("##### Verificación de espesor de carpeta asfáltica — diseño/fórmula de trabajo")\n',
    1,
)
text = text.replace(
    '        st.caption("Rango configurable mientras se documenta la tabla GDP/CR-2020 aplicable. El sistema no declara estos valores como límites normativos universales.")\n',
    '        st.caption("CR-2020 controla el espesor contra el diseño, fórmula de trabajo y tamaño máximo nominal aplicable; no se impone aquí un único rango universal. Los límites siguientes son del proyecto y deben quedar documentados.")\n',
    1,
)

APP.write_text(text, encoding='utf-8')
print('Umbrales verificados CR-2020 integrados y criterios no verificados claramente separados.')
