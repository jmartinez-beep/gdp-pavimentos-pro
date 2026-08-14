from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')

old = 'reliability_pct = rc1.number_input("Confiabilidad del análisis (%)", min_value=50.0, max_value=99.9, value=float(reliability_default), step=1.0, key="design_reliability")'
new = 'reliability_pct = rc1.number_input("Confiabilidad del análisis (%)", min_value=50.0, max_value=99.9, value=float(reliability_default), step=1.0, key="design_reliability_pct")'

if old not in text:
    if new in text:
        print('Corrección ya aplicada; no hay cambios.')
        raise SystemExit(0)
    raise RuntimeError('No se encontró la línea esperada de confiabilidad para corregir.')

text = text.replace(old, new, 1)
APP.write_text(text, encoding='utf-8')
print('Colisión de session_state design_reliability corregida.')
