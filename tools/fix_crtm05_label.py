from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
old = 'Conversión automática WGS84 → Latitud'
new = 'Conversión automática CRTM05 → WGS84: Latitud'
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit('No se encontró la etiqueta de conversión esperada.')
path.write_text(text, encoding='utf-8')
print('Etiqueta CRTM05 → WGS84 verificada.')
