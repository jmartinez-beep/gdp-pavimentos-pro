from pathlib import Path
import subprocess
import sys

SCRIPT = Path('tools/add_aashto93_layer_controls.py')
text = SCRIPT.read_text(encoding='utf-8')
old = "replace_once('import math\\n', 'import math\\nfrom statistics import NormalDist\\n', 'importar NormalDist')"
new = """if 'from statistics import NormalDist\\n' not in text:\n    pos = text.find('import math\\n')\n    if pos < 0:\n        raise RuntimeError('No se encontró import math para agregar NormalDist')\n    pos += len('import math\\n')\n    text = text[:pos] + 'from statistics import NormalDist\\n' + text[pos:]"""
if old not in text:
    if "from statistics import NormalDist" in text and "pos = text.find('import math" in text:
        print('Migrador ya corregido.')
    else:
        raise RuntimeError('No se encontró la instrucción de importación a corregir en el migrador.')
else:
    SCRIPT.write_text(text.replace(old, new, 1), encoding='utf-8')
    print('Migrador AASHTO93 corregido para múltiples import math.')

subprocess.run([sys.executable, str(SCRIPT)], check=True)
