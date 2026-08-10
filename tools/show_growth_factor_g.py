from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

replacements = [
    (
        '    m4.metric("Factor acumulado", f"{gf:,.3f}")\n',
        '    m4.metric("Factor de crecimiento G", f"{gf:,.3f}")\n'
    ),
    (
        '    st.latex(r"EEq = 365 \\cdot \\left[\\sum(TPD_i\\,FC_i)\\right] \\cdot FD \\cdot FCarril \\cdot \\frac{(1+r)^Y-1}{r}")\n    st.caption("Cada cantidad corresponde al tránsito promedio diario de esa categoría. Revise cuidadosamente valores atípicos antes de continuar.")\n',
        '    st.latex(r"EEq = 365 \\cdot \\left[\\sum(TPD_i\\,FC_i)\\right] \\cdot FD \\cdot FCarril \\cdot G, \\qquad G=\\frac{(1+r)^Y-1}{r}")\n    st.info(\n        f"**Factor de crecimiento acumulado G = {gf:,.3f}** · "\n        f"calculado con r = {growth_pct:.2f}% anual y Y = {int(years)} años. "\n        "G transforma el tránsito del año base en la acumulación equivalente durante el período de diseño."\n    )\n    st.caption("Cada cantidad corresponde al tránsito promedio diario de esa categoría. Revise cuidadosamente valores atípicos antes de continuar.")\n'
    ),
    (
        '<tr><th>Tasa de crecimiento</th><td>{traffic[\'growth_rate\']:.2f}%</td></tr>\n<tr><th>Periodo de diseño</th><td>{traffic[\'years\']} años</td></tr>\n',
        '<tr><th>Tasa de crecimiento</th><td>{traffic[\'growth_rate\']:.2f}%</td></tr>\n<tr><th>Factor de crecimiento acumulado G</th><td>{traffic.get(\'growth_factor\', 0):.3f}</td></tr>\n<tr><th>Periodo de diseño</th><td>{traffic[\'years\']} años</td></tr>\n'
    ),
    (
        '            "growth_rate": growth_pct,\n            "years": int(years),\n',
        '            "growth_rate": growth_pct,\n            "growth_factor": gf,\n            "years": int(years),\n'
    ),
    (
        '    rows=[["Parámetro","Resultado"], ["Tomo activo", payload.get("active_tomo","")], ["TPD", f"{payload[\'traffic\'][\'tpd_total\']:,.0f}"], ["ESAL", f"{payload[\'traffic\'][\'esal\']:,.0f}"], ["Clase", payload[\'traffic\'][\'class\']], ["CBR", f"{payload[\'subgrade\'][\'cbr\']:.2f}%"], ["Subrasante", payload[\'subgrade\'][\'class\']]]\n',
        '    rows=[["Parámetro","Resultado"], ["Tomo activo", payload.get("active_tomo","")], ["TPD", f"{payload[\'traffic\'][\'tpd_total\']:,.0f}"], ["Crecimiento anual", f"{payload[\'traffic\'][\'growth_rate\']:.2f}%"], ["Factor de crecimiento G", f"{payload[\'traffic\'].get(\'growth_factor\', 0):.3f}"], ["Periodo de diseño", f"{payload[\'traffic\'][\'years\']} años"], ["ESAL", f"{payload[\'traffic\'][\'esal\']:,.0f}"], ["Clase", payload[\'traffic\'][\'class\']], ["CBR", f"{payload[\'subgrade\'][\'cbr\']:.2f}%"], ["Subrasante", payload[\'subgrade\'][\'class\']]]\n'
    ),
    (
        '        (k4,"Periodo de diseño",f"{int(years)} años",f"Crecimiento: {growth_pct:.2f}%<br>Factor acumulado: {gf:.3f}","#ff831d"),\n',
        '        (k4,"Periodo de diseño",f"{int(years)} años",f"Crecimiento: {growth_pct:.2f}%<br>Factor G: {gf:.3f}","#ff831d"),\n'
    ),
]

changed = 0
for old, new in replacements:
    if new in text:
        continue
    if old not in text:
        raise SystemExit(f'No se encontró un bloque esperado para aplicar el parche:\n{old[:160]}')
    text = text.replace(old, new, 1)
    changed += 1

path.write_text(text, encoding='utf-8')
print(f'Factor G actualizado en {changed} bloque(s).')
