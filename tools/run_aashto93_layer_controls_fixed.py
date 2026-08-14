from pathlib import Path
import subprocess
import sys

SCRIPT = Path('tools/add_aashto93_layer_controls.py')
text = SCRIPT.read_text(encoding='utf-8')

# 1) Hacer robusta la inserción de NormalDist aunque app.py tenga varios import math.
old = "replace_once('import math\\n', 'import math\\nfrom statistics import NormalDist\\n', 'importar NormalDist')"
new = """if 'from statistics import NormalDist\\n' not in text:\n    pos = text.find('import math\\n')\n    if pos < 0:\n        raise RuntimeError('No se encontró import math para agregar NormalDist')\n    pos += len('import math\\n')\n    text = text[:pos] + 'from statistics import NormalDist\\n' + text[pos:]"""
if old in text:
    text = text.replace(old, new, 1)

# 2) La arquitectura del payload cambió en una etapa previa. Para esta primera
# integración priorizamos funciones, UI AASHTO93 y controles de granulares;
# la persistencia/exportación se añadirá en un paso posterior con anclajes actuales.
label = "'añadir AASHTO93 al payload'"
idx = text.find(label)
if idx >= 0:
    start = text.rfind('replace_once(', 0, idx)
    if start < 0:
        raise RuntimeError('No se pudo localizar el bloque de payload AASHTO93.')
    text = text[:start] + "\nAPP.write_text(text, encoding='utf-8')\nprint('AASHTO93 y controles de capas aplicados; exportación diferida a la siguiente etapa.')\n"

SCRIPT.write_text(text, encoding='utf-8')
print('Migrador AASHTO93 preparado de forma idempotente.')
subprocess.run([sys.executable, str(SCRIPT)], check=True)
