from pathlib import Path

APP = Path("app.py")
START = '    st.markdown("#### Resumen del conteo ingresado")'
END = '    a, b, c, d = st.columns(4)'

text = APP.read_text(encoding="utf-8")
start = text.find(START)
if start < 0:
    print("El resumen duplicado ya no existe; no se requieren cambios.")
    raise SystemExit(0)
end = text.find(END, start)
if end < 0:
    raise SystemExit("No se encontró el límite final esperado del bloque de resumen.")

updated = text[:start] + text[end:]
APP.write_text(updated, encoding="utf-8")
print("Resumen duplicado de conteo eliminado. Se conservan ayuda, entradas y métricas calculadas.")
