from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# FIX_TOMO2_REPORT_DESIGN_CATEGORY_NONE'
if MARKER in text:
    print('Corrección Tomo II report design_category ya aplicada.')
    raise SystemExit(0)

old = '''    active_tomo = payload.get("active_tomo", "Tomo II")
    design_category = int(traffic.get("design_category", tomo1_design_category(float(traffic.get("esal", 0.0)))))
    traffic_class_html = (
'''
new = '''    active_tomo = payload.get("active_tomo", "Tomo II")
    # FIX_TOMO2_REPORT_DESIGN_CATEGORY_NONE
    raw_design_category = traffic.get("design_category")
    design_category = (
        int(raw_design_category)
        if raw_design_category not in (None, "")
        else tomo1_design_category(float(traffic.get("esal", 0.0)))
    )
    traffic_class_html = (
'''
if text.count(old) != 1:
    raise RuntimeError(f'No se encontró exactamente una vez el bloque make_report esperado; coincidencias={text.count(old)}')
text = text.replace(old, new, 1)

# Endurecer cualquier otra conversión directa del mismo patrón que haya quedado en generadores de salida.
bad = 'int(traffic.get("design_category", tomo1_design_category(float(traffic.get("esal", 0.0)))))'
if bad in text:
    raise RuntimeError('Quedó al menos una conversión insegura de design_category después de la migración.')

APP.write_text(text, encoding='utf-8')
print('Corrección aplicada: Tomo II ya no intenta convertir None a int al generar el informe.')
